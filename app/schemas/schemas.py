from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Generic Bulk Delete Payload
class BulkDeletePayload(BaseModel):
    ids: List[int]

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserResponse"

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    name: str
    email: str
    role: str
    profileImage: Optional[str] = None
    phone: Optional[str] = None
    isActive: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    profileImage: Optional[str] = None
    phone: Optional[str] = None
    isActive: Optional[bool] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# Department Schemas
class DepartmentCreate(BaseModel):
    name: str
    code: str
    hod_name: Optional[str] = "Dr. Alan Turing"
    description: Optional[str] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    hod_name: Optional[str] = None
    description: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str
    hod_name: Optional[str] = None
    description: Optional[str] = None
    total_faculty: Optional[int] = 0
    total_students: Optional[int] = 0
    total_subjects: Optional[int] = 0
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# Course Schemas
class CourseCreate(BaseModel):
    name: str
    code: str
    department_id: int

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[int] = None

class CourseResponse(BaseModel):
    id: int
    name: str
    code: str
    department_id: int
    department: Optional[DepartmentResponse] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# Subject Schemas
class SubjectCreate(BaseModel):
    name: str
    code: str
    course_id: int
    department_id: int
    total_classes: Optional[int] = 40

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    course_id: Optional[int] = None
    department_id: Optional[int] = None
    total_classes: Optional[int] = None

class SubjectResponse(BaseModel):
    id: int
    name: str
    code: str
    course_id: int
    department_id: int
    total_classes: int
    course: Optional[CourseResponse] = None
    department: Optional[DepartmentResponse] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# Student Schemas
class StudentCreate(BaseModel):
    name: str
    email: str
    roll_number: str
    department_id: int
    course_id: int
    semester: Optional[str] = "Semester 4"
    section: Optional[str] = "Section A"
    phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    profileImage: Optional[str] = None
    batch_year: Optional[int] = 2024
    current_gpa: Optional[float] = 3.5
    assignment_score: Optional[float] = 85.0
    internal_marks: Optional[float] = 80.0
    password: Optional[str] = "Student@123"

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    roll_number: Optional[str] = None
    department_id: Optional[int] = None
    course_id: Optional[int] = None
    semester: Optional[str] = None
    section: Optional[str] = None
    phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    profileImage: Optional[str] = None
    batch_year: Optional[int] = None
    current_gpa: Optional[float] = None
    assignment_score: Optional[float] = None
    internal_marks: Optional[float] = None
    isActive: Optional[bool] = None

class StudentResponse(BaseModel):
    id: int
    user_id: int
    roll_number: str
    semester: Optional[str] = "Semester 4"
    section: Optional[str] = "Section A"
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    batch_year: int
    current_gpa: float
    assignment_score: float
    internal_marks: float
    user: UserResponse
    department: Optional[DepartmentResponse] = None
    course: Optional[CourseResponse] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# Faculty Schemas
class FacultyCreate(BaseModel):
    name: str
    email: str
    employee_id: str
    department_id: int
    phone: Optional[str] = None
    profileImage: Optional[str] = None
    assigned_subjects: Optional[str] = "Data Structures, Database Systems"
    assigned_classes: Optional[str] = "CS-A, CS-B"
    password: Optional[str] = "Faculty@123"

class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: Optional[int] = None
    phone: Optional[str] = None
    profileImage: Optional[str] = None
    assigned_subjects: Optional[str] = None
    assigned_classes: Optional[str] = None

class FacultyResponse(BaseModel):
    id: int
    user_id: int
    employee_id: str
    phone: Optional[str] = None
    assigned_subjects: Optional[str] = "Data Structures, Database Systems"
    assigned_classes: Optional[str] = "CS-A, CS-B"
    user: UserResponse
    department: Optional[DepartmentResponse] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# Attendance Schemas
class AttendanceMark(BaseModel):
    student_id: int
    subject_id: int
    date: str
    status: str
    type: Optional[str] = "MANUAL"

class AttendanceResponse(BaseModel):
    id: int
    student_id: int
    subject_id: int
    date: str
    status: str
    type: str
    createdAt: datetime
    updatedAt: datetime
    student: Optional[StudentResponse] = None
    subject: Optional[SubjectResponse] = None

    class Config:
        from_attributes = True

# Notification Schemas
class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# AI Risk Prediction Schema
class RiskInput(BaseModel):
    attendance_pct: float
    assignment_score: float
    internal_marks: float
    previous_gpa: float

class RiskOutput(BaseModel):
    risk_level: str
    risk_score: float
    recommendations: List[str]
    confidence: float
