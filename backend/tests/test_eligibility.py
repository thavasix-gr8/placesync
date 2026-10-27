from datetime import datetime, timedelta
from types import SimpleNamespace

from app.eligibility import check_eligibility


def make_student(**changes):
    student = {"cgpa": 8.0, "arrears": 0, "department": "IT", "batch": "2026"}
    student.update(changes)
    return SimpleNamespace(**student)


def make_drive(**changes):
    drive = {
        "min_cgpa": 7.0,
        "max_arrears": 0,
        "allowed_departments": "IT,CSE",
        "batch": "2026",
        "deadline": datetime.now() + timedelta(days=1),
    }
    drive.update(changes)
    return SimpleNamespace(**drive)


def test_eligible_student_passes_all_rules():
    eligible, reasons = check_eligibility(make_student(), make_drive())
    assert eligible is True
    assert reasons == []


def test_low_cgpa_fails():
    eligible, reasons = check_eligibility(make_student(cgpa=6.9), make_drive())
    assert eligible is False
    assert "CGPA below 7" in reasons


def test_too_many_arrears_fails():
    eligible, reasons = check_eligibility(make_student(arrears=1), make_drive())
    assert eligible is False
    assert "Arrears above the limit (max 0)" in reasons


def test_wrong_department_fails():
    eligible, reasons = check_eligibility(make_student(department="ECE"), make_drive())
    assert eligible is False
    assert "Department not eligible" in reasons


def test_wrong_batch_fails():
    eligible, reasons = check_eligibility(make_student(batch="2025"), make_drive())
    assert eligible is False
    assert "Batch not eligible" in reasons


def test_passed_deadline_fails():
    eligible, reasons = check_eligibility(make_student(), make_drive(deadline=datetime.now() - timedelta(days=1)))
    assert eligible is False
    assert "Applications closed" in reasons


def test_multiple_failures_return_all_reasons():
    eligible, reasons = check_eligibility(
        make_student(cgpa=6.0, arrears=2, department="ECE", batch="2025"),
        make_drive(deadline=datetime.now() - timedelta(days=1)),
    )
    assert eligible is False
    assert len(reasons) == 5
