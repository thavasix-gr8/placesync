import os
import re
import unicodedata
from pathlib import Path
from tempfile import SpooledTemporaryFile
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from starlette.background import BackgroundTask

from .auth import require_admin, require_student
from .database import get_db
from .models import Application, Drive, StudentResume, User
from .schemas import ResumeOut

router = APIRouter(tags=["Resumes"])
MAX_RESUME_BYTES = 10 * 1024 * 1024
READ_CHUNK_SIZE = 64 * 1024
RESUME_STORAGE_DIR = Path(__file__).resolve().parents[1] / "private_uploads" / "resumes"


def safe_display_filename(filename: str) -> str:
    leaf = filename.replace("\\", "/").rsplit("/", 1)[-1]
    leaf = unicodedata.normalize("NFKD", leaf).encode("ascii", "ignore").decode("ascii")
    leaf = re.sub(r"[^A-Za-z0-9._-]+", "_", leaf).strip("._")
    if not leaf or not leaf.lower().endswith(".pdf"):
        leaf = "resume.pdf"
    return f"{leaf[:-4][:116]}.pdf"


def get_private_resume_path(storage_name: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}\.pdf", storage_name):
        raise HTTPException(status_code=404, detail="Resume file was not found")
    root = Path(RESUME_STORAGE_DIR).resolve()
    path = (root / storage_name).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file was not found")
    return path


def resume_file_response(resume: StudentResume, disposition: str):
    resume_path = get_private_resume_path(resume.storage_name)
    return FileResponse(
        resume_path,
        media_type="application/pdf",
        filename=safe_display_filename(resume.original_filename),
        content_disposition_type=disposition,
        headers={"X-Content-Type-Options": "nosniff"},
    )


def get_application_resume(drive_id: int, application_id: int, db: Session, current_user: User):
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.drive_id == drive_id,
    ).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.drive.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only access resumes for your own drives.")
    if application.resume is None or application.resume.student_id != application.student_id:
        raise HTTPException(status_code=404, detail="No resume was attached to this application.")
    return application.resume


def safe_zip_part(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_-")
    return value[:80] or "Student"


def is_valid_pdf(prefix: bytes, tail: bytes, size: int, file_path: Path) -> bool:
    if size < 20 or not prefix.startswith(b"%PDF-"):
        return False
    eof_position = tail.rfind(b"%%EOF")
    startxref_position = tail.rfind(b"startxref")
    if startxref_position < 0 or eof_position <= startxref_position:
        return False
    xref_value = tail[startxref_position + len(b"startxref"):eof_position].strip().splitlines()
    if not xref_value:
        return False
    try:
        xref_offset = int(xref_value[0].strip())
        if xref_offset <= 0 or xref_offset >= size:
            return False
    except ValueError:
        return False
    with file_path.open("rb") as pdf_file:
        pdf_file.seek(xref_offset)
        xref_data = pdf_file.read(32)
    if not xref_data.startswith(b"xref") and not re.match(rb"\d+\s+\d+\s+obj\b", xref_data):
        return False
    return not tail[eof_position + len(b"%%EOF"):].strip()


@router.get("/resumes/me", response_model=ResumeOut | None)
def get_my_resume(db: Session = Depends(get_db), current_user: User = Depends(require_student)):
    resume = db.query(StudentResume).filter(
        StudentResume.student_id == current_user.id
    ).order_by(StudentResume.id.desc()).first()
    if resume is None:
        return None
    return {"id": resume.id, "filename": resume.original_filename, "uploaded_at": resume.uploaded_at}


@router.get("/resumes/me/view")
def view_my_resume(db: Session = Depends(get_db), current_user: User = Depends(require_student)):
    resume = db.query(StudentResume).filter(
        StudentResume.student_id == current_user.id
    ).order_by(StudentResume.id.desc()).first()
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume has been uploaded.")
    return resume_file_response(resume, "inline")


@router.post("/resumes/me", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_my_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    filename = file.filename or ""
    if not filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Choose a PDF file with a valid filename.")
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")
    if file.size is not None and file.size > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="Resume must be 10 MB or smaller.")

    root = Path(RESUME_STORAGE_DIR).resolve()
    temporary_path = root / f"{uuid4().hex}.upload"
    storage_name = f"{uuid4().hex}.pdf"
    final_path = root / storage_name
    size = 0
    prefix = bytearray()
    tail = b""
    saved_path = None
    database_saved = False
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        with temporary_path.open("xb") as destination:
            os.chmod(temporary_path, 0o600)
            while chunk := await file.read(READ_CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_RESUME_BYTES:
                    raise HTTPException(status_code=413, detail="Resume must be 10 MB or smaller.")
                if len(prefix) < 8:
                    prefix.extend(chunk[:8 - len(prefix)])
                tail = (tail + chunk)[-4096:]
                destination.write(chunk)

        if not is_valid_pdf(bytes(prefix), tail, size, temporary_path):
            raise HTTPException(status_code=400, detail="This file is not a valid PDF resume.")

        resume = StudentResume(
            student_id=current_user.id,
            storage_name=storage_name,
            original_filename=safe_display_filename(filename),
        )
        db.add(resume)
        db.flush()
        response = {"id": resume.id, "filename": resume.original_filename, "uploaded_at": resume.uploaded_at}
        os.replace(temporary_path, final_path)
        saved_path = final_path
        db.commit()
        database_saved = True
        return response
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Resume could not be saved. Please try again.") from exc
    finally:
        temporary_path.unlink(missing_ok=True)
        if saved_path is not None and not database_saved:
            saved_path.unlink(missing_ok=True)
        await file.close()


@router.get("/admin/drives/{drive_id}/applications/{application_id}/resume")
def download_applicant_resume(
    drive_id: int,
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    resume = get_application_resume(drive_id, application_id, db, current_user)
    return resume_file_response(resume, "attachment")


@router.get("/admin/drives/{drive_id}/applications/{application_id}/resume/view")
def view_applicant_resume(
    drive_id: int,
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    resume = get_application_resume(drive_id, application_id, db, current_user)
    return resume_file_response(resume, "inline")


@router.get("/admin/drives/{drive_id}/resumes.zip")
def download_drive_resumes(
    drive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if drive is None:
        raise HTTPException(status_code=404, detail="Drive not found")
    if drive.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only export resumes for your own drives.")

    applications = db.query(Application).options(
        joinedload(Application.student), joinedload(Application.resume)
    ).filter(Application.drive_id == drive_id).order_by(Application.id).all()
    archive_file = SpooledTemporaryFile(max_size=2 * 1024 * 1024, mode="w+b")
    used_names = set()
    skipped = 0
    try:
        with ZipFile(archive_file, mode="w", compression=ZIP_DEFLATED) as archive:
            for application in applications:
                resume = application.resume
                if resume is None or resume.student_id != application.student_id:
                    skipped += 1
                    continue

                register_number = safe_zip_part(application.student.register_number)
                student_name = safe_zip_part(application.student.name)
                base_name = f"{register_number}_{student_name}"
                filename = f"{base_name}.pdf"
                suffix = 2
                while filename.casefold() in used_names:
                    filename = f"{base_name}_{suffix}.pdf"
                    suffix += 1
                used_names.add(filename.casefold())
                archive.write(get_private_resume_path(resume.storage_name), arcname=filename)
    except Exception:
        archive_file.close()
        raise

    archive_file.seek(0)

    async def read_archive():
        while chunk := archive_file.read(64 * 1024):
            yield chunk

    async def close_archive():
        archive_file.close()

    return StreamingResponse(
        read_archive(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="drive_{drive_id}_resumes.zip"',
            "X-Resumes-Skipped": str(skipped),
        },
        background=BackgroundTask(close_archive),
    )
