from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import Student, StudentRiskPrediction, UserRole
from app.schemas.schemas import RiskInput, RiskOutput
from app.ml.risk_model import risk_predictor
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/ai", tags=["AI Academic Risk Predictor"])

@router.post("/predict-risk", response_model=RiskOutput)
def predict_student_risk(input_data: RiskInput):
    result = risk_predictor.predict_risk(
        attendance_pct=input_data.attendance_pct,
        assignment_score=input_data.assignment_score,
        internal_marks=input_data.internal_marks,
        previous_gpa=input_data.previous_gpa
    )
    return result

@router.get("/student-risk/{student_id}", response_model=RiskOutput)
def get_student_risk_by_id(student_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Compute mock attendance % for student
    total_att = len(student.attendances) if student.attendances else 40
    present_att = sum(1 for a in student.attendances if a.status in ["PRESENT", "OD"]) if student.attendances else 34
    att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 85.0

    result = risk_predictor.predict_risk(
        attendance_pct=att_pct,
        assignment_score=student.assignment_score or 80.0,
        internal_marks=student.internal_marks or 75.0,
        previous_gpa=student.current_gpa or 3.5
    )

    # Save to database
    prediction_record = StudentRiskPrediction(
        student_id=student.id,
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        recommendations="; ".join(result["recommendations"])
    )
    db.add(prediction_record)
    db.commit()

    return result
