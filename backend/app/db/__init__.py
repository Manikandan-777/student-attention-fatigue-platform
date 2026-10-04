"""DB package — exposes models, engine, session factory and services."""

from app.db.database import create_tables, drop_tables, engine, get_db, get_db_session, SessionLocal
from app.db.models import (
    Alert,
    Base,
    Camera,
    Classroom,
    ClassroomStudent,
    Observation,
    Session,
    Student,
    Teacher,
    TeacherClassroom,
    TrackRosterMap,
    User,
)

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_session",
    "create_tables",
    "drop_tables",
    # Models
    "User",
    "Teacher",
    "Student",
    "Camera",
    "Classroom",
    "TeacherClassroom",
    "ClassroomStudent",
    "Session",
    "TrackRosterMap",
    "Observation",
    "Alert",
]
