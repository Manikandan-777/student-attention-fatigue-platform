"""Phase 14 Test Suite — Auth, Roles & REST API.

Spec refs: APP-2/3/5/7/9/12/15-19/26, CON §3.
Pass conditions:
- JWT login succeeds with correct credentials, fails otherwise (401).
- Bad / missing token → 401 on all protected routes.
- Teacher accessing admin-only route → 403.
- Teacher accessing another teacher's classroom → 403.
- Full CRUD for classrooms, students, teachers (admin).
- Teacher can only see their own classrooms/sessions.
- Session start/stop with teacher-classroom scoping.
- /system/status accessible by admin only.
- /teacher/dashboard accessible by teacher.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.jwt import hash_password
from app.db.database import get_db
from app.db.models import Base, Camera, Classroom, Teacher, TeacherClassroom, User
from app.main import app

# ---------------------------------------------------------------------------
# In-memory test database setup
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_phase14.db"

test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,   # keep attributes readable after commit/close
)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def fresh_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_admin(db) -> User:
    u = User(username="admin", password_hash=hash_password("adminpass"), role="admin")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed_teacher(db, username="teacher1", password="teachpass") -> tuple:
    u = User(username=username, password_hash=hash_password(password), role="teacher")
    db.add(u)
    db.flush()
    t = Teacher(user_id=u.id, display_name=f"Dr. {username.title()}")
    db.add(t)
    db.commit()
    db.refresh(t)
    return u, t


def _seed_classroom(db, name="Room 101", class_name="III AI") -> Classroom:
    cam = Camera(id="CAM-001", state="Online")
    db.merge(cam)
    db.flush()
    room = Classroom(room_name=name, class_name=class_name, camera_id="CAM-001")
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def _login(client, username, password) -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestAuth:
    def test_login_success_admin(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        resp = client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "admin"
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/auth/login", json={"username": "nobody", "password": "x"})
        assert resp.status_code == 401

    def test_me_authenticated(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.get("/auth/me", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"
        assert resp.json()["role"] == "admin"

    def test_me_no_token_401(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_bad_token_401(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer badtoken"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Role enforcement
# ---------------------------------------------------------------------------

class TestRoleEnforcement:
    def test_teacher_cannot_access_admin_route(self, client):
        """Teacher → /system/status must return 403."""
        db = TestSessionLocal()
        _seed_teacher(db)
        db.close()
        token = _login(client, "teacher1", "teachpass")
        resp = client.get("/system/status", headers=_auth(token))
        assert resp.status_code == 403

    def test_admin_can_access_system_status(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.get("/system/status", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "ai_server" in data
        assert "privacy_mode" in data

    def test_teacher_cannot_create_classroom(self, client):
        """POST /classrooms is admin-only → 403 for teacher."""
        db = TestSessionLocal()
        _seed_teacher(db)
        db.close()
        token = _login(client, "teacher1", "teachpass")
        resp = client.post("/classrooms",
                           json={"room_name": "X", "class_name": "Y"},
                           headers=_auth(token))
        assert resp.status_code == 403

    def test_no_token_on_classrooms_401(self, client):
        resp = client.get("/classrooms")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Classrooms CRUD
# ---------------------------------------------------------------------------

class TestClassrooms:
    def test_admin_creates_classroom(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.post("/classrooms",
                           json={"room_name": "Room 101", "class_name": "III AI"},
                           headers=_auth(token))
        assert resp.status_code == 201
        assert resp.json()["room_name"] == "Room 101"

    def test_admin_lists_all_classrooms(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        _seed_classroom(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.get("/classrooms", headers=_auth(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_teacher_sees_only_assigned_classroom(self, client):
        db = TestSessionLocal()
        _, teacher = _seed_teacher(db)
        room1 = _seed_classroom(db, "Room A", "CS-A")
        _seed_classroom(db, "Room B", "CS-B")   # not assigned to teacher
        db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=room1.id))
        db.commit()
        db.close()

        token = _login(client, "teacher1", "teachpass")
        resp = client.get("/classrooms", headers=_auth(token))
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert room1.id in ids
        assert len(ids) == 1, "Teacher must only see their own classroom"

    def test_admin_updates_classroom(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        room = _seed_classroom(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.put(f"/classrooms/{room.id}",
                          json={"room_name": "Updated Room"},
                          headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["room_name"] == "Updated Room"

    def test_admin_soft_deletes_classroom(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        room = _seed_classroom(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.delete(f"/classrooms/{room.id}", headers=_auth(token))
        assert resp.status_code == 204
        # Should no longer appear in list
        resp2 = client.get("/classrooms", headers=_auth(token))
        ids = [r["id"] for r in resp2.json()]
        assert room.id not in ids


# ---------------------------------------------------------------------------
# Students CRUD
# ---------------------------------------------------------------------------

class TestStudents:
    def test_admin_creates_student(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.post("/students",
                           json={"student_code": "S001", "name": "Alice", "year": 3},
                           headers=_auth(token))
        assert resp.status_code == 201
        assert resp.json()["student_code"] == "S001"

    def test_teacher_cannot_create_student(self, client):
        db = TestSessionLocal()
        _seed_teacher(db)
        db.close()
        token = _login(client, "teacher1", "teachpass")
        resp = client.post("/students",
                           json={"student_code": "S001", "name": "Alice"},
                           headers=_auth(token))
        assert resp.status_code == 403

    def test_admin_deactivates_student(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.post("/students",
                           json={"student_code": "S002", "name": "Bob"},
                           headers=_auth(token))
        sid = resp.json()["id"]
        resp2 = client.delete(f"/students/{sid}", headers=_auth(token))
        assert resp2.status_code == 204
        # After deactivation should not appear in list
        resp3 = client.get("/students", headers=_auth(token))
        ids = [s["id"] for s in resp3.json()]
        assert sid not in ids


# ---------------------------------------------------------------------------
# Teachers CRUD
# ---------------------------------------------------------------------------

class TestTeachers:
    def test_admin_creates_teacher(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.post("/teachers",
                           json={"username": "new_teacher", "password": "pass123",
                                 "display_name": "Dr. New"},
                           headers=_auth(token))
        assert resp.status_code == 201
        assert resp.json()["display_name"] == "Dr. New"

    def test_duplicate_teacher_username_409(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        client.post("/teachers",
                    json={"username": "dup", "password": "x", "display_name": "Dup"},
                    headers=_auth(token))
        resp2 = client.post("/teachers",
                            json={"username": "dup", "password": "y", "display_name": "Dup2"},
                            headers=_auth(token))
        assert resp2.status_code == 409

    def test_delete_teacher_deactivates_and_blocks_login(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        token = _login(client, "admin", "adminpass")
        resp = client.post("/teachers",
                           json={"username": "to_delete", "password": "pass123", "display_name": "Delete Me"},
                           headers=_auth(token))
        assert resp.status_code == 201
        teacher_id = resp.json()["id"]

        # Delete teacher
        del_resp = client.delete(f"/teachers/{teacher_id}", headers=_auth(token))
        assert del_resp.status_code == 204

        # Teacher can no longer log in
        login_resp = client.post("/auth/login", json={"username": "to_delete", "password": "pass123"})
        assert login_resp.status_code == 401


# ---------------------------------------------------------------------------
# Sessions with teacher-classroom scoping
# ---------------------------------------------------------------------------

class TestSessions:
    def test_teacher_starts_session_in_own_classroom(self, client):
        db = TestSessionLocal()
        _, teacher = _seed_teacher(db)
        room = _seed_classroom(db)
        db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=room.id))
        db.commit()
        db.close()
        token = _login(client, "teacher1", "teachpass")
        resp = client.post("/sessions",
                           json={"classroom_id": room.id},
                           headers=_auth(token))
        assert resp.status_code == 201
        assert resp.json()["status"] == "Monitoring"
        assert resp.json()["started_at"] is not None

    def test_teacher_cannot_start_session_in_other_classroom(self, client):
        db = TestSessionLocal()
        _seed_teacher(db)                        # teacher1 — not assigned anywhere
        room = _seed_classroom(db)
        db.close()
        token = _login(client, "teacher1", "teachpass")
        resp = client.post("/sessions",
                           json={"classroom_id": room.id},
                           headers=_auth(token))
        assert resp.status_code == 403

    def test_teacher_stops_own_session(self, client):
        db = TestSessionLocal()
        _, teacher = _seed_teacher(db)
        room = _seed_classroom(db)
        db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=room.id))
        db.commit()
        db.close()
        token = _login(client, "teacher1", "teachpass")
        start_resp = client.post("/sessions",
                                 json={"classroom_id": room.id},
                                 headers=_auth(token))
        sid = start_resp.json()["id"]
        stop_resp = client.post(f"/sessions/{sid}/stop",
                                json={"status": "Completed"},
                                headers=_auth(token))
        assert stop_resp.status_code == 200
        assert stop_resp.json()["status"] == "Completed"
        assert stop_resp.json()["ended_at"] is not None

    def test_teacher_cannot_see_other_sessions(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        _, teacher = _seed_teacher(db, "teacher2", "pass2")
        room = _seed_classroom(db)
        db.close()
        # Admin starts session
        admin_token = _login(client, "admin", "adminpass")
        client.post("/sessions", json={"classroom_id": room.id}, headers=_auth(admin_token))
        # Teacher2 not assigned → should see 0 sessions
        t_token = _login(client, "teacher2", "pass2")
        resp = client.get("/sessions", headers=_auth(t_token))
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_teacher_dashboard(self, client):
        db = TestSessionLocal()
        _, teacher = _seed_teacher(db)
        room = _seed_classroom(db)
        db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=room.id))
        db.commit()
        db.close()
        token = _login(client, "teacher1", "teachpass")
        client.post("/sessions", json={"classroom_id": room.id}, headers=_auth(token))
        resp = client.get("/teacher/dashboard", headers=_auth(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert "session_id" in resp.json()[0]
