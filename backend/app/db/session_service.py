"""Session & Observation Service — Phase 13.

Implements SYS-12, APP-12, CON §7:
- Session start/stop with automatic UTC timestamps and status transitions.
- Observation aggregation flush (call every OBSERVATION_INTERVAL_S = 5 s from the pipeline).
- Data-retention purge job: deletes observations and alerts older than RETENTION_DAYS.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.db.models import Alert, Observation, Session, TrackRosterMap


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

def start_session(db: DBSession, classroom_id: int) -> Session:
    """Create and persist a new monitoring session (status → Monitoring)."""
    session = Session(
        classroom_id=classroom_id,
        started_at=_utcnow(),
        status="Monitoring",
        students_detected_max=0,
    )
    db.add(session)
    db.flush()          # get the assigned id within the transaction
    return session


def stop_session(db: DBSession, session_id: int, status: str = "Completed") -> Optional[Session]:
    """Mark a session as Completed (or Aborted) and record ended_at."""
    if status not in ("Completed", "Aborted"):
        raise ValueError(f"Invalid stop status: {status!r}. Use 'Completed' or 'Aborted'.")

    session = db.get(Session, session_id)
    if session is None:
        return None
    if session.status not in ("Monitoring", "Scheduled"):
        raise ValueError(f"Session {session_id} is already {session.status}; cannot stop.")

    session.ended_at = _utcnow()
    session.status = status
    db.flush()
    return session


def get_session(db: DBSession, session_id: int) -> Optional[Session]:
    """Fetch a session by id."""
    return db.get(Session, session_id)


def list_sessions(db: DBSession, classroom_id: Optional[int] = None) -> List[Session]:
    """List all sessions, optionally filtered by classroom."""
    q = db.query(Session)
    if classroom_id is not None:
        q = q.filter(Session.classroom_id == classroom_id)
    return q.order_by(Session.started_at.desc()).all()


# ---------------------------------------------------------------------------
# Observation aggregation
# ---------------------------------------------------------------------------

def flush_observation(
    db: DBSession,
    session_id: int,
    track_id: int,
    attention_status: str,
    fatigue_status: str,
    attention_score_mean: float,
    fatigue_index_mean: float,
    confidence_mean: float,
    drowsy_frames: int,
    total_frames: int,
    ts: Optional[datetime] = None,
) -> Observation:
    """Persist one aggregated observation row (called every OBSERVATION_INTERVAL_S).

    Updates session.students_detected_max if needed.
    """
    obs = Observation(
        session_id=session_id,
        track_id=track_id,
        ts=ts or _utcnow(),
        attention_status=attention_status,
        fatigue_status=fatigue_status,
        attention_score_mean=round(float(attention_score_mean), 4),
        fatigue_index_mean=round(float(fatigue_index_mean), 4),
        confidence_mean=round(float(confidence_mean), 4),
        drowsy_frames=int(drowsy_frames),
        total_frames=int(total_frames),
    )
    db.add(obs)

    # Keep students_detected_max updated
    session = db.get(Session, session_id)
    if session is not None and track_id > session.students_detected_max:
        session.students_detected_max = track_id

    db.flush()
    return obs


def flush_observations_bulk(
    db: DBSession,
    session_id: int,
    records: List[Dict[str, Any]],
) -> List[Observation]:
    """Bulk-insert multiple observation rows in one DB round-trip."""
    results = []
    for rec in records:
        obs = flush_observation(db, session_id=session_id, **rec)
        results.append(obs)
    return results


# ---------------------------------------------------------------------------
# Alert persistence
# ---------------------------------------------------------------------------

def store_alert(
    db: DBSession,
    session_id: int,
    track_id: int,
    label: str,
    alert_type: str,
    message: str,
    confidence: float,
    ts: Optional[datetime] = None,
) -> Alert:
    """Persist an alert that was emitted by the scoring engine."""
    alert = Alert(
        session_id=session_id,
        track_id=track_id,
        label=label,
        type=alert_type,
        status="New",
        message=message,
        confidence=round(float(confidence), 4),
        created_at=ts or _utcnow(),
    )
    db.add(alert)
    db.flush()
    return alert


# ---------------------------------------------------------------------------
# Retention job
# ---------------------------------------------------------------------------

def run_retention_purge(db: DBSession, retention_days: Optional[int] = None) -> Dict[str, int]:
    """Delete observations and alerts older than RETENTION_DAYS.

    Returns counts of deleted rows per table.
    Per spec: no images, no face crops are ever stored — only numeric aggregates.
    """
    days = retention_days if retention_days is not None else settings.RETENTION_DAYS
    cutoff = _utcnow() - timedelta(days=days)

    deleted_obs = (
        db.query(Observation)
        .filter(Observation.ts < cutoff)
        .delete(synchronize_session="fetch")
    )
    deleted_alerts = (
        db.query(Alert)
        .filter(Alert.created_at < cutoff)
        .delete(synchronize_session="fetch")
    )

    db.flush()
    return {"observations_deleted": deleted_obs, "alerts_deleted": deleted_alerts}
