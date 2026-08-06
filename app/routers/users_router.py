from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import User, Student, Faculty, Department, Course, UserRole
from app.schemas.schemas import StudentResponse, FacultyResponse, UserCreate, UserUpdate
from app.utils.security import get_password_hash, verify_password
from app.middleware.auth import get_current_user, require_role
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["Users & Profiles"])

class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str

@router.get("/me")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = {"user": current_user}
    if current_user.role == UserRole.STUDENT.value and current_user.student_profile:
        profile["student"] = current_user.student_profile
    if current_user.role == UserRole.FACULTY.value and current_user.faculty_profile:
        profile["faculty"] = current_user.faculty_profile
    return profile

@router.put("/me")
def update_my_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    update_data = payload.dict(exclude_unset=True)
    if "email" in update_data and update_data["email"] != current_user.email:
        existing = db.query(User).filter(User.email == update_data["email"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/change-password")
def change_password(
    payload: ChangePasswordPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@router.put("/{user_id}")
def update_user_by_admin(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN.value]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = payload.dict(exclude_unset=True)
    if "email" in update_data and update_data["email"] != user.email:
        existing = db.query(User).filter(User.email == update_data["email"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user

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
