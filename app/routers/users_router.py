from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import User, Student, Faculty, Department, Course, UserRole
from app.schemas.schemas import StudentResponse, FacultyResponse, UserCreate
from app.utils.security import get_password_hash
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/users", tags=["Users & Profiles"])

@router.get("/students", response_model=List[StudentResponse])
def get_all_students(
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Student).join(User)
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((User.name.like(search_filter)) | (Student.roll_number.like(search_filter)))
    
    return query.all()

@router.get("/faculty", response_model=List[FacultyResponse])
def get_all_faculty(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Faculty).join(User)
    if department_id:
        query = query.filter(Faculty.department_id == department_id)
    return query.all()

@router.post("/students", response_model=StudentResponse)
def create_student(
    name: str,
    email: str,
    roll_number: str,
    department_id: int,
    course_id: int,
    password: str = "Student@123",
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        name=name,
        email=email,
        hashed_password=get_password_hash(password),
        role=UserRole.STUDENT.value
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_student = Student(
        user_id=new_user.id,
        roll_number=roll_number,
        department_id=department_id,
        course_id=course_id,
        batch_year=2024,
        current_gpa=3.6,
        assignment_score=85.0,
        internal_marks=80.0
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student
