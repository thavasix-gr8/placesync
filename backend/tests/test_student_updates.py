from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import require_admin
from app.database import Base
from app.eligibility import check_eligibility
from app.migrations import upgrade_student_updates
from app.models import Announcement, Application, Drive, Notification, User
from app.routes_applications import update_application_status, update_drive_applications_status
from app.routes_drives import get_drives
from app.routes_student_updates import (
    create_announcement,
    delete_announcement,
    get_admin_announcements,
    get_my_notifications,
    get_student_announcements,
    mark_my_notifications_read,
)
from app.schemas import AnnouncementCreate, ApplicationStatusUpdate, BulkApplicationStatusUpdate


@pytest.fixture
def data(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'student-updates.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    student = User(
        name="Student", email="student@ssn.edu", password_hash="test", role="student",
        register_number="STU-1", department="ECE", batch="2025", cgpa=6.0, arrears=2,
    )
    other_student = User(
        name="Other Student", email="other@ssn.edu", password_hash="test", role="student",
        register_number="STU-2", department="IT", batch="2026", cgpa=8.0, arrears=0,
    )
    admin = User(
        name="Admin", email="admin@ssn.edu", password_hash="test", role="admin",
        register_number="ADM-1", department="IT", batch="2026", cgpa=0, arrears=0,
    )
    db.add_all([student, other_student, admin])
    db.flush()
    drive = Drive(
        company="Zoho", job_role="Engineer", description="Placement drive",
        deadline=datetime.now() + timedelta(days=3), min_cgpa=6.5, max_arrears=1,
        allowed_departments="IT,CSE", batch="2026", applicant_count=0,
        created_by_id=admin.id,
    )
    db.add(drive)
    db.flush()
    application = Application(student_id=student.id, drive_id=drive.id, status="Applied")
    bulk_application = Application(student_id=other_student.id, drive_id=drive.id, status="Applied")
    db.add_all([application, bulk_application])
    db.commit()
    yield {
        "db": db, "engine": engine, "student": student,
        "other_student": other_student, "admin": admin, "drive": drive,
        "application": application, "bulk_application": bulk_application,
    }
    db.close()
    engine.dispose()


def test_single_and_bulk_status_changes_create_student_notifications(data):
    update_application_status(
        data["application"].id,
        ApplicationStatusUpdate(status="Shortlisted"),
        data["db"],
        data["admin"],
    )
    result = update_drive_applications_status(
        data["drive"].id,
        BulkApplicationStatusUpdate(
            application_ids=[data["bulk_application"].id], status="Selected"
        ),
        data["db"],
        data["admin"],
    )
    assert result["updated"] == 1
    assert data["db"].query(Notification).count() == 2
    student_messages = get_my_notifications(data["db"], data["student"])
    other_messages = get_my_notifications(data["db"], data["other_student"])
    assert student_messages[0].message == "You were shortlisted for Zoho."
    assert other_messages[0].message == "You were selected for Zoho."


def test_students_only_read_and_mark_their_own_notifications(data):
    data["db"].add_all([
        Notification(user_id=data["student"].id, message="For student"),
        Notification(user_id=data["other_student"].id, message="For another student"),
    ])
    data["db"].commit()
    own = get_my_notifications(data["db"], data["student"])
    assert len(own) == 1 and own[0].message == "For student"

    result = mark_my_notifications_read(data["db"], data["student"])
    assert result["updated"] == 1
    assert data["db"].query(Notification).filter(
        Notification.user_id == data["student"].id, Notification.is_read.is_(False)
    ).count() == 0
    assert data["db"].query(Notification).filter(
        Notification.user_id == data["other_student"].id, Notification.is_read.is_(False)
    ).count() == 1


def test_eligibility_returns_all_plain_reasons_from_backend(data):
    eligible, reasons = check_eligibility(data["student"], data["drive"])
    assert eligible is False
    assert reasons == [
        "CGPA below 6.5",
        "Arrears above the limit (max 1)",
        "Department not eligible",
        "Batch not eligible",
    ]
    drives = get_drives(data["db"], data["student"])
    assert drives[0]["reasons"] == reasons


def test_admin_announcements_are_sanitised_visible_and_admin_managed(data):
    with pytest.raises(HTTPException) as denied:
        require_admin(data["student"])
    assert denied.value.status_code == 403

    announcement = create_announcement(
        AnnouncementCreate(
            title="<b>Placement news</b>",
            message="<script>alert('x')</script>Drive registrations open.",
            drive_id=data["drive"].id,
        ),
        data["db"],
        data["admin"],
    )
    assert "<" not in announcement["title"] and "<" not in announcement["message"]
    assert announcement["drive_company"] == "Zoho"
    assert get_student_announcements(data["db"], data["student"])[0]["id"] == announcement["id"]
    assert get_admin_announcements(data["db"], data["admin"])[0]["id"] == announcement["id"]

    delete_announcement(announcement["id"], data["db"], data["admin"])
    assert data["db"].query(Announcement).count() == 0


def test_announcement_delete_is_limited_to_its_admin(data):
    second_admin = User(
        name="Second Admin", email="admin2@ssn.edu", password_hash="test", role="admin",
        register_number="ADM-2", department="IT", batch="2026", cgpa=0, arrears=0,
    )
    data["db"].add(second_admin)
    data["db"].flush()
    announcement = Announcement(
        title="News", message="A plain announcement", created_by_id=data["admin"].id
    )
    data["db"].add(announcement)
    data["db"].commit()
    with pytest.raises(HTTPException) as denied:
        delete_announcement(announcement.id, data["db"], second_admin)
    assert denied.value.status_code == 403
    assert data["db"].query(Announcement).count() == 1


def test_student_updates_migration_preserves_existing_rows(tmp_path):
    database_path = tmp_path / "old-project.db"
    from sqlite3 import connect
    with connect(database_path) as database:
        database.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE drives (id INTEGER PRIMARY KEY, company TEXT);
            CREATE TABLE applications (id INTEGER PRIMARY KEY, student_id INTEGER, drive_id INTEGER);
            INSERT INTO users VALUES (1, 'Student');
            INSERT INTO drives VALUES (2, 'Company');
            INSERT INTO applications VALUES (3, 1, 2);
        """)
    backup = upgrade_student_updates(str(database_path))
    assert backup
    from sqlite3 import connect
    with connect(database_path) as database:
        assert database.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert database.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM drives").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 0
        assert database.execute("SELECT COUNT(*) FROM announcements").fetchone()[0] == 0
    with connect(backup) as database:
        assert database.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert database.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 1
