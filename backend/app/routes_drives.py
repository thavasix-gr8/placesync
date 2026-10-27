from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import get_current_user, require_admin, require_student
from .database import get_db
from .eligibility import application_deadline_passed, check_eligibility
from .models import Application, Drive, User
from .schemas import DriveCreate, DriveOut, DriveUpdate, StudentUpdate, UserOut

router = APIRouter(tags=["Drives"])


def get_drive_or_404(drive_id: int, db: Session) -> Drive:
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if drive is None:
        raise HTTPException(status_code=404, detail="Drive not found")
    return drive


@router.post("/drives", response_model=DriveOut, status_code=status.HTTP_201_CREATED)
def create_drive(data: DriveCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    drive = Drive(**data.model_dump(), created_by_id=current_user.id)
    db.add(drive)
    db.commit()
    db.refresh(drive)
    return drive


@router.get("/drives")
def get_drives(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    drives = db.query(Drive).order_by(Drive.deadline).all()
    if current_user.role == "admin":
        return [DriveOut.model_validate(drive).model_dump(mode="json") for drive in drives]

    results = []
    for drive in drives:
        eligible, reasons = check_eligibility(current_user, drive)
        drive_data = DriveOut.model_validate(drive).model_dump(mode="json")
        drive_data["eligible"] = eligible
        drive_data["reasons"] = reasons
        drive_data["application_closed"] = application_deadline_passed(drive.deadline)
        results.append(drive_data)
    return results


@router.put("/drives/{drive_id}", response_model=DriveOut)
def update_drive(drive_id: int, data: DriveUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    drive = get_drive_or_404(drive_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(drive, field, value)
    db.commit()
    db.refresh(drive)
    return drive


@router.delete("/drives/{drive_id}")
def delete_drive(drive_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    drive = get_drive_or_404(drive_id, db)
    db.query(Application).filter(Application.drive_id == drive_id).delete()
    db.delete(drive)
    db.commit()
    return {"message": "Drive deleted"}


@router.put("/me", response_model=UserOut)
def update_me(data: StudentUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_student)):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
