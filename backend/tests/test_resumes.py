import asyncio
import csv
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
import sqlite3
from tempfile import SpooledTemporaryFile
import zipfile

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import get_current_user, require_admin
from app.migrations import upgrade_resume_feature
from app.models import Application, Base, Drive, StudentResume, User
from app.routes_applications import apply_to_drive, get_stats
from app.routes_applications import (
    export_drive_applicants_csv,
    update_drive_applications_status,
)
from app.routes_resumes import (
    MAX_RESUME_BYTES,
    download_drive_resumes,
    download_applicant_resume,
    get_my_resume,
    get_private_resume_path,
    upload_my_resume,
    view_applicant_resume,
    view_my_resume,
)
from app.schemas import BulkApplicationStatusUpdate
from app import routes_resumes

VALID_PDF = b"%PDF-1.4\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF\n"
SECOND_PDF = b"%PDF-1.5\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF\n"


def make_user(name, email, role="student"):
    return User(
        name=name, email=email, password_hash="test-hash", role=role,
        register_number=f"REG-{email}", department="IT", batch="2026", cgpa=8.2, arrears=0,
    )


def make_drive(owner, company="Test Company"):
    return Drive(
        company=company, job_role="Engineer", description="Test drive",
        deadline=datetime.utcnow() + timedelta(days=2), min_cgpa=7.0,
        max_arrears=0, allowed_departments="IT", batch="2026",
        applicant_count=0, created_by=owner,
    )


def make_upload(filename="resume.pdf", content=VALID_PDF):
    file = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
    file.write(content)
    file.seek(0)
    return UploadFile(file=file, filename=filename, size=len(content))


def upload(db, student, filename="resume.pdf", content=VALID_PDF):
    return asyncio.run(upload_my_resume(make_upload(filename, content), db, student))


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "resume-test-secret")
    engine = create_engine(f"sqlite:///{tmp_path / 'resume-tests.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    db = sessions()
    student = make_user("Student", "student@ssn.edu")
    other_student = make_user("Other Student", "other@ssn.edu")
    admin = make_user("Admin", "admin@ssn.edu", "admin")
    other_admin = make_user("Other Admin", "other-admin@ssn.edu", "admin")
    db.add_all([student, other_student, admin, other_admin])
    db.flush()
    drive = make_drive(admin)
    other_drive = make_drive(other_admin, "Other Company")
    second_drive = make_drive(admin, "Second Company")
    db.add_all([drive, other_drive, second_drive])
    db.commit()
    storage = tmp_path / "private-resumes"
    monkeypatch.setattr(routes_resumes, "RESUME_STORAGE_DIR", storage)
    yield {
        "db": db, "engine": engine, "student": student, "other_student": other_student,
        "admin": admin, "other_admin": other_admin, "drive": drive,
        "other_drive": other_drive, "second_drive": second_drive, "storage": storage,
    }
    db.close()
    engine.dispose()


def test_valid_upload_metadata_and_profile_fields_are_preserved(data):
    student = data["student"]
    original_profile = (student.name, student.email, student.department, student.batch, student.cgpa, student.arrears)
    uploaded = upload(data["db"], student, "student resume.pdf")
    current = get_my_resume(data["db"], student)

    assert uploaded["id"] == current["id"]
    assert current["filename"] == "student_resume.pdf"
    assert current["uploaded_at"] is not None
    assert (student.name, student.email, student.department, student.batch, student.cgpa, student.arrears) == original_profile
    assert len(list(data["storage"].glob("*.pdf"))) == 1
    assert oct(next(data["storage"].glob("*.pdf")).stat().st_mode & 0o777) == "0o600"


def test_oversize_non_pdf_fake_pdf_and_path_traversal_are_rejected(data):
    with pytest.raises(HTTPException) as oversize:
        upload(data["db"], data["student"], content=b"x" * (MAX_RESUME_BYTES + 1))
    assert oversize.value.status_code == 413

    with pytest.raises(HTTPException) as wrong_extension:
        upload(data["db"], data["student"], "resume.txt", b"not a PDF")
    assert wrong_extension.value.status_code == 400

    with pytest.raises(HTTPException) as fake_pdf:
        upload(data["db"], data["student"], "fake.pdf", b"%PDF-1.4 fake file without xref or EOF")
    assert fake_pdf.value.status_code == 400

    with pytest.raises(HTTPException) as bad_xref:
        upload(data["db"], data["student"], "bad-xref.pdf", b"%PDF-1.4\nxref\nstartxref\n1\n%%EOF")
    assert bad_xref.value.status_code == 400

    with pytest.raises(HTTPException) as traversal:
        upload(data["db"], data["student"], "../../outside.pdf")
    assert traversal.value.status_code == 400
    assert data["db"].query(StudentResume).count() == 0
    assert not data["storage"].exists() or list(data["storage"].iterdir()) == []


def test_replacement_keeps_the_resume_version_attached_to_each_application(data):
    db, student = data["db"], data["student"]
    first = upload(db, student, "first.pdf", VALID_PDF)
    first_application = apply_to_drive(data["drive"].id, db, student)
    second = upload(db, student, "replacement.pdf", SECOND_PDF)
    second_application = apply_to_drive(data["second_drive"].id, db, student)

    assert first["id"] != second["id"]
    assert first_application.resume_id == first["id"]
    assert second_application.resume_id == second["id"]
    assert db.query(StudentResume).count() == 2
    assert len(list(data["storage"].glob("*.pdf"))) == 2

    response = download_applicant_resume(
        data["drive"].id, first_application.id, db, data["admin"]
    )
    assert Path(response.path).read_bytes() == VALID_PDF
    assert response.media_type == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]


def test_student_can_view_only_their_current_resume_inline(data):
    student_resume = upload(data["db"], data["student"], "mine.pdf", VALID_PDF)
    upload(data["db"], data["other_student"], "other.pdf", SECOND_PDF)

    response = view_my_resume(data["db"], data["student"])

    assert Path(response.path).read_bytes() == VALID_PDF
    assert f"filename=\"{student_resume['filename']}\"" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].startswith("inline;")


def test_apply_updates_drive_and_admin_statistics_in_the_same_transaction(data):
    db, student, drive = data["db"], data["student"], data["drive"]
    resume = upload(db, student)
    application = apply_to_drive(drive.id, db, student)

    db.refresh(drive)
    assert application.resume_id == resume["id"]
    assert drive.applicant_count == 1
    assert db.query(Application).count() == 1
    assert get_stats(db, data["admin"])["total_applications"] == 1
    with pytest.raises(HTTPException) as duplicate:
        apply_to_drive(drive.id, db, student)
    assert duplicate.value.status_code == 400
    assert drive.applicant_count == 1


def test_apply_without_resume_does_not_create_an_application(data):
    with pytest.raises(HTTPException) as missing:
        apply_to_drive(data["drive"].id, data["db"], data["student"])
    assert missing.value.status_code == 400
    assert missing.value.detail == "Please upload your resume first"
    assert data["db"].query(Application).count() == 0
    assert data["drive"].applicant_count == 0


def test_apply_is_open_until_end_of_deadline_day_and_closed_afterward(data):
    db, drive, student = data["db"], data["drive"], data["student"]
    upload(db, student)
    drive.deadline = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    db.commit()
    same_day_application = apply_to_drive(drive.id, db, student)
    assert same_day_application.student_id == student.id

    next_drive = data["second_drive"]
    next_drive.deadline = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    db.commit()
    with pytest.raises(HTTPException) as closed:
        apply_to_drive(next_drive.id, db, student)
    assert closed.value.status_code == 400
    assert closed.value.detail == "Applications for this drive are closed."


def test_failed_apply_rolls_back_application_and_drive_count(data):
    db, drive, student = data["db"], data["drive"], data["student"]
    upload(db, student)
    original_commit = db.commit

    def fail_commit():
        raise RuntimeError("simulated commit failure")

    db.commit = fail_commit
    with pytest.raises(HTTPException) as failure:
        apply_to_drive(drive.id, db, student)
    assert failure.value.status_code == 500
    db.commit = original_commit
    db.rollback()
    db.refresh(drive)
    assert db.query(Application).count() == 0
    assert drive.applicant_count == 0


def test_only_the_drive_owner_admin_can_download_and_students_are_rejected(data):
    db, student = data["db"], data["student"]
    resume = upload(db, student)
    application = apply_to_drive(data["drive"].id, db, student)
    assert application.resume_id == resume["id"]

    with pytest.raises(HTTPException) as student_denied:
        require_admin(student)
    assert student_denied.value.status_code == 403
    with pytest.raises(HTTPException) as other_admin_denied:
        download_applicant_resume(data["drive"].id, application.id, db, data["other_admin"])
    assert other_admin_denied.value.status_code == 403
    with pytest.raises(HTTPException) as other_admin_view_denied:
        view_applicant_resume(data["drive"].id, application.id, db, data["other_admin"])
    assert other_admin_view_denied.value.status_code == 403
    view_response = view_applicant_resume(data["drive"].id, application.id, db, data["admin"])
    assert Path(view_response.path).read_bytes() == VALID_PDF
    assert view_response.headers["content-disposition"].startswith("inline;")
    with pytest.raises(HTTPException) as wrong_drive:
        download_applicant_resume(data["other_drive"].id, application.id, db, data["admin"])
    assert wrong_drive.value.status_code == 404
    with pytest.raises(HTTPException) as not_linked:
        download_applicant_resume(data["drive"].id, application.id + 1000, db, data["admin"])
    assert not_linked.value.status_code == 404


def test_missing_authentication_and_path_traversal_are_rejected(data, tmp_path):
    # An invalid or absent bearer token is rejected by the existing JWT dependency.
    with pytest.raises(HTTPException) as unauthenticated:
        get_current_user(token="invalid", db=data["db"])
    assert unauthenticated.value.status_code == 401

    resume = upload(data["db"], data["student"])
    record = data["db"].query(StudentResume).filter(StudentResume.id == resume["id"]).one()
    original_storage_name = record.storage_name
    record.storage_name = "../../outside.pdf"
    data["db"].commit()
    with pytest.raises(HTTPException) as traversal:
        download_applicant_resume(data["drive"].id, 1, data["db"], data["admin"])
    assert traversal.value.status_code == 404
    record.storage_name = original_storage_name
    data["db"].commit()


def test_resume_migration_preserves_existing_data_and_counts(tmp_path):
    database_path = tmp_path / "existing.db"
    with sqlite3.connect(database_path) as database:
        database.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password_hash TEXT, role TEXT,
                register_number TEXT, department TEXT, batch TEXT, cgpa REAL, arrears INTEGER);
            CREATE TABLE drives (id INTEGER PRIMARY KEY, company TEXT, job_role TEXT, description TEXT,
                deadline DATETIME, min_cgpa REAL, max_arrears INTEGER, allowed_departments TEXT, batch TEXT);
            CREATE TABLE applications (id INTEGER PRIMARY KEY, student_id INTEGER, drive_id INTEGER,
                status TEXT, applied_at DATETIME);
            INSERT INTO users VALUES (1, 'Admin', 'admin@ssn.edu', 'hash', 'admin', 'A1', 'IT', '2026', 0, 0);
            INSERT INTO users VALUES (2, 'Student', 'student@ssn.edu', 'hash2', 'student', 'S1', 'IT', '2026', 8, 0);
            INSERT INTO drives VALUES (7, 'Company', 'Engineer', 'Drive', '2030-01-01', 7, 0, 'IT', '2026');
            INSERT INTO applications VALUES (10, 2, 7, 'Applied', '2026-01-01');
            INSERT INTO applications VALUES (11, 2, 7, 'Shortlisted', '2026-01-02');
        """)
    backup = upgrade_resume_feature(str(database_path))
    assert backup and Path(backup).is_file()
    with sqlite3.connect(database_path) as database:
        assert database.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert database.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
        assert database.execute("SELECT COUNT(*) FROM drives").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 2
        assert database.execute("SELECT applicant_count, created_by_id FROM drives WHERE id=7").fetchone() == (2, 1)
        assert database.execute("SELECT COUNT(*) FROM applications WHERE resume_id IS NULL").fetchone()[0] == 2
        assert database.execute("SELECT COUNT(*) FROM student_resumes").fetchone()[0] == 0
    with sqlite3.connect(backup) as database:
        assert database.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert database.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 2
    assert upgrade_resume_feature(str(database_path)) is None


def test_csv_export_includes_applicant_fields_and_escapes_formula_cells(data):
    student = data["student"]
    student.name = "=1+1"
    student.register_number = "+SUM(1,2)"
    student.department = "-cmd"
    data["db"].add(Application(student_id=student.id, drive_id=data["drive"].id, status="@name"))
    data["db"].commit()

    response = export_drive_applicants_csv(data["drive"].id, data["db"], data["admin"])
    rows = list(csv.reader(StringIO(response.body.decode("utf-8"))))

    assert rows[0] == ["Name", "Register number", "Department", "CGPA", "Arrears", "Status", "Applied date"]
    assert rows[1][0:3] == ["'=1+1", "'+SUM(1,2)", "'-cmd"]
    assert rows[1][5] == "'@name"
    assert "attachment" in response.headers["content-disposition"]


def test_zip_export_uses_application_resume_version_and_skips_legacy_apps(data):
    db, student, drive = data["db"], data["student"], data["drive"]
    first_resume = upload(db, student, "first.pdf", VALID_PDF)
    application = apply_to_drive(drive.id, db, student)
    upload(db, student, "newer.pdf", SECOND_PDF)
    old_application = Application(
        student_id=data["other_student"].id,
        drive_id=drive.id,
        status="Applied",
    )
    db.add(old_application)
    db.commit()

    response = download_drive_resumes(drive.id, db, data["admin"])

    async def read_archive():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        if response.background:
            await response.background()
        return b"".join(chunks)

    archive_bytes = asyncio.run(read_archive())
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        assert len(names) == 1
        assert names[0].endswith(".pdf")
        assert "/" not in names[0] and "\\" not in names[0]
        assert archive.read(names[0]) == VALID_PDF
    assert application.resume_id == first_resume["id"]
    assert response.headers["x-resumes-skipped"] == "1"


def test_exports_require_drive_owner_admin(data):
    with pytest.raises(HTTPException) as csv_denied:
        export_drive_applicants_csv(data["drive"].id, data["db"], data["other_admin"])
    assert csv_denied.value.status_code == 403
    with pytest.raises(HTTPException) as zip_denied:
        download_drive_resumes(data["drive"].id, data["db"], data["other_admin"])
    assert zip_denied.value.status_code == 403
    with pytest.raises(HTTPException) as student_denied:
        require_admin(data["student"])
    assert student_denied.value.status_code == 403


def test_bulk_status_update_is_drive_scoped_and_updates_stats(data):
    db = data["db"]
    first = Application(student_id=data["student"].id, drive_id=data["drive"].id, status="Applied")
    second = Application(student_id=data["other_student"].id, drive_id=data["drive"].id, status="Rejected")
    db.add_all([first, second])
    db.commit()

    result = update_drive_applications_status(
        data["drive"].id,
        BulkApplicationStatusUpdate(application_ids=[first.id, second.id], status="Shortlisted"),
        db,
        data["admin"],
    )

    assert result == {"updated": 2, "status": "Shortlisted"}
    assert db.query(Application).filter(Application.status == "Shortlisted").count() == 2
    assert get_stats(db, data["admin"])["shortlisted"] == 2
    with pytest.raises(HTTPException) as wrong_drive:
        update_drive_applications_status(
            data["drive"].id,
            BulkApplicationStatusUpdate(application_ids=[first.id, second.id], status="Selected"),
            db,
            data["other_admin"],
        )
    assert wrong_drive.value.status_code == 403
    assert db.query(Application).filter(Application.status == "Selected").count() == 0
