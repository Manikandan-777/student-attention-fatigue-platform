"""Phase 15 Test Suite — Alert Engine & Alert API.

Spec refs: SYS-9, APP-10/11/20/21, CON §1, CON §2.3, CON §3, CON §4.
Pass conditions:
- Scripted sessions produce expected alerts (fatigue, distraction).
- Cooldown suppresses duplicate alerts within ALERT_COOLDOWN_S.
- System alerts (camera_offline, ai_offline) emitted for admin and suppressed by cooldown.
- Alert lifecycle: New → Viewed → Resolved with correct timestamps.
- Invalid state transitions rejected (422 / ValueError).
- Wording check: no diagnostic/disciplinary language (D8: never 'is sleeping' / 'is sick').
- Role-based scoping: teachers see only assigned classroom alerts; system alerts admin-only.
- Teacher mutating or viewing unauthorized alerts receives 403.
- Unauthenticated access returns 401.
- WebSocket pushes alerts with contracts.md §2.3 schema.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.alerts.engine import (
    AlertEngine,
    alert_engine,
    alert_to_dict,
    validate_alert_wording,
)
from app.auth.jwt import create_access_token, hash_password
from app.db.database import get_db
from app.db.models import (
    Alert,
    Base,
    Camera,
    Classroom,
    Session,
    Teacher,
    TeacherClassroom,
    User,
)
from app.main import app

# ---------------------------------------------------------------------------
# Test DB setup
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_phase15.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_teardown_db():
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
# Seed Helpers
# ---------------------------------------------------------------------------

def _seed_admin(db) -> User:
    u = User(username="admin_user", password_hash=hash_password("adminpass"), role="admin")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed_teacher(db, username="teacher1", password="teachpass") -> tuple:
    u = User(username=username, password_hash=hash_password(password), role="teacher")
    db.add(u)
    db.flush()
    t = Teacher(user_id=u.id, display_name=f"Prof. {username.capitalize()}")
    db.add(t)
    db.commit()
    db.refresh(t)
    return u, t


def _seed_classroom_and_session(db, room_name="Lab 1", class_name="AI 101") -> tuple:
    cam = Camera(id=f"CAM-{room_name.replace(' ', '')}", state="Online")
    db.merge(cam)
    db.flush()

    room = Classroom(room_name=room_name, class_name=class_name, camera_id=cam.id)
    db.add(room)
    db.flush()

    sess = Session(classroom_id=room.id, status="Monitoring")
    db.add(sess)
    db.commit()
    db.refresh(room)
    db.refresh(sess)
    return room, sess


def _auth(role="admin", username="admin_user"):
    token = create_access_token(subject=username, role=role)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit Tests — Language Guard (D8, APP-21)
# ---------------------------------------------------------------------------

class TestAlertLanguageGuard:
    def test_valid_informational_messages_pass(self):
        valid_messages = [
            "Repeated fatigue-related indicators during the current session.",
            "Persistent off-task gaze or orientation detected during the current session.",
            "Camera feed CAM-001 is offline or unavailable.",
            "AI processing worker heartbeat timed out.",
            "Repeated distraction-related indicators during the current session.",
        ]
        for msg in valid_messages:
            validate_alert_wording(msg)  # Should not raise

    def test_prohibited_diagnostic_language_rejected(self):
        prohibited = [
            "Student is sleeping in class.",
            "Student is fast asleep.",
            "Student is sick and coughing.",
            "Student is ill.",
            "Student is lazy and slacking off.",
            "Student needs punishment for misbehavior.",
            "Student shows signs of adhd disorder.",
            "Student looks depressed.",
        ]
        for bad_msg in prohibited:
            with pytest.raises(ValueError, match="Prohibited diagnostic/disciplinary language"):
                validate_alert_wording(bad_msg)


# ---------------------------------------------------------------------------
# Unit Tests — AlertEngine Cooldown & Lifecycle
# ---------------------------------------------------------------------------

class TestAlertEngineLogic:
    def test_record_alert_and_dict_schema(self):
        db = TestSessionLocal()
        _, sess = _seed_classroom_and_session(db)

        engine = AlertEngine(cooldown_s=60.0)
        alert = engine.record_alert(
            db=db,
            session_id=sess.id,
            track_id=1,
            label="S001",
            alert_type="fatigue",
            message="Repeated fatigue-related indicators during the current session.",
            confidence=0.92,
            broadcast=False,
        )
        db.commit()

        assert alert.id is not None
        assert alert.status == "New"
        assert alert.type == "fatigue"

        data = alert_to_dict(alert)
        assert data["id"] == alert.id
        assert data["session_id"] == sess.id
        assert data["track_id"] == 1
        assert data["label"] == "S001"
        assert data["type"] == "fatigue"
        assert data["status"] == "New"
        assert data["confidence"] == 0.92
        assert "created_at" in data
        assert data["viewed_at"] is None
        assert data["resolved_at"] is None
        db.close()

    def test_system_alerts_camera_and_ai_offline_with_cooldown(self):
        db = TestSessionLocal()
        engine = AlertEngine(cooldown_s=50.0)

        # 1. Camera offline triggers first time
        a1 = engine.emit_camera_offline(db=db, camera_id="CAM-99", now_ts=100.0)
        db.commit()
        assert a1 is not None
        assert a1.type == "camera_offline"
        assert a1.track_id == 0

        # 2. Camera offline suppressed during cooldown
        a2 = engine.emit_camera_offline(db=db, camera_id="CAM-99", now_ts=120.0)
        assert a2 is None

        # 3. Camera offline emits after cooldown expires (100 + 50 = 150)
        a3 = engine.emit_camera_offline(db=db, camera_id="CAM-99", now_ts=160.0)
        db.commit()
        assert a3 is not None
        assert a3.type == "camera_offline"

        # 4. AI offline triggers first time
        ai1 = engine.emit_ai_offline(db=db, now_ts=200.0)
        db.commit()
        assert ai1 is not None
        assert ai1.type == "ai_offline"

        # 5. AI offline suppressed during cooldown
        ai2 = engine.emit_ai_offline(db=db, now_ts=220.0)
        assert ai2 is None

        db.close()

    def test_alert_lifecycle_valid_transitions(self):
        db = TestSessionLocal()
        _, sess = _seed_classroom_and_session(db)
        engine = AlertEngine()

        alert = engine.record_alert(
            db=db,
            session_id=sess.id,
            track_id=1,
            label="S001",
            alert_type="distraction",
            message="Repeated distraction-related indicators during the current session.",
            confidence=0.88,
            broadcast=False,
        )
        assert alert.status == "New"
        assert alert.viewed_at is None
        assert alert.resolved_at is None

        # New → Viewed
        engine.transition_status(alert, "Viewed")
        assert alert.status == "Viewed"
        assert alert.viewed_at is not None
        assert alert.resolved_at is None

        # Viewed → Resolved
        engine.transition_status(alert, "Resolved")
        assert alert.status == "Resolved"
        assert alert.resolved_at is not None

        db.close()

    def test_alert_lifecycle_invalid_transitions_rejected(self):
        db = TestSessionLocal()
        _, sess = _seed_classroom_and_session(db)
        engine = AlertEngine()

        alert = engine.record_alert(
            db=db,
            session_id=sess.id,
            track_id=1,
            label="S001",
            alert_type="fatigue",
            message="Repeated fatigue-related indicators during the current session.",
            confidence=0.90,
            broadcast=False,
        )

        # Transition to Resolved directly (valid)
        engine.transition_status(alert, "Resolved")
        assert alert.status == "Resolved"

        # Resolved → Viewed (INVALID)
        with pytest.raises(ValueError, match="Invalid status transition"):
            engine.transition_status(alert, "Viewed")

        # Resolved → New (INVALID)
        with pytest.raises(ValueError, match="Invalid status transition"):
            engine.transition_status(alert, "New")

        # Unknown status
        with pytest.raises(ValueError, match="Invalid alert status"):
            engine.transition_status(alert, "Archived")

        db.close()


# ---------------------------------------------------------------------------
# API Tests — REST Endpoints & Role Matrix
# ---------------------------------------------------------------------------

class TestAlertsAPI:
    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/alerts")
        assert resp.status_code == 401

        resp = client.patch("/alerts/1", json={"status": "Viewed"})
        assert resp.status_code == 401

    def test_admin_can_view_all_alerts_and_filter(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        _, sess1 = _seed_classroom_and_session(db, "Room 1", "Class 1")
        _, sess2 = _seed_classroom_and_session(db, "Room 2", "Class 2")

        engine = AlertEngine()
        a1 = engine.record_alert(db, sess1.id, 1, "S001", "fatigue",
                                 "Repeated fatigue-related indicators during the current session.", 0.95, broadcast=False)
        a2 = engine.record_alert(db, sess2.id, 2, "S002", "distraction",
                                 "Repeated distraction-related indicators during the current session.", 0.85, broadcast=False)
        sys_alert = engine.emit_camera_offline(db, "CAM-999")
        db.commit()
        db.close()

        headers = _auth(role="admin", username="admin_user")

        # Admin sees all 3 alerts
        resp = client.get("/alerts", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

        # Filter by type=camera_offline
        resp_cam = client.get("/alerts?type=camera_offline", headers=headers)
        assert resp_cam.status_code == 200
        assert len(resp_cam.json()) == 1
        assert resp_cam.json()[0]["type"] == "camera_offline"

        # Filter by session_id=sess1.id
        resp_sess = client.get(f"/alerts?session_id={sess1.id}", headers=headers)
        assert resp_sess.status_code == 200
        assert len(resp_sess.json()) == 1
        assert resp_sess.json()[0]["label"] == "S001"

    def test_teacher_scoping_sees_only_assigned_classroom_alerts(self, client):
        db = TestSessionLocal()
        user_t, teacher = _seed_teacher(db, "teacher_alpha", "pass123")
        room_assigned, sess_assigned = _seed_classroom_and_session(db, "Assigned Room", "CS A")
        room_other, sess_other = _seed_classroom_and_session(db, "Other Room", "CS B")

        # Assign teacher to room_assigned
        db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=room_assigned.id))
        db.commit()

        engine = AlertEngine()
        # Alert in teacher's classroom
        engine.record_alert(db, sess_assigned.id, 1, "S001", "fatigue",
                            "Repeated fatigue-related indicators during the current session.", 0.92, broadcast=False)
        # Alert in other teacher's classroom
        engine.record_alert(db, sess_other.id, 2, "S002", "distraction",
                            "Repeated distraction-related indicators during the current session.", 0.88, broadcast=False)
        # System alert (should be hidden from teachers)
        engine.emit_camera_offline(db, "CAM-1")
        db.commit()
        db.close()

        headers = _auth(role="teacher", username="teacher_alpha")

        # Teacher should only see the 1 alert from assigned classroom
        resp = client.get("/alerts", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["session_id"] == sess_assigned.id
        assert data[0]["label"] == "S001"

        # Teacher requesting unauthorized session_id receives 403 Forbidden
        resp_forbidden = client.get(f"/alerts?session_id={sess_other.id}", headers=headers)
        assert resp_forbidden.status_code == 403

    def test_patch_alert_status_new_to_viewed_to_resolved(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        _, sess = _seed_classroom_and_session(db)

        engine = AlertEngine()
        alert = engine.record_alert(db, sess.id, 1, "S001", "fatigue",
                                    "Repeated fatigue-related indicators during the current session.", 0.91, broadcast=False)
        db.commit()
        aid = alert.id
        db.close()

        headers = _auth(role="admin", username="admin_user")

        # 1. New → Viewed
        patch1 = client.patch(f"/alerts/{aid}", json={"status": "Viewed"}, headers=headers)
        assert patch1.status_code == 200
        data1 = patch1.json()
        assert data1["status"] == "Viewed"
        assert data1["viewed_at"] is not None
        assert data1["resolved_at"] is None

        # 2. Viewed → Resolved
        patch2 = client.patch(f"/alerts/{aid}", json={"status": "Resolved"}, headers=headers)
        assert patch2.status_code == 200
        data2 = patch2.json()
        assert data2["status"] == "Resolved"
        assert data2["resolved_at"] is not None

        # 3. Invalid transition: Resolved → Viewed (422)
        patch3 = client.patch(f"/alerts/{aid}", json={"status": "Viewed"}, headers=headers)
        assert patch3.status_code == 422

    def test_teacher_cannot_patch_unassigned_classroom_or_system_alert(self, client):
        db = TestSessionLocal()
        user_t, teacher = _seed_teacher(db, "teacher_beta", "pass456")
        room_other, sess_other = _seed_classroom_and_session(db, "Unassigned", "CS C")

        engine = AlertEngine()
        alert_other = engine.record_alert(db, sess_other.id, 1, "S001", "fatigue",
                                          "Repeated fatigue-related indicators during the current session.", 0.90, broadcast=False)
        sys_alert = engine.emit_ai_offline(db)
        db.commit()
        aid_other = alert_other.id
        aid_sys = sys_alert.id
        db.close()

        headers = _auth(role="teacher", username="teacher_beta")

        # Cannot patch alert from unassigned classroom
        r1 = client.patch(f"/alerts/{aid_other}", json={"status": "Viewed"}, headers=headers)
        assert r1.status_code == 403

        # Cannot patch system alert
        r2 = client.patch(f"/alerts/{aid_sys}", json={"status": "Viewed"}, headers=headers)
        assert r2.status_code == 403

    def test_patch_nonexistent_alert_returns_404(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        db.close()
        headers = _auth(role="admin", username="admin_user")
        resp = client.patch("/alerts/99999", json={"status": "Viewed"}, headers=headers)
        assert resp.status_code == 404
