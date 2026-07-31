from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import Course, Department, UserRole
from app.schemas.schemas import CourseCreate, CourseUpdate, CourseResponse, BulkDeletePayload
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/courses", tags=["Courses Management"])

@router.get("", response_model=dict)
def get_courses(
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Course)
    if department_id:
        query = query.filter(Course.department_id == department_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((Course.name.ilike(search_filter)) | (Course.code.ilike(search_filter)))

    total = query.count()

    column = getattr(Course, sort_by, Course.id)
    if sort_order.lower() == "desc":
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    items = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [CourseResponse.from_orm(item) for item in items],
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit if total > 0 else 1
    }

@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.post("", response_model=CourseResponse)
def create_course(
    data: CourseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    existing = db.query(Course).filter(Course.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course code already exists")

    dept = db.query(Department).filter(Department.id == data.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    course = Course(name=data.name, code=data.code, department_id=data.department_id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if data.name is not None: course.name = data.name
    if data.code is not None: course.code = data.code
    if data.department_id is not None: course.department_id = data.department_id

    db.commit()
    db.refresh(course)
    return course

@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"message": f"Course '{course.name}' deleted successfully"}

@router.post("/bulk-delete")
def bulk_delete_courses(
    payload: BulkDeletePayload,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    db.query(Course).filter(Course.id.in_(payload.ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Successfully deleted {len(payload.ids)} courses"}
