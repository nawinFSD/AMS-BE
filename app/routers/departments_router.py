from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import Department, Student, Faculty, Subject, UserRole
from app.schemas.schemas import DepartmentCreate, DepartmentUpdate, DepartmentResponse, BulkDeletePayload
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/departments", tags=["Departments Management"])

@router.get("", response_model=dict)
def get_departments(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Department)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((Department.name.ilike(search_filter)) | (Department.code.ilike(search_filter)))

    total = query.count()

    column = getattr(Department, sort_by, Department.id)
    if sort_order.lower() == "desc":
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    departments = query.offset((page - 1) * limit).limit(limit).all()

    # Compute metrics (total students, total faculty, total subjects)
    result_items = []
    for dept in departments:
        total_students = db.query(Student).filter(Student.department_id == dept.id).count()
        total_faculty = db.query(Faculty).filter(Faculty.department_id == dept.id).count()
        total_subjects = db.query(Subject).filter(Subject.department_id == dept.id).count()

        item_data = DepartmentResponse.from_orm(dept)
        item_data.total_students = total_students
        item_data.total_faculty = total_faculty
        item_data.total_subjects = total_subjects
        result_items.append(item_data)

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit if total > 0 else 1
    }

@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    total_students = db.query(Student).filter(Student.department_id == dept.id).count()
    total_faculty = db.query(Faculty).filter(Faculty.department_id == dept.id).count()
    total_subjects = db.query(Subject).filter(Subject.department_id == dept.id).count()

    res = DepartmentResponse.from_orm(dept)
    res.total_students = total_students
    res.total_faculty = total_faculty
    res.total_subjects = total_subjects
    return res

@router.post("", response_model=DepartmentResponse)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    existing = db.query(Department).filter(Department.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")

    dept = Department(
        name=data.name, 
        code=data.code, 
        hod_name=data.hod_name or "Dr. Alan Turing",
        description=data.description
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    if data.name is not None: dept.name = data.name
    if data.code is not None: dept.code = data.code
    if data.hod_name is not None: dept.hod_name = data.hod_name
    if data.description is not None: dept.description = data.description

    db.commit()
    db.refresh(dept)
    return dept

@router.delete("/{dept_id}")
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    # Dependency check: prevent deletion if students exist
    student_count = db.query(Student).filter(Student.department_id == dept.id).count()
    if student_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete Department '{dept.name}'. There are {student_count} active students enrolled. Reassign students first."
        )

    db.delete(dept)
    db.commit()
    return {"message": f"Department '{dept.name}' deleted successfully"}

@router.post("/bulk-delete")
def bulk_delete_departments(
    payload: BulkDeletePayload,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.ADMIN.value]))
):
    # Check for student dependencies in bulk list
    dept_with_students = (
        db.query(Department.name)
        .join(Student, Student.department_id == Department.id)
        .filter(Department.id.in_(payload.ids))
        .first()
    )

    if dept_with_students:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete. Department '{dept_with_students[0]}' has enrolled students."
        )

    db.query(Department).filter(Department.id.in_(payload.ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Successfully deleted {len(payload.ids)} departments"}
