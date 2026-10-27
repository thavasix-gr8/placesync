from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="student")
    register_number = Column(String, unique=True, index=True, nullable=False)
    department = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    cgpa = Column(Float, nullable=False)
    arrears = Column(Integer, nullable=False, default=0)

    applications = relationship("Application", back_populates="student")
    microsoft_identity = relationship("MicrosoftIdentity", back_populates="user", uselist=False)
    resumes = relationship("StudentResume", back_populates="student")
    notifications = relationship("Notification", back_populates="user")
    created_announcements = relationship(
        "Announcement", back_populates="created_by", foreign_keys="Announcement.created_by_id"
    )


class MicrosoftIdentity(Base):
    __tablename__ = "microsoft_identities"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    __table_args__ = (UniqueConstraint("tenant_id", "object_id"),)
    user = relationship("User", back_populates="microsoft_identity")


class MicrosoftAuthNonce(Base):
    __tablename__ = "microsoft_auth_nonces"

    nonce = Column(String, primary_key=True)
    expires_at = Column(DateTime, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    drive_id = Column(Integer, ForeignKey("drives.id", ondelete="SET NULL"), nullable=True, index=True)

    created_by = relationship("User", back_populates="created_announcements", foreign_keys=[created_by_id])
    drive = relationship("Drive", back_populates="announcements")


class StudentResume(Base):
    __tablename__ = "student_resumes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    storage_name = Column(String, nullable=False, unique=True)
    original_filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    student = relationship("User", back_populates="resumes")
    applications = relationship("Application", back_populates="resume")


class Drive(Base):
    __tablename__ = "drives"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False)
    job_role = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=False)
    min_cgpa = Column(Float, nullable=False)
    max_arrears = Column(Integer, nullable=False)
    allowed_departments = Column(String, default="", nullable=False)
    batch = Column(String, default="", nullable=False)
    applicant_count = Column(Integer, nullable=False, default=0, server_default="0")
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    applications = relationship("Application", back_populates="drive")
    created_by = relationship("User", foreign_keys=[created_by_id])
    announcements = relationship("Announcement", back_populates="drive")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=False)
    status = Column(String, nullable=False, default="Applied")
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resume_id = Column(Integer, ForeignKey("student_resumes.id"), nullable=True)

    student = relationship("User", back_populates="applications")
    drive = relationship("Drive", back_populates="applications")
    resume = relationship("StudentResume", back_populates="applications")
