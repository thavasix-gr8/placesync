import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import require_admin, require_student
from .database import get_db
from .eligibility import check_eligibility
from .models import Application, Drive, StudentResume, User
from .schemas import (
    ApplicationApplicantOut,
    ApplicationOut,
    ApplicationStatusUpdate,
    BulkApplicationStatusUpdate,
    StatsOut,
)

router = APIRouter(tags=["Applications"])


def get_drive_or_404(drive_id: int, db: Session) -> Drive:
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if drive is None:
        raise HTTPException(status_code=404, detail="Drive not found")
    return drive


def get_owned_drive(drive_id: int, db: Session, current_user: User) -> Drive:
    drive = get_drive_or_404(drive_id, db)
    if drive.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage applicants for your own drives.")
    return drive


def csv_cell(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


@router.post("/drives/{drive_id}/apply", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def apply_to_drive(drive_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_student)):
    drive = get_drive_or_404(drive_id, db)
    eligible, reasons = check_eligibility(current_user, drive)
    if not eligible:
        raise HTTPException(status_code=400, detail={"message": "Not eligible", "reasons": reasons})

    existing_application = db.query(Application).filter(
        Application.student_id == current_user.id,
        Application.drive_id == drive_id,
    ).first()
    if existing_application:
        raise HTTPException(status_code=400, detail="You have already applied to this drive")

    resume = db.query(StudentResume).filter(
        StudentResume.student_id == current_user.id
    ).order_by(StudentResume.id.desc()).first()
    if resume is None:
        raise HTTPException(status_code=400, detail="Please upload your resume first")

    application = Application(
        student_id=current_user.id,
        drive_id=drive_id,
        resume_id=resume.id,
    )
    try:
        drive.applicant_count += 1
        db.add(application)
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="You have already applied to this drive") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Your application could not be submitted. Please try again.",
        ) from exc
    return application


@router.get("/applications/me", response_model=list[ApplicationOut])
def get_my_applications(db: Session = Depends(get_db), current_user: User = Depends(require_student)):
    return db.query(Application).filter(Application.student_id == current_user.id).order_by(Application.applied_at.desc()).all()


@router.get("/drives/{drive_id}/applications", response_model=list[ApplicationApplicantOut])
def get_drive_applications(drive_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    get_drive_or_404(drive_id, db)
    return db.query(Application).filter(Application.drive_id == drive_id).all()


@router.put("/applications/{application_id}/status", response_model=ApplicationOut)
def update_application_status(application_id: int, data: ApplicationStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    application = db.query(Application).filter(Application.id == application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    application.status = data.status
    db.commit()
    db.refresh(application)
    return application


@router.get("/admin/drives/{drive_id}/applicants.csv")
def export_drive_applicants_csv(
    drive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    get_owned_drive(drive_id, db, current_user)
    applications = db.query(Application).filter(Application.drive_id == drive_id).order_by(Application.id).all()
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Name", "Register number", "Department", "CGPA", "Arrears", "Status", "Applied date"])
    for application in applications:
        student = application.student
        writer.writerow([
            csv_cell(student.name),
            csv_cell(student.register_number),
            csv_cell(student.department),
            csv_cell(student.cgpa),
            csv_cell(student.arrears),
            csv_cell(application.status),
            csv_cell(application.applied_at.isoformat()),
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="drive_{drive_id}_applicants.csv"'},
    )


@router.put("/drives/{drive_id}/applications/status")
def update_drive_applications_status(
    drive_id: int,
    data: BulkApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    get_owned_drive(drive_id, db, current_user)
    application_ids = set(data.application_ids)
    applications = db.query(Application).filter(
        Application.drive_id == drive_id,
        Application.id.in_(application_ids),
    ).all()
    if len(applications) != len(application_ids):
        raise HTTPException(status_code=404, detail="One or more applications were not found for this drive.")
    try:
        for application in applications:
            application.status = data.status
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Application statuses could not be updated.") from exc
    return {"updated": len(applications), "status": data.status}


@router.get("/admin/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return {
        "total_drives": db.query(Drive).count(),
        "total_applications": db.query(Application).count(),
        "shortlisted": db.query(Application).filter(Application.status == "Shortlisted").count(),
        "selected": db.query(Application).filter(Application.status == "Selected").count(),
    }
