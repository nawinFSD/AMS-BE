from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import engine, Base
from app.routers import (
    auth_router, attendance_router, analytics_router, 
    users_router, ai_router, ws_router, predictions_router,
    departments_router, courses_router, subjects_router, 
    students_router, faculty_router
)

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Attendance & Academic Analytics API",
    description="Enterprise REST & WebSocket API built with FastAPI, SQLAlchemy, Scikit-learn & WebSockets",
    version="1.0.0"
)

# Explicit CORS Origins for Local Dev & Production
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:5173",
]

# Enable CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router.router)
app.include_router(departments_router.router)
app.include_router(courses_router.router)
app.include_router(subjects_router.router)
app.include_router(students_router.router)
app.include_router(faculty_router.router)
app.include_router(attendance_router.router)
app.include_router(analytics_router.router)
app.include_router(predictions_router.router)
app.include_router(users_router.router)
app.include_router(ai_router.router)
app.include_router(ws_router.router)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "Smart Attendance & Academic Analytics Management API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
