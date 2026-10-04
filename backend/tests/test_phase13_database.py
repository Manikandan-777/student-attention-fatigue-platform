"""Phase 13 Test Suite — Database & Session Logging.

Spec refs: SYS-12, APP-12, CON §7, README_EXECUTION.md Phase 13.
Pass conditions:
- Alembic migration up/down succeeds.
- CRUD operations on all key tables succeed.
- FK and integrity violations are rejected.
- No BLOB/image columns exist anywhere in the schema.
- Session start/stop records automatic timestamps and status transitions.
- Observation aggregation (flush_observation) inserts rows correctly.
- Retention purge deletes only rows older than RETENTION_DAYS.
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import inspect, text

from app.db.database import create_tables, drop_tables, engine, SessionLocal
from app.db.models import (
    Alert, Camera, Classroom, ClassroomStudent,
    Observation, Session, Student, Teacher,
    TeacherClassroom, TrackRosterMap, User,
)
from app.db.session_service import (
    flush_observation,
    run_retention_purge,
    start_session,
    stop_session,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db():
    """Create tables before each test, drop after."""
    drop_tables()
    create_tables()
    yield
    drop_tables()


@pytest.fixture
def db():
    """Yield a transactional DB session, always rolled back after test."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_classroom(db) -> tuple:
    """Seed minimal Camera + Classroom, return (camera, classroom)."""
    cam = Camera(id="CAM-001", source_uri="rtsp://localhost/test", state="Online")
    db.add(cam)
    db.flush()

    room = Classroom(room_name="Room 101", class_name="III AI & DS", camera_id="CAM-001")
    db.add(room)
    db.flush()
    return cam, room


# ---------------------------------------------------------------------------
# Migration: up / down
# ---------------------------------------------------------------------------

def test_migration_up_creates_all_tables():
    """All 11 tables from CON §7 must exist after create_tables()."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    required = {
        "users", "teachers", "students", "cameras", "classrooms",
        "teacher_classrooms", "classroom_students",
        "sessions", "track_roster_map", "observations", "alerts",
    }
    missing = required - tables
    assert not missing, f"Missing tables after migration: {missing}"


def test_migration_down_removes_tables():
    """drop_tables() must remove all application tables."""
    drop_tables()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    # alembic_version may remain — only check our tables are gone
    app_tables = {
        "users", "teachers", "students", "cameras", "classrooms",
        "teacher_classrooms", "classroom_students",
        "sessions", "track_roster_map", "observations", "alerts",
    }
    still_present = app_tables & tables
    assert not still_present, f"Tables still present after drop: {still_present}"
    # Re-create so autouse fixture teardown doesn't error
    create_tables()


# ---------------------------------------------------------------------------
# No BLOB/image columns
# ---------------------------------------------------------------------------

def test_no_blob_image_columns():
    """CON §7 hard rule: no BLOB or image columns anywhere in the schema."""
    inspector = inspect(engine)
    blob_types = {"BLOB", "BINARY", "VARBINARY", "IMAGE", "BYTEA", "LONGBLOB"}
    violations = []
    for table_name in inspector.get_table_names():
        for col in inspector.get_columns(table_name):
            col_type = str(col["type"]).upper()
            if any(b in col_type for b in blob_types):
                violations.append(f"{table_name}.{col['name']} ({col_type})")
    assert not violations, f"BLOB/image columns found (violates CON §7): {violations}"


# ---------------------------------------------------------------------------
# CRUD — Users
# ---------------------------------------------------------------------------

def test_user_crud(db):
    """Insert, query, and enforce uniqueness on users.username."""
    import sqlalchemy.exc

    u = User(username="teacher_a", password_hash="hashed", role="teacher")
    db.add(u)
    db.flush()

    fetched = db.query(User).filter_by(username="teacher_a").one()
    assert fetched.id is not None
    assert fetched.role == "teacher"
    assert fetched.active is True

    # Duplicate username must fail — use a nested savepoint so we stay in one session
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        with db.begin_nested():          # SAVEPOINT
            db.add(User(username="teacher_a", password_hash="x", role="admin"))
            db.flush()


# ---------------------------------------------------------------------------
# CRUD — Session lifecycle
# ---------------------------------------------------------------------------

def test_session_start_stop(db):
    """start_session sets started_at and status=Monitoring; stop_session sets ended_at."""
    _, room = _seed_classroom(db)

    sess = start_session(db, classroom_id=room.id)
    assert sess.id is not None
    assert sess.status == "Monitoring"
    assert sess.started_at is not None
    assert sess.ended_at is None

    stopped = stop_session(db, session_id=sess.id, status="Completed")
    assert stopped.status == "Completed"
    assert stopped.ended_at is not None
    assert stopped.ended_at >= stopped.started_at


def test_session_abort(db):
    """stop_session with status=Aborted must be accepted."""
    _, room = _seed_classroom(db)
    sess = start_session(db, classroom_id=room.id)

    stopped = stop_session(db, session_id=sess.id, status="Aborted")
    assert stopped.status == "Aborted"


def test_session_stop_invalid_status(db):
    """Stopping with an invalid status must raise ValueError."""
    _, room = _seed_classroom(db)
    sess = start_session(db, classroom_id=room.id)

    with pytest.raises(ValueError, match="Invalid stop status"):
        stop_session(db, session_id=sess.id, status="BadStatus")


def test_session_stop_nonexistent_returns_none(db):
    """Stopping a non-existent session must return None, not crash."""
    result = stop_session(db, session_id=99999)
    assert result is None


# ---------------------------------------------------------------------------
# CRUD — Observations
# ---------------------------------------------------------------------------

def test_flush_observation(db):
    """flush_observation inserts a row with correct field values."""
    _, room = _seed_classroom(db)
    sess = start_session(db, classroom_id=room.id)

    obs = flush_observation(
        db,
        session_id=sess.id,
        track_id=1,
        attention_status="Attentive",
        fatigue_status="Normal",
        attention_score_mean=85.5,
        fatigue_index_mean=0.12,
        confidence_mean=0.95,
        drowsy_frames=2,
        total_frames=60,
    )
    assert obs.id is not None
    assert obs.session_id == sess.id
    assert obs.track_id == 1
    assert obs.attention_status == "Attentive"
    assert obs.fatigue_status == "Normal"
    assert abs(obs.attention_score_mean - 85.5) < 0.01
    assert obs.total_frames == 60


def test_observation_fk_enforced(db):
    """Observation must reject an invalid session_id (FK violation)."""
    import sqlalchemy.exc
    db2 = SessionLocal()
    try:
        obs = Observation(
            session_id=99999,
            track_id=1,
            ts=datetime.now(timezone.utc).replace(tzinfo=None),
            attention_status="Attentive",
            fatigue_status="Normal",
            attention_score_mean=80.0,
            fatigue_index_mean=0.1,
            confidence_mean=0.9,
            drowsy_frames=0,
            total_frames=30,
        )
        db2.add(obs)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db2.flush()
    finally:
        db2.rollback()
        db2.close()


# ---------------------------------------------------------------------------
# CRUD — Alerts
# ---------------------------------------------------------------------------

def test_alert_crud(db):
    """Insert alert and verify status lifecycle New→Viewed→Resolved."""
    _, room = _seed_classroom(db)
    sess = start_session(db, classroom_id=room.id)

    alert = Alert(
        session_id=sess.id,
        track_id=3,
        label="S003",
        type="fatigue",
        status="New",
        message="Repeated fatigue-related indicators during the current session.",
        confidence=0.92,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(alert)
    db.flush()

    assert alert.id is not None
    assert alert.status == "New"
    assert alert.viewed_at is None
    assert alert.resolved_at is None

    # Viewed
    alert.status = "Viewed"
    alert.viewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
    assert alert.status == "Viewed"

    # Resolved
    alert.status = "Resolved"
    alert.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
    assert alert.status == "Resolved"


# ---------------------------------------------------------------------------
# Retention purge
# ---------------------------------------------------------------------------

def test_retention_purge(db):
    """Retention job deletes rows older than RETENTION_DAYS; keeps recent rows."""
    _, room = _seed_classroom(db)
    sess = start_session(db, classroom_id=room.id)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_ts = now - timedelta(days=200)
    recent_ts = now - timedelta(days=5)

    # Old observation
    db.add(Observation(
        session_id=sess.id, track_id=1, ts=old_ts,
        attention_status="Unknown", fatigue_status="Unknown",
        attention_score_mean=0, fatigue_index_mean=0, confidence_mean=0,
        drowsy_frames=0, total_frames=0,
    ))
    # Recent observation
    db.add(Observation(
        session_id=sess.id, track_id=2, ts=recent_ts,
        attention_status="Attentive", fatigue_status="Normal",
        attention_score_mean=80, fatigue_index_mean=0.1, confidence_mean=0.9,
        drowsy_frames=0, total_frames=30,
    ))
    # Old alert
    db.add(Alert(
        session_id=sess.id, track_id=1, label="S001", type="fatigue",
        status="New", message="test", confidence=0.9, created_at=old_ts,
    ))
    db.flush()

    result = run_retention_purge(db, retention_days=180)
    assert result["observations_deleted"] == 1
    assert result["alerts_deleted"] == 1

    # Recent observation must still exist
    remaining = db.query(Observation).filter_by(session_id=sess.id).count()
    assert remaining == 1


# ---------------------------------------------------------------------------
# FK Cascade
# ---------------------------------------------------------------------------

def test_cascade_delete_session_cleans_observations_and_alerts(db):
    """Deleting a session must cascade-delete its observations and alerts."""
    _, room = _seed_classroom(db)
    sess = start_session(db, classroom_id=room.id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    db.add(Observation(
        session_id=sess.id, track_id=1, ts=now,
        attention_status="Attentive", fatigue_status="Normal",
        attention_score_mean=80, fatigue_index_mean=0.1, confidence_mean=0.9,
        drowsy_frames=0, total_frames=30,
    ))
    db.add(Alert(
        session_id=sess.id, track_id=1, label="S001", type="distraction",
        status="New", message="test", confidence=0.88, created_at=now,
    ))
    db.flush()

    db.delete(sess)
    db.flush()

    assert db.query(Observation).filter_by(session_id=sess.id).count() == 0
    assert db.query(Alert).filter_by(session_id=sess.id).count() == 0
