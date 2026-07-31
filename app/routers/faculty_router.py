from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import Faculty, User, UserRole
from app.schemas.schemas import FacultyCreate, FacultyUpdate, FacultyResponse, BulkDeletePayload
from app.utils.security import get_password_hash
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/faculty", tags=["Faculty Management"])

@router.get("", response_model=dict)
def get_faculty(
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Faculty).join(User)
    if department_id:
        query = query.filter(Faculty.department_id == department_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((User.name.ilike(search_filter)) | (Faculty.employee_id.ilike(search_filter)) | (User.email.ilike(search_filter)))

    total = query.count()

    column = getattr(Faculty, sort_by, Faculty.id)
    if sort_order.lower() == "desc":
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    items = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [FacultyResponse.from_orm(item) for item in items],
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit if total > 0 else 1
    }

@router.get("/{faculty_id}", response_model=FacultyResponse)
def get_faculty_member(faculty_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    fac = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Faculty member not found")
    return fac

@router.post("", response_model=FacultyResponse)
def create_faculty_member(
    data: FacultyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    existing_emp = db.query(Faculty).filter(Faculty.employee_id == data.employee_id).first()
    if existing_emp:
        raise HTTPException(status_code=400, detail="Employee ID already assigned")

    new_user = User(
        name=data.name,
        email=data.email,
        hashed_password=get_password_hash(data.password or "Faculty@123"),
        role=UserRole.FACULTY.value,
        phone=data.phone,
        profileImage=data.profileImage or "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=256"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_faculty = Faculty(
        user_id=new_user.id,
        employee_id=data.employee_id,
        department_id=data.department_id,
        phone=data.phone,
        assigned_subjects=data.assigned_subjects or "Data Structures, Database Systems",
        assigned_classes=data.assigned_classes or "CS-A, CS-B"
    )
    db.add(new_faculty)
    db.commit()
    db.refresh(new_faculty)

    return new_faculty

@router.put("/{faculty_id}", response_model=FacultyResponse)
def update_faculty_member(
    faculty_id: int,
    data: FacultyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    fac = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Faculty member not found")

    if data.name is not None: fac.user.name = data.name
    if data.email is not None: fac.user.email = data.email
    if data.employee_id is not None: fac.employee_id = data.employee_id
    if data.department_id is not None: fac.department_id = data.department_id
    if data.phone is not None: fac.phone = data.phone; fac.user.phone = data.phone
    if data.profileImage is not None: fac.user.profileImage = data.profileImage
    if data.assigned_subjects is not None: fac.assigned_subjects = data.assigned_subjects
    if data.assigned_classes is not None: fac.assigned_classes = data.assigned_classes

    db.commit()
    db.refresh(fac)
    return fac

@router.delete("/{faculty_id}")
def delete_faculty_member(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    fac = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Faculty member not found")
    user = db.query(User).filter(User.id == fac.user_id).first()

    db.delete(fac)
    if user:
        db.delete(user)

    db.commit()
    return {"message": "Faculty member deleted successfully"}

@router.post("/bulk-delete")
def bulk_delete_faculty(
    payload: BulkDeletePayload,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    faculty_members = db.query(Faculty).filter(Faculty.id.in_(payload.ids)).all()
    user_ids = [f.user_id for f in faculty_members]

    db.query(Faculty).filter(Faculty.id.in_(payload.ids)).delete(synchronize_session=False)
    if user_ids:
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)

    db.commit()
    return {"message": f"Successfully deleted {len(payload.ids)} faculty members"}
