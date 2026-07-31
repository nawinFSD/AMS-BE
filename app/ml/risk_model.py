import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle
import os

class StudentRiskPredictor:
    def __init__(self):
        self.model = None
        self._initialize_and_train()

    def _generate_synthetic_data(self, samples=500):
        np.random.seed(42)
        # Features: [attendance_pct, assignment_score, internal_marks, previous_gpa]
        attendance = np.random.uniform(40, 100, samples)
        assignments = np.random.uniform(40, 100, samples)
        internals = np.random.uniform(35, 100, samples)
        gpa = np.random.uniform(1.8, 4.0, samples)

        X = np.column_stack((attendance, assignments, internals, gpa))
        
        # Label heuristic: High risk if attendance < 65 or (internals < 50 and gpa < 2.5)
        # Medium risk if attendance between 65 and 75
        # Low risk otherwise
        y = []
        for att, ass, idx, g in zip(attendance, assignments, internals, gpa):
            risk_score = (100 - att) * 0.4 + (100 - ass) * 0.2 + (100 - idx) * 0.2 + (4.0 - g) * 10
            if risk_score > 35 or att < 65:
                y.append("HIGH")
            elif risk_score > 20 or att < 75:
                y.append("MEDIUM")
            else:
                y.append("LOW")

        return X, np.array(y)

    def _initialize_and_train(self):
        X, y = self._generate_synthetic_data()
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X, y)

    def predict_risk(self, attendance_pct: float, assignment_score: float, internal_marks: float, previous_gpa: float):
        input_data = np.array([[attendance_pct, assignment_score, internal_marks, previous_gpa]])
        prediction = self.model.predict(input_data)[0]
        probabilities = self.model.predict_proba(input_data)[0]
        confidence = float(np.max(probabilities))

        # Risk score scaling 0.0 (safest) to 1.0 (highest risk)
        raw_risk_score = ((100 - attendance_pct) * 0.4 + (100 - assignment_score) * 0.2 + 
                          (100 - internal_marks) * 0.2 + (4.0 - previous_gpa) * 10) / 60.0
        risk_score = round(min(max(raw_risk_score, 0.05), 0.98), 2)

        # Generate targeted recommendations based on inputs
        recommendations = []
        if attendance_pct < 75:
            recommendations.append("Attendance is below 75% threshold. Issue mandatory attendance counseling.")
        if assignment_score < 60:
            recommendations.append("Low assignment completion score. Assign tutorial mentor for coursework assistance.")
        if internal_marks < 50:
            recommendations.append("Poor internal examination performance. Recommend remedial classes before finals.")
        if previous_gpa < 2.5:
            recommendations.append("Low GPA trajectory detected. Schedule academic advising session.")

        if not recommendations:
            recommendations.append("Student is performing well across all academic metrics. Maintain current trajectory.")

        return {
            "risk_level": prediction,
            "risk_score": risk_score,
            "confidence": round(confidence, 2),
            "recommendations": recommendations
        }

# Global predictor instance
risk_predictor = StudentRiskPredictor()
