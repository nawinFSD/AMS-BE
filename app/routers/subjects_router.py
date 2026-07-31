from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import Subject, Course, Department, UserRole
from app.schemas.schemas import SubjectCreate, SubjectUpdate, SubjectResponse, BulkDeletePayload
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/subjects", tags=["Subjects Management"])

@router.get("", response_model=dict)
def get_subjects(
    search: Optional[str] = None,
    course_id: Optional[int] = None,
    department_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Subject)
    if course_id:
        query = query.filter(Subject.course_id == course_id)
    if department_id:
        query = query.filter(Subject.department_id == department_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((Subject.name.ilike(search_filter)) | (Subject.code.ilike(search_filter)))

    total = query.count()

    column = getattr(Subject, sort_by, Subject.id)
    if sort_order.lower() == "desc":
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    items = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [SubjectResponse.from_orm(item) for item in items],
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit if total > 0 else 1
    }

@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.post("", response_model=SubjectResponse)
def create_subject(
    data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    existing = db.query(Subject).filter(Subject.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject code already exists")

    subject = Subject(
        name=data.name,
        code=data.code,
        course_id=data.course_id,
        department_id=data.department_id,
        total_classes=data.total_classes or 40
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: int,
    data: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if data.name is not None: subject.name = data.name
    if data.code is not None: subject.code = data.code
    if data.course_id is not None: subject.course_id = data.course_id
    if data.department_id is not None: subject.department_id = data.department_id
    if data.total_classes is not None: subject.total_classes = data.total_classes

    db.commit()
    db.refresh(subject)
    return subject

@router.delete("/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(subject)
    db.commit()
    return {"message": f"Subject '{subject.name}' deleted successfully"}

@router.post("/bulk-delete")
def bulk_delete_subjects(
    payload: BulkDeletePayload,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    db.query(Subject).filter(Subject.id.in_(payload.ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Successfully deleted {len(payload.ids)} subjects"}
