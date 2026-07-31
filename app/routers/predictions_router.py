from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database.connection import get_db
from app.models.domain import Student, StudentRiskPrediction, RiskLevel
from app.middleware.auth import get_current_user
import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

router = APIRouter(prefix="/api/predictions", tags=["AI Risk Predictions"])

class PredictionInputPayload(BaseModel):
    student_id: Optional[int] = 1
    attendance_pct: float
    internal_marks: float
    assignment_score: float
    previous_gpa: float
    study_hours: Optional[float] = 15.0

class PredictionResponsePayload(BaseModel):
    id: Optional[int] = 1
    student_id: int
    risk_level: str
    risk_score: float
    recommendations: List[str]
    confidence: float

# Train Random Forest Classifier on initial synthetic dataset
rf_model = None
if SKLEARN_AVAILABLE:
    # Feature order: [attendance_pct, internal_marks, assignment_score, previous_gpa, study_hours]
    X_train = np.array([
        [95.0, 90.0, 92.0, 3.9, 20.0],
        [92.0, 85.0, 88.0, 3.7, 18.0],
        [88.0, 80.0, 82.0, 3.4, 15.0],
        [78.0, 68.0, 70.0, 2.9, 10.0],
        [72.0, 60.0, 65.0, 2.6, 8.0],
        [60.0, 50.0, 55.0, 2.2, 5.0],
        [45.0, 40.0, 48.0, 1.8, 3.0]
    ])
    # Labels: 0 = Safe, 1 = Warning, 2 = Critical
    y_train = np.array([0, 0, 0, 1, 1, 2, 2])
    rf_model = RandomForestClassifier(n_estimators=10, random_state=42)
    rf_model.fit(X_train, y_train)

@router.post("", response_model=PredictionResponsePayload)
@router.post("/predict", response_model=PredictionResponsePayload)
def predict_academic_risk(
    payload: PredictionInputPayload,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    att = payload.attendance_pct
    marks = payload.internal_marks
    assign = payload.assignment_score
    gpa = payload.previous_gpa
    hours = payload.study_hours or 12.0

    risk_level = "Safe"
    risk_score = 0.15
    confidence = 0.95

    if SKLEARN_AVAILABLE and rf_model is not None:
        features = np.array([[att, marks, assign, gpa, hours]])
        pred_class = rf_model.predict(features)[0]
        probs = rf_model.predict_proba(features)[0]
        confidence = float(np.max(probs))

        if pred_class == 0:
            risk_level = "Safe"
            risk_score = round(float(1.0 - probs[0]), 2)
        elif pred_class == 1:
            risk_level = "Warning"
            risk_score = round(float(probs[1] + 0.3), 2)
        else:
            risk_level = "Critical"
            risk_score = round(float(probs[2] + 0.5), 2)
    else:
        # Fallback heuristic prediction engine
        if att >= 85 and marks >= 75:
            risk_level = "Safe"
            risk_score = 0.12
        elif att >= 75 or marks >= 60:
            risk_level = "Warning"
            risk_score = 0.55
        else:
            risk_level = "Critical"
            risk_score = 0.88

    # Generate tailored academic recommendations
    recommendations = []
    if risk_level == "Safe":
        recommendations = [
            "Maintain current outstanding attendance trajectory (>90%).",
            "Consider enrolling in advanced research honours projects.",
            "Eligible for peer-tutoring mentorship role."
        ]
    elif risk_level == "Warning":
        recommendations = [
            "Attend mandatory office hours with course instructor twice weekly.",
            "Target assignment score improvement by +10% in next 2 weeks.",
            "Join guided group study sessions in campus library."
        ]
    else:
        recommendations = [
            "CRITICAL: Immediate academic counselor intervention scheduled.",
            "Mandatory attendance recovery plan initiated (>85% required).",
            "Remedial tutorial sessions assigned for low internal test scores."
        ]

    # Save prediction record to database
    prediction_record = StudentRiskPrediction(
        student_id=payload.student_id or 1,
        risk_level=risk_level,
        risk_score=risk_score,
        recommendations=" | ".join(recommendations),
        confidence=confidence
    )
    db.add(prediction_record)
    db.commit()
    db.refresh(prediction_record)

    return {
        "id": prediction_record.id,
        "student_id": payload.student_id or 1,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "recommendations": recommendations,
        "confidence": confidence
    }

@router.get("", response_model=List[PredictionResponsePayload])
def get_risk_predictions(
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(StudentRiskPrediction)
    if student_id:
        query = query.filter(StudentRiskPrediction.student_id == student_id)
    records = query.order_by(StudentRiskPrediction.id.desc()).all()

    res = []
    for r in records:
        recs = r.recommendations.split(" | ") if r.recommendations else []
        res.append({
            "id": r.id,
            "student_id": r.student_id,
            "risk_level": r.risk_level,
            "risk_score": r.risk_score,
            "recommendations": recs,
            "confidence": r.confidence or 0.95
        })
    return res
