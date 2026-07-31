from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import Student, User, UserRole
from app.schemas.schemas import StudentCreate, StudentUpdate, StudentResponse, BulkDeletePayload
from app.utils.security import get_password_hash
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/students", tags=["Students Management"])

@router.get("", response_model=dict)
def get_students(
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    course_id: Optional[int] = None,
    semester: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Student).join(User)
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if course_id:
        query = query.filter(Student.course_id == course_id)
    if semester:
        query = query.filter(Student.semester == semester)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((User.name.ilike(search_filter)) | (Student.roll_number.ilike(search_filter)) | (User.email.ilike(search_filter)))

    total = query.count()

    column = getattr(Student, sort_by, Student.id)
    if sort_order.lower() == "desc":
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    items = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [StudentResponse.from_orm(item) for item in items],
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit if total > 0 else 1
    }

@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.post("", response_model=StudentResponse)
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    # Validation: Duplicate Email Check
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail=f"Duplicate Email: Student with email '{data.email}' already exists.")

    # Validation: Duplicate Roll Number Check
    existing_roll = db.query(Student).filter(Student.roll_number == data.roll_number).first()
    if existing_roll:
        raise HTTPException(status_code=400, detail=f"Duplicate Roll Number: Student with roll number '{data.roll_number}' already exists.")

    new_user = User(
        name=data.name,
        email=data.email,
        hashed_password=get_password_hash(data.password or "Student@123"),
        role=UserRole.STUDENT.value,
        phone=data.phone,
        profileImage=data.profileImage or "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&q=80&w=256"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_student = Student(
        user_id=new_user.id,
        roll_number=data.roll_number,
        department_id=data.department_id,
        course_id=data.course_id,
        semester=data.semester or "Semester 4",
        section=data.section or "Section A",
        parent_name=data.parent_name,
        parent_phone=data.parent_phone,
        batch_year=data.batch_year or 2024,
        current_gpa=data.current_gpa or 3.5,
        assignment_score=data.assignment_score or 85.0,
        internal_marks=data.internal_marks or 80.0
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student

@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Duplicate check for email if changing
    if data.email and data.email != student.user.email:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Duplicate Email: '{data.email}' is already in use.")
        student.user.email = data.email

    # Duplicate check for roll number if changing
    if data.roll_number and data.roll_number != student.roll_number:
        existing = db.query(Student).filter(Student.roll_number == data.roll_number).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Duplicate Roll Number: '{data.roll_number}' is already assigned.")
        student.roll_number = data.roll_number

    if data.name is not None: student.user.name = data.name
    if data.phone is not None: student.user.phone = data.phone
    if data.profileImage is not None: student.user.profileImage = data.profileImage
    if data.department_id is not None: student.department_id = data.department_id
    if data.course_id is not None: student.course_id = data.course_id
    if data.semester is not None: student.semester = data.semester
    if data.section is not None: student.section = data.section
    if data.parent_name is not None: student.parent_name = data.parent_name
    if data.parent_phone is not None: student.parent_phone = data.parent_phone
    if data.current_gpa is not None: student.current_gpa = data.current_gpa
    if data.isActive is not None: student.user.isActive = data.isActive

    db.commit()
    db.refresh(student)
    return student

@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    user = db.query(User).filter(User.id == student.user_id).first()

    db.delete(student)
    if user:
        db.delete(user)

    db.commit()
    return {"message": "Student deleted successfully"}

@router.post("/bulk-delete")
def bulk_delete_students(
    payload: BulkDeletePayload,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    students = db.query(Student).filter(Student.id.in_(payload.ids)).all()
    user_ids = [s.user_id for s in students]

    db.query(Student).filter(Student.id.in_(payload.ids)).delete(synchronize_session=False)
    if user_ids:
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)

    db.commit()
    return {"message": f"Successfully deleted {len(payload.ids)} students"}
