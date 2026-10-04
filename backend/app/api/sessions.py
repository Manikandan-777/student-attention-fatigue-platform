"""Sessions router — CON §3, APP-12/15/16.

POST /sessions — start a session (teacher scoped, admin unrestricted).
POST /sessions/{id}/stop — stop a session.
GET  /sessions — list sessions (teacher sees only their classrooms).
GET  /sessions/{id} — session detail.
GET  /teacher/dashboard — ClassSnapshot for teacher's active sessions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.advisory.engine import advisory_engine
from app.auth.jwt import get_current_user, require_teacher, require_teacher_or_admin
from app.db.database import get_db
from app.db.models import Alert, Observation, Session as SessionModel, Teacher, TeacherClassroom, User
from app.db.session_service import start_session, stop_session

router = APIRouter(tags=["sessions"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SessionOut(BaseModel):
    id: int
    classroom_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str
    students_detected_max: int

    model_config = {"from_attributes": True}


class StartSessionRequest(BaseModel):
    classroom_id: int


class StopSessionRequest(BaseModel):
    status: str = "Completed"   # "Completed" | "Aborted"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _can_access_classroom(db: DBSession, user: User, classroom_id: int) -> bool:
    if user.role == "admin":
        return True
    teacher = db.query(Teacher).filter_by(user_id=user.id).first()
    if not teacher:
        return False
    return db.query(TeacherClassroom).filter_by(
        teacher_id=teacher.id, classroom_id=classroom_id
    ).first() is not None


def _get_session_or_404(db: DBSession, session_id: int) -> SessionModel:
    s = db.get(SessionModel, session_id)
    if not s:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Session not found."},
        )
    return s


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: StartSessionRequest,
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> SessionOut:
    """Start a new monitoring session. Teachers must own the classroom."""
    if not _can_access_classroom(db, current_user, body.classroom_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You are not assigned to this classroom."},
        )
    sess = start_session(db, classroom_id=body.classroom_id)
    db.commit()
    db.refresh(sess)
    return sess


@router.post("/sessions/{session_id}/stop", response_model=SessionOut)
def end_session(
    session_id: int,
    body: StopSessionRequest = StopSessionRequest(),
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> SessionOut:
    """Stop an active session (teacher must own the classroom)."""
    sess = _get_session_or_404(db, session_id)
    if not _can_access_classroom(db, current_user, sess.classroom_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You are not assigned to this classroom."},
        )
    try:
        stopped = stop_session(db, session_id=session_id, status=body.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "INVALID_STATE", "message": str(exc)})
    db.commit()
    db.refresh(stopped)
    return stopped


@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(
    limit: Optional[int] = Query(None, description="Max sessions to return (clamped to 100)"),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> List[SessionOut]:
    """List sessions with role scoping and clamped pagination (DOS5)."""
    q = db.query(SessionModel)
    if current_user.role != "admin":
        teacher = db.query(Teacher).filter_by(user_id=current_user.id).first()
        if not teacher:
            return []
        classroom_ids = [
            link.classroom_id
            for link in db.query(TeacherClassroom).filter_by(teacher_id=teacher.id).all()
        ]
        q = q.filter(SessionModel.classroom_id.in_(classroom_ids))
    q = q.order_by(SessionModel.started_at.desc())
    if limit is not None:
        effective_limit = min(max(1, limit), 100)
        q = q.offset(offset).limit(effective_limit)
    return q.all()


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> SessionOut:
    sess = _get_session_or_404(db, session_id)
    if not _can_access_classroom(db, current_user, sess.classroom_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You are not assigned to this classroom."},
        )
    return sess


@router.get("/teacher/dashboard", response_model=List[Dict[str, Any]])
def teacher_dashboard(
    current_user: User = Depends(require_teacher),
    db: DBSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """ClassSnapshot list for all active (Monitoring) sessions for this teacher only (CON §3 R4)."""
    q = db.query(SessionModel).filter(SessionModel.status == "Monitoring")
    teacher = db.query(Teacher).filter_by(user_id=current_user.id).first()
    if not teacher:
        return []
    classroom_ids = [
        link.classroom_id
        for link in db.query(TeacherClassroom).filter_by(teacher_id=teacher.id).all()
    ]
    q = q.filter(SessionModel.classroom_id.in_(classroom_ids))

    snapshots = []
    for sess in q.all():
        class_name = sess.classroom.class_name if sess.classroom else ""
        open_alerts = db.query(Alert).filter_by(session_id=sess.id, status="New").count()

        # Retrieve recent observations to compute counts and class fatigue advisory
        recent_obs = (
            db.query(Observation)
            .filter_by(session_id=sess.id)
            .order_by(Observation.ts.desc())
            .limit(100)
            .all()
        )

        counts = {"attentive": 0, "distracted": 0, "unknown": 0, "fatigued": 0}
        avg_score = 0.0
        advisory = None

        if recent_obs:
            scores = []
            tracks_for_advisory = []
            for obs in recent_obs:
                att_status = (obs.attention_status or "Unknown").lower()
                fat_status = (obs.fatigue_status or "Normal").lower()

                if att_status in counts:
                    counts[att_status] += 1
                if fat_status == "fatigued":
                    counts["fatigued"] += 1

                if obs.attention_score_mean is not None:
                    scores.append(obs.attention_score_mean)

                tracks_for_advisory.append({
                    "fatigue_status": obs.fatigue_status,
                    "fatigue_index": obs.fatigue_index_mean,
                })

            if scores:
                avg_score = round(float(sum(scores) / len(scores)), 1)

            advisory, _ = advisory_engine.process_class_tracks(
                session_id=sess.id,
                tracks=tracks_for_advisory,
                class_name=class_name or "Classroom",
            )

        snapshots.append({
            "session_id": sess.id,
            "class_name": class_name,
            "status": sess.status,
            "students_detected": sess.students_detected_max,
            "counts": counts,
            "avg_attention_score": avg_score,
            "open_alerts": open_alerts,
            "fatigue_advisory": advisory,
        })
    return snapshots
