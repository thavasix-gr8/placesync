from datetime import datetime, timedelta

from . import models
from .auth import hash_password
from .database import SessionLocal, engine
from .migrations import upgrade_microsoft_identity

upgrade_microsoft_identity(engine.url.database)
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()
now = datetime.utcnow()

# company, job role, description, days until deadline, min cgpa, max arrears, departments, batch
drives = [
    ("Zoho", "Software Developer", "Product development team in Chennai.", 20, 7.5, 0, "IT,CSE", 2024),
    ("TCS", "System Engineer", "Ninja hiring for fresh graduates.", 15, 6.0, 2, "IT,CSE,ECE,EEE", 2024),
    ("Infosys", "Systems Specialist", "Open to all departments.", 25, 6.5, 1, "", 2024),
    ("Cognizant", "Programmer Analyst Trainee", "GenC hiring drive.", 10, 6.0, 3, "", 2024),
    ("Freshworks", "Product Engineer", "SaaS product team, strong coding round.", 30, 8.0, 0, "IT,CSE", 2024),
    ("Wipro", "Project Engineer", "Open to all batches.", 12, 6.0, 2, "", None),
    ("Accenture", "Associate Software Engineer", "Deadline already passed (demo).", -5, 6.5, 1, "IT,CSE,ECE", 2024),
]

# name, email, register number, department, batch, cgpa, arrears
students = [
    ("Arun Kumar", "arun@test.com", "3122245002101", "IT", 2024, 8.6, 0),
    ("Priya S", "priya@test.com", "3122245002102", "CSE", 2024, 7.8, 0),
    ("Karthik R", "karthik@test.com", "3122245002103", "IT", 2024, 7.1, 1),
    ("Divya M", "divya@test.com", "3122245002104", "ECE", 2024, 6.4, 2),
    ("Rahul V", "rahul@test.com", "3122245002105", "IT", 2024, 6.9, 0),
    ("Meena L", "meena@test.com", "3122245002106", "CSE", 2024, 9.1, 0),
]

# student email, company, status
applications = [
    ("arun@test.com", "Zoho", "Selected"),
    ("priya@test.com", "Zoho", "Shortlisted"),
    ("meena@test.com", "Zoho", "Applied"),
    ("arun@test.com", "Freshworks", "Shortlisted"),
    ("meena@test.com", "Freshworks", "Applied"),
    ("arun@test.com", "TCS", "Applied"),
    ("priya@test.com", "TCS", "Rejected"),
    ("karthik@test.com", "TCS", "Shortlisted"),
    ("divya@test.com", "TCS", "Applied"),
    ("rahul@test.com", "TCS", "Applied"),
    ("karthik@test.com", "Infosys", "Applied"),
    ("rahul@test.com", "Infosys", "Rejected"),
    ("meena@test.com", "Infosys", "Selected"),
    ("divya@test.com", "Cognizant", "Applied"),
    ("rahul@test.com", "Cognizant", "Shortlisted"),
]

# Add drives (skip if the same company and role already exist)
for company, role, desc, days, cgpa, arrears, depts, batch in drives:
    exists = db.query(models.Drive).filter(
        models.Drive.company == company, models.Drive.job_role == role
    ).first()
    if not exists:
        db.add(models.Drive(
            company=company, job_role=role, description=desc,
            deadline=now + timedelta(days=days),
            min_cgpa=cgpa, max_arrears=arrears,
            allowed_departments=depts, batch=batch,
        ))
db.commit()

# Add students (password for all of them is test123)
for name, email, reg, dept, batch, cgpa, arrears in students:
    exists = db.query(models.User).filter(models.User.email == email).first()
    if not exists:
        db.add(models.User(
            name=name, email=email, password_hash=hash_password("test123"),
            role="student", register_number=reg, department=dept,
            batch=batch, cgpa=cgpa, arrears=arrears,
        ))
db.commit()

# Add applications
for email, company, status in applications:
    student = db.query(models.User).filter(models.User.email == email).first()
    drive = db.query(models.Drive).filter(models.Drive.company == company).first()
    if student and drive:
        exists = db.query(models.Application).filter(
            models.Application.student_id == student.id,
            models.Application.drive_id == drive.id,
        ).first()
        if not exists:
            db.add(models.Application(
                student_id=student.id, drive_id=drive.id, status=status
            ))
db.commit()

print("Drives:", db.query(models.Drive).count())
print("Users:", db.query(models.User).count())
print("Applications:", db.query(models.Application).count())
db.close()
