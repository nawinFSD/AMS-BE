from app.database.connection import SessionLocal, engine, Base
from app.models.domain import (
    User, Student, Faculty, Department, Course, Subject, 
    Attendance, Notification, AttendanceLog, StudentRiskPrediction, 
    UserRole, AttendanceStatus, AttendanceType, RiskLevel
)
from app.utils.security import get_password_hash
from datetime import datetime, timedelta
import random

def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    print("Seeding database with normalized enterprise schema records...")

    # 1. Departments
    dept_cs = Department(name="Computer Science & Engineering", code="CSE", hod_name="Dr. Ramanujan Krishnan", description="Department of Computer Science & Artificial Intelligence")
    dept_ece = Department(name="Electronics & Communication", code="ECE", hod_name="Dr. Subhashini Kameshwaran", description="Department of Electronics, VLSI & Communications")
    dept_it = Department(name="Information Technology", code="IT", hod_name="Dr. Soundarya Natarajan", description="Department of Software Systems & Cloud Computing")

    db.add_all([dept_cs, dept_ece, dept_it])
    db.commit()

    # 2. Courses
    course_btech_cs = Course(name="B.Tech Computer Science", code="CS-2024", department_id=dept_cs.id)
    course_btech_it = Course(name="B.Tech Information Tech", code="IT-2024", department_id=dept_it.id)
    db.add_all([course_btech_cs, course_btech_it])
    db.commit()

    # 3. Subjects
    sub_ds = Subject(name="Data Structures & Algorithms", code="CS301", course_id=course_btech_cs.id, department_id=dept_cs.id, total_classes=45)
    sub_dbms = Subject(name="Database Management Systems", code="CS302", course_id=course_btech_cs.id, department_id=dept_cs.id, total_classes=40)
    sub_ai = Subject(name="Artificial Intelligence & ML", code="CS303", course_id=course_btech_cs.id, department_id=dept_cs.id, total_classes=42)
    sub_web = Subject(name="Web Application Architecture", code="IT301", course_id=course_btech_it.id, department_id=dept_it.id, total_classes=38)

    db.add_all([sub_ds, sub_dbms, sub_ai, sub_web])
    db.commit()

    # 4. Admin User
    admin_user = User(
        name="Dr. Arumugam Sundaram",
        email="admin@smartatt.edu",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN.value,
        profileImage="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256"
    )
    db.add(admin_user)
    db.commit()

    # 5. Faculty User & Profile
    faculty_user = User(
        name="Prof. Karthik Selvam",
        email="faculty@smartatt.edu",
        hashed_password=get_password_hash("faculty123"),
        role=UserRole.FACULTY.value,
        profileImage="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=256"
    )
    db.add(faculty_user)
    db.commit()

    faculty_prof = Faculty(
        user_id=faculty_user.id,
        department_id=dept_cs.id,
        employee_id="FAC-2024-001",
        phone="+91 98765 12345"
    )
    db.add(faculty_prof)
    db.commit()

    # 6. Students
    student_user = User(
        name="Ananya Murugan",
        email="student@smartatt.edu",
        hashed_password=get_password_hash("student123"),
        role=UserRole.STUDENT.value,
        profileImage="https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&q=80&w=256"
    )
    db.add(student_user)
    db.commit()

    demo_student = Student(
        user_id=student_user.id,
        roll_number="2024-CS-001",
        department_id=dept_cs.id,
        course_id=course_btech_cs.id,
        batch_year=2024,
        current_gpa=3.85,
        assignment_score=92.0,
        internal_marks=88.5
    )
    db.add(demo_student)
    db.commit()

    additional_students_data = [
        ("Kaviya Ramanathan", "kaviya@smartatt.edu", "2024-CS-002", 3.9, 95.0, 94.0),
        ("Senthil Kumar", "senthil@smartatt.edu", "2024-CS-003", 2.4, 45.0, 48.0),
        ("Dhanush Vishwanathan", "dhanush@smartatt.edu", "2024-CS-004", 3.4, 82.0, 78.0),
        ("Elango Thangavel", "elango@smartatt.edu", "2024-IT-001", 3.1, 75.0, 70.0),
        ("Priya Swaminathan", "priya@smartatt.edu", "2024-IT-002", 2.1, 50.0, 42.0)
    ]

    student_objects = [demo_student]
    for name, email, roll, gpa, ass, idx in additional_students_data:
        u = User(
            name=name,
            email=email,
            hashed_password=get_password_hash("student123"),
            role=UserRole.STUDENT.value,
            profileImage="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256"
        )
        db.add(u)
        db.commit()

        s = Student(
            user_id=u.id,
            roll_number=roll,
            department_id=dept_cs.id if "CS" in roll else dept_it.id,
            course_id=course_btech_cs.id if "CS" in roll else course_btech_it.id,
            batch_year=2024,
            current_gpa=gpa,
            assignment_score=ass,
            internal_marks=idx
        )
        db.add(s)
        db.commit()
        student_objects.append(s)

    # 7. Attendance & AttendanceLogs
    today = datetime.utcnow()
    for student in student_objects:
        is_low_perf = student.current_gpa < 2.8
        for days_back in range(1, 10):
            date_str = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
            status_choice = random.choice([AttendanceStatus.ABSENT.value, AttendanceStatus.LATE.value]) if is_low_perf else AttendanceStatus.PRESENT.value
            
            att = Attendance(
                student_id=student.id,
                subject_id=sub_ds.id if student.course_id == course_btech_cs.id else sub_web.id,
                date=date_str,
                status=status_choice,
                type=AttendanceType.MANUAL.value,
                marked_by_faculty_id=faculty_prof.id
            )
            db.add(att)
            db.commit()
            db.refresh(att)

            log = AttendanceLog(
                attendance_id=att.id,
                action="INITIAL_RECORD",
                details=f"Marked {status_choice} by Faculty ID {faculty_prof.id}"
            )
            db.add(log)

    db.commit()

    # 8. Notifications
    notif1 = Notification(user_id=student_user.id, title="Attendance Milestone", message="Your attendance in Data Structures is currently 94.2%.")
    notif2 = Notification(user_id=student_user.id, title="Upcoming Seminar", message="Guest lecture on AI & Quantum Computing scheduled for Friday.")
    db.add_all([notif1, notif2])
    db.commit()

    # 9. StudentRiskPrediction
    for s in student_objects:
        risk_level = RiskLevel.HIGH.value if s.current_gpa < 2.5 else RiskLevel.LOW.value
        pred = StudentRiskPrediction(
            student_id=s.id,
            risk_level=risk_level,
            risk_score=0.75 if risk_level == "HIGH" else 0.12,
            recommendations="Academic advising recommended." if risk_level == "HIGH" else "Maintaining good trajectory.",
            confidence=0.96
        )
        db.add(pred)

    db.commit()
    print("Seeding complete! All 10 normalized tables populated successfully.")

if __name__ == "__main__":
    seed_database()
