from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.domain import Student, Faculty, Department, Course, Subject, Attendance, AttendanceStatus, User, Notification, AttendanceLog
from app.middleware.auth import get_current_user
from datetime import datetime, timedelta
from collections import OrderedDict

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Dashboard Data"])


def _status_rate(rows, status):
    if not rows:
        return 0
    return round(100 * sum(1 for r in rows if r.status == status) / len(rows), 1)


def _recent_dates(days):
    base = datetime.utcnow().date()
    return [(base - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


@router.get("/dashboard-summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Live Database Counts
    total_students = db.query(Student).count()
    total_faculty = db.query(Faculty).count()
    total_departments = db.query(Department).count()
    total_courses = db.query(Course).count()
    total_subjects = db.query(Subject).count()

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today_attendances = db.query(Attendance).filter(Attendance.date == today_str).all()
    today_present = sum(1 for a in today_attendances if a.status == AttendanceStatus.PRESENT.value)
    today_absent = sum(1 for a in today_attendances if a.status == AttendanceStatus.ABSENT.value)
    today_late = sum(1 for a in today_attendances if a.status == AttendanceStatus.LATE.value)
    today_od = sum(1 for a in today_attendances if a.status == AttendanceStatus.OD.value)

    # ---- Monthly attendance trend (last 6 months) ----
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    now = datetime.utcnow()
    monthly_attendance = []
    all_att = db.query(Attendance).all()
    for offset in range(5, -1, -1):
        year, month = now.year, now.month - offset
        while month <= 0:
            month += 12
            year -= 1
        rows = [a for a in all_att if a.date[:7] == f"{year}-{month:02d}"]
        present = [a for a in rows if a.status in (AttendanceStatus.PRESENT.value, AttendanceStatus.OD.value)]
        rate = round(100 * len(present) / len(rows), 1) if rows else 0
        monthly_attendance.append({"month": month_labels[month - 1], "attendance": rate})

    # ---- Department comparison ----
    department_comparison = []
    departments = db.query(Department).all()
    dept_attendance = db.query(Attendance).join(Student).filter(Student.department_id != None).all()
    for dept in departments:
        rows = [a for a in dept_attendance if a.student.department_id == dept.id]
        rate = _status_rate(rows, AttendanceStatus.PRESENT.value)
        department_comparison.append({
            "dept": dept.code or dept.name,
            "attendance": rate,
            "students": len(set(a.student_id for a in rows))
        })

    # ---- Weekly attendance trend (last 8 weeks) ----
    attendance_trend = []
    today = now.date()
    for week_offset in range(7, -1, -1):
        week_start = today - timedelta(days=today.weekday() + 7 * week_offset)
        week_end = week_start + timedelta(days=6)
        rows = [a for a in all_att if week_start.strftime("%Y-%m-%d") <= a.date <= week_end.strftime("%Y-%m-%d")]
        present = [a for a in rows if a.status in (AttendanceStatus.PRESENT.value, AttendanceStatus.OD.value)]
        rate = round(100 * len(present) / len(rows), 1) if rows else 0
        attendance_trend.append({"week": f"W{8 - week_offset}", "rate": rate})

    # ---- Subject performance ----
    subject_performance = []
    subjects = db.query(Subject).all()
    for subject in subjects:
        rows = [a for a in all_att if a.subject_id == subject.id]
        rate = _status_rate(rows, AttendanceStatus.PRESENT.value)
        subject_performance.append({
            "subject": subject.code or subject.name,
            "rate": rate,
            "total_classes": len(rows)
        })

    # ---- Daily attendance (last 7 days) ----
    daily_attendance = []
    for date_str in reversed(_recent_dates(7)):
        rows = [a for a in all_att if a.date == date_str]
        present = sum(1 for a in rows if a.status in (AttendanceStatus.PRESENT.value, AttendanceStatus.OD.value))
        absent = sum(1 for a in rows if a.status == AttendanceStatus.ABSENT.value)
        late = sum(1 for a in rows if a.status == AttendanceStatus.LATE.value)
        day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][datetime.strptime(date_str, "%Y-%m-%d").weekday()]
        daily_attendance.append({"day": day_name, "present": present, "absent": absent, "late": late})

    # ---- Status distribution today ----
    total_today = len(today_attendances)
    attendance_distribution = [
        {"status": "PRESENT", "value": today_present},
        {"status": "ABSENT", "value": today_absent},
        {"status": "LATE", "value": today_late},
        {"status": "OD", "value": today_od},
        {"status": "LEAVE", "value": sum(1 for a in today_attendances if a.status == AttendanceStatus.LEAVE.value)},
    ]

    overall_rate = _status_rate(all_att, AttendanceStatus.PRESENT.value)

    # ---- Recent activities from attendance logs ----
    logs = db.query(AttendanceLog).order_by(AttendanceLog.timestamp.desc()).limit(8).all()
    recent_activities = []
    for log in logs:
        recent_activities.append({
            "id": log.id,
            "title": log.details or log.action,
            "time": log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "",
            "type": "ATTENDANCE",
        })
    if not recent_activities:
        recent_activities = []

    # ---- Latest notifications for current user ----
    latest_notifications = db.query(Notification).filter(Notification.user_id == current_user.id) \
        .order_by(Notification.createdAt.desc()).limit(5).all()
    latest_notifications = [
        {
            "id": n.id,
            "title": n.title,
            "time": n.createdAt.strftime("%Y-%m-%d %H:%M") if n.createdAt else "",
            "is_read": n.is_read,
        } for n in latest_notifications
    ]

    return {
        "kpis": {
            "total_students": total_students,
            "total_faculty": total_faculty,
            "today_present": today_present,
            "today_absent": today_absent,
            "today_late": today_late,
            "today_od": today_od,
            "total_departments": total_departments,
            "total_courses": total_courses,
            "total_subjects": total_subjects,
            "overall_attendance_rate": overall_rate,
            "attendance_distribution": attendance_distribution,
        },
        "charts": {
            "monthly_attendance": monthly_attendance,
            "department_comparison": department_comparison,
            "attendance_trend": attendance_trend,
            "subject_performance": subject_performance,
            "daily_attendance": daily_attendance,
        },
        "recent_activities": recent_activities,
        "latest_notifications": latest_notifications,
    }
