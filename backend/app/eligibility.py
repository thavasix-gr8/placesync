from datetime import datetime


def check_eligibility(student, drive):
    """Check every drive rule and return readable reasons for failures."""
    reasons = []

    if student.cgpa < drive.min_cgpa:
        reasons.append(f"CGPA below {drive.min_cgpa:g}")
    if student.arrears > drive.max_arrears:
        reasons.append(f"Arrears above the limit (max {drive.max_arrears})")

    if drive.allowed_departments:
        departments = [item.strip() for item in drive.allowed_departments.split(",")]
        if student.department not in departments:
            reasons.append("Department not eligible")

    if drive.batch and student.batch != drive.batch:
        reasons.append("Batch not eligible")

    if application_deadline_passed(drive.deadline):
        reasons.append("Applications closed")

    return len(reasons) == 0, reasons


def application_deadline_passed(deadline):
    """A drive stays open for the whole calendar date shown as its deadline."""
    now = datetime.now(deadline.tzinfo) if deadline.tzinfo else datetime.now()
    return now.date() > deadline.date()
