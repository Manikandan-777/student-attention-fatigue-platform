"""API package — aggregates all routers."""
from app.api import alerts, classrooms, reports, sessions, students, system, teachers

__all__ = ["alerts", "classrooms", "reports", "sessions", "students", "system", "teachers"]
