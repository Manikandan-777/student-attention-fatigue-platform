"""Shared fixtures for security test suite — README_SECURITY_TESTING.md.

Implements the seed user matrix from Section 2:
  admin1       admin   active   all classrooms
  teacherA     teacher active   Room A only
  teacherB     teacher active   Room B only
  teacherOff   teacher DISABLED Room A

Fixture ordering:
  fresh_db (session-scoped schema reset) → scenario (seed data) → test
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt import hash_password
from app.auth.rate_limiter import login_rate_limiter
from app.db.database import get_db
from app.db.models import (
    Base, Camera, Classroom,
    Session as ClassSession,
    Teacher, TeacherClassroom, User,
)
from app.main import app

# ---------------------------------------------------------------------------
# Isolated, file-based test database (avoids WAL file issues on Windows)
# ---------------------------------------------------------------------------
SEC_DB_URL = "sqlite:///./test_security_suite.db"
_engine = create_engine(
    SEC_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
_Session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_engine,
    expire_on_commit=False,
)


def _db_session():
    """Yield a fresh SQLAlchemy Session and always close it."""
    db = _Session()
    try:
        yield db
    finally:
        db.close()


def _override_db():
    """FastAPI dependency override — routes use the same isolated DB."""
    yield from _db_session()


# ---------------------------------------------------------------------------
# fresh_db — function-scoped: wipe + recreate schema before every test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def fresh_db():
    """Drop and recreate schema before each test.  Also resets the rate limiter."""
    app.dependency_overrides[get_db] = _override_db
    login_rate_limiter.reset()
    Base.metadata.drop_all(bind=_engine, checkfirst=True)
    Base.metadata.create_all(bind=_engine, checkfirst=True)
    yield
    try:
        Base.metadata.drop_all(bind=_engine, checkfirst=True)
    except Exception:
        pass
    app.dependency_overrides.pop(get_db, None)



# ---------------------------------------------------------------------------
# client — standard FastAPI test client
# ---------------------------------------------------------------------------
@pytest.fixture
def client(fresh_db):   # explicit dep ensures fresh_db runs first
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Low-level seed helpers (all use a caller-provided db session)
# ---------------------------------------------------------------------------
def _make_user(db, username: str, password: str, role: str, active: bool = True) -> User:
    """Insert a User (+ Teacher profile if role=='teacher') and return the User."""
    u = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        active=active,
    )
    db.add(u)
    db.commit()
    db.refresh(u)               # reload from DB so u.id is populated
    if role == "teacher":
        t = Teacher(user_id=u.id, display_name=f"Dr. {username.title()}")
        db.add(t)
        db.commit()
    return u


def _make_room(db, room_name: str, class_name: str, cam_id: str) -> Classroom:
    cam = Camera(id=cam_id, state="Online")
    db.merge(cam)
    db.commit()
    room = Classroom(room_name=room_name, class_name=class_name, camera_id=cam_id)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def _assign(db, user_id: int, classroom_id: int) -> None:
    """Assign a teacher (by user_id) to a classroom (by id)."""
    t = db.query(Teacher).filter(Teacher.user_id == user_id).one()
    db.add(TeacherClassroom(teacher_id=t.id, classroom_id=classroom_id))
    db.commit()


def _make_session(db, classroom_id: int) -> ClassSession:
    sess = ClassSession(classroom_id=classroom_id, status="Monitoring")
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _login(client, username: str, password: str) -> str:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed for {username!r}: {r.text}"
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# scenario — Section 2 user + classroom + session matrix
# ---------------------------------------------------------------------------
@pytest.fixture
def scenario(client):     # client already depends on fresh_db
    """Seed admin1, teacherA, teacherB, teacherOff, Room A, Room B, one session each."""
    db = _Session()

    # Users
    admin1     = _make_user(db, "admin1",     "Admin@Pass1", "admin")
    teacher_a  = _make_user(db, "teacherA",   "PassA#123",   "teacher")
    teacher_b  = _make_user(db, "teacherB",   "PassB#456",   "teacher")
    _make_user(db, "teacherOff", "PassOff#!",  "teacher", active=False)

    # Rooms
    room_a = _make_room(db, "Room A", "III AI", "CAM-A01")
    room_b = _make_room(db, "Room B", "III DS", "CAM-B01")

    # Classroom assignments (pass plain IDs to avoid stale-object issues)
    _assign(db, teacher_a.id, room_a.id)
    _assign(db, teacher_b.id, room_b.id)

    # Sessions
    sess_a = _make_session(db, room_a.id)
    sess_b = _make_session(db, room_b.id)

    db.close()

    # Log in — must happen after schema is ready (client fixture already created)
    tok_admin = _login(client, "admin1",   "Admin@Pass1")
    tok_a     = _login(client, "teacherA", "PassA#123")
    tok_b     = _login(client, "teacherB", "PassB#456")

    return {
        "client":       client,
        "admin_token":  tok_admin,
        "token_a":      tok_a,
        "token_b":      tok_b,
        "room_a_id":    room_a.id,
        "room_b_id":    room_b.id,
        "session_a_id": sess_a.id,
        "session_b_id": sess_b.id,
        "users": {
            "admin1":   admin1,
            "teacherA": teacher_a,
            "teacherB": teacher_b,
        },
    }
