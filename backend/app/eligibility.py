from datetime import datetime, timezone


def check_eligibility(student, drive):
    """Check every drive rule and return readable reasons for failures."""
    reasons = []

    if student.cgpa < drive.min_cgpa:
        reasons.append(f"CGPA {student.cgpa:g} is below the required {drive.min_cgpa:g}")
    if student.arrears > drive.max_arrears:
        reasons.append(f"Arrears {student.arrears} exceed the allowed {drive.max_arrears}")

    if drive.allowed_departments:
        departments = [item.strip() for item in drive.allowed_departments.split(",")]
        if student.department not in departments:
            reasons.append(f"Department {student.department} is not eligible for this drive")

    if drive.batch and student.batch != drive.batch:
        reasons.append(f"Batch {student.batch} does not match the required {drive.batch}")

    now = datetime.now(timezone.utc) if drive.deadline.tzinfo else datetime.now()
    if drive.deadline <= now:
        reasons.append("The application deadline has passed")

    return len(reasons) == 0, reasons
