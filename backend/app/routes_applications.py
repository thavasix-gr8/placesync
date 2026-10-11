from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import require_admin, require_student
from .database import get_db
from .eligibility import check_eligibility
from .models import Application, Drive, User
from .schemas import ApplicationApplicantOut, ApplicationOut, ApplicationStatusUpdate, StatsOut

router = APIRouter(tags=["Applications"])


def get_drive_or_404(drive_id: int, db: Session) -> Drive:
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if drive is None:
        raise HTTPException(status_code=404, detail="Drive not found")
    return drive


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

    application = Application(student_id=current_user.id, drive_id=drive_id)
    db.add(application)
    db.commit()
    db.refresh(application)
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


@router.get("/admin/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return {
        "total_drives": db.query(Drive).count(),
        "total_applications": db.query(Application).count(),
        "shortlisted": db.query(Application).filter(Application.status == "Shortlisted").count(),
        "selected": db.query(Application).filter(Application.status == "Selected").count(),
    }
