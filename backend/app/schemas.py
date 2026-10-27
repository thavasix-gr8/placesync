from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6)
    register_number: str
    department: str
    batch: str
    cgpa: float = Field(ge=0, le=10)
    arrears: int = Field(ge=0)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    register_number: str
    department: str
    batch: str
    cgpa: float
    arrears: int

    model_config = ConfigDict(from_attributes=True)


class StudentUpdate(BaseModel):
    department: str | None = None
    batch: str | None = None
    cgpa: float | None = Field(default=None, ge=0, le=10)
    arrears: int | None = Field(default=None, ge=0)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class DriveCreate(BaseModel):
    company: str
    job_role: str
    description: str
    deadline: datetime
    min_cgpa: float = Field(ge=0, le=10)
    max_arrears: int = Field(ge=0)
    allowed_departments: str = ""
    batch: str = ""


class DriveUpdate(BaseModel):
    company: str | None = None
    job_role: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    min_cgpa: float | None = Field(default=None, ge=0, le=10)
    max_arrears: int | None = Field(default=None, ge=0)
    allowed_departments: str | None = None
    batch: str | None = None


class DriveOut(DriveCreate):
    id: int
    applicant_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ApplicationOut(BaseModel):
    id: int
    student_id: int
    drive_id: int
    status: str
    applied_at: datetime
    resume_id: int | None = None
    drive: DriveOut

    model_config = ConfigDict(from_attributes=True)


class ApplicationApplicantOut(BaseModel):
    id: int
    student_id: int
    drive_id: int
    status: str
    applied_at: datetime
    resume_id: int | None = None
    student: UserOut

    model_config = ConfigDict(from_attributes=True)


class ApplicationStatusUpdate(BaseModel):
    status: Literal["Applied", "Shortlisted", "Rejected", "Selected"]


class BulkApplicationStatusUpdate(BaseModel):
    application_ids: list[int] = Field(min_length=1)
    status: Literal["Shortlisted", "Selected", "Rejected"]


class StatsOut(BaseModel):
    total_drives: int
    total_applications: int
    shortlisted: int
    selected: int


class ResumeOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime


class NotificationOut(BaseModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    drive_id: int | None = None


class AnnouncementOut(BaseModel):
    id: int
    title: str
    message: str
    created_at: datetime
    drive_id: int | None = None
    drive_company: str | None = None
