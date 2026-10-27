from html.parser import HTMLParser

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import require_admin, require_student
from .database import get_db
from .models import Announcement, Drive, Notification, User
from .schemas import AnnouncementCreate, AnnouncementOut, NotificationOut

router = APIRouter(tags=["Student updates"])


class PlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = PlainTextParser()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def announcement_out(announcement: Announcement) -> dict:
    return {
        "id": announcement.id,
        "title": announcement.title,
        "message": announcement.message,
        "created_at": announcement.created_at,
        "drive_id": announcement.drive_id,
        "drive_company": announcement.drive.company if announcement.drive else None,
    }


@router.get("/notifications/me", response_model=list[NotificationOut])
def get_my_notifications(
    db: Session = Depends(get_db), current_user: User = Depends(require_student)
):
    return db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(5).all()


@router.put("/notifications/me/read")
def mark_my_notifications_read(
    db: Session = Depends(get_db), current_user: User = Depends(require_student)
):
    updated = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"updated": updated}


@router.get("/announcements", response_model=list[AnnouncementOut])
def get_student_announcements(
    db: Session = Depends(get_db), current_user: User = Depends(require_student)
):
    announcements = db.query(Announcement).order_by(
        Announcement.created_at.desc(), Announcement.id.desc()
    ).limit(5).all()
    return [announcement_out(item) for item in announcements]


@router.get("/admin/announcements", response_model=list[AnnouncementOut])
def get_admin_announcements(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    announcements = db.query(Announcement).filter(
        Announcement.created_by_id == current_user.id
    ).order_by(Announcement.created_at.desc(), Announcement.id.desc()).all()
    return [announcement_out(item) for item in announcements]


@router.post("/admin/announcements", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    title = plain_text(data.title)
    message = plain_text(data.message)
    if not title or not message:
        raise HTTPException(status_code=400, detail="Enter a title and message using plain text.")
    if data.drive_id is not None and db.query(Drive).filter(Drive.id == data.drive_id).first() is None:
        raise HTTPException(status_code=404, detail="Drive not found")

    announcement = Announcement(
        title=title,
        message=message,
        created_by_id=current_user.id,
        drive_id=data.drive_id,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement_out(announcement)


@router.delete("/admin/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()
    if announcement is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if announcement.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own announcements.")
    db.delete(announcement)
    db.commit()
    return None
