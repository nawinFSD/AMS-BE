from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database.connection import get_db
from app.models.domain import Attendance, Student, Subject, User, Faculty, UserRole, Notification
from app.schemas.schemas import AttendanceMark, AttendanceResponse
from app.middleware.auth import get_current_user, require_role
from app.routers.ws_router import ws_manager

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

@router.post("/mark", response_model=AttendanceResponse)
async def mark_attendance(
    data: AttendanceMark,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.FACULTY.value, UserRole.ADMIN.value]))
):
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    faculty_id = None
    if current_user.role == UserRole.FACULTY.value and current_user.faculty_profile:
        faculty_id = current_user.faculty_profile.id

    # Check if attendance already recorded for this date/subject/student
    existing = db.query(Attendance).filter(
        Attendance.student_id == data.student_id,
        Attendance.subject_id == data.subject_id,
        Attendance.date == data.date
    ).first()

    if existing:
        existing.status = data.status
        existing.type = data.type or "MANUAL"
        existing.timestamp = datetime.utcnow()
        attendance_record = existing
    else:
        attendance_record = Attendance(
            student_id=data.student_id,
            subject_id=data.subject_id,
            date=data.date,
            status=data.status,
            type=data.type or "MANUAL",
            marked_by_faculty_id=faculty_id,
            timestamp=datetime.utcnow()
        )
        db.add(attendance_record)

    db.commit()
    db.refresh(attendance_record)

    # Add notification for student
    notif = Notification(
        user_id=student.user_id,
        title="Attendance Updated",
        message=f"Your attendance for {subject.name} on {data.date} was marked as {data.status}."
    )
    db.add(notif)
    db.commit()

    # Real-time WebSocket Broadcast update
    await ws_manager.broadcast({
        "type": "ATTENDANCE_UPDATED",
        "student_id": student.id,
        "student_name": student.user.name,
        "subject_name": subject.name,
        "status": data.status,
        "date": data.date,
        "timestamp": datetime.utcnow().isoformat()
    })

    return attendance_record

@router.get("/history", response_model=List[AttendanceResponse])
def get_attendance_history(
    student_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Attendance)

    # If student role, enforce filtering for their own student_id
    if current_user.role == UserRole.STUDENT.value:
        if not current_user.student_profile:
            return []
        query = query.filter(Attendance.student_id == current_user.student_profile.id)
    elif student_id:
        query = query.filter(Attendance.student_id == student_id)

    if subject_id:
        query = query.filter(Attendance.subject_id == subject_id)
    if date:
        query = query.filter(Attendance.date == date)

    return query.order_by(Attendance.timestamp.desc()).limit(100).all()
