"""Alerts API router — CON §2.3, CON §3, SYS-9, APP-10/11/20/21.

- GET /alerts: List alerts (teachers scoped to assigned classrooms, no system alerts).
- PATCH /alerts/{id}: Update alert status (New → Viewed → Resolved).
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.alerts.engine import alert_engine
from app.auth.jwt import get_current_user, require_teacher_or_admin
from app.db.database import get_db
from app.db.models import Alert, Classroom, Session, Teacher, TeacherClassroom, User

router = APIRouter(tags=["alerts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AlertOut(BaseModel):
    id: int
    session_id: Optional[int] = None
    track_id: Optional[int] = None
    label: Optional[str] = None
    type: str
    status: str
    message: str
    confidence: float
    created_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertStatusUpdate(BaseModel):
    status: str

    model_config = {"extra": "forbid"}



# ---------------------------------------------------------------------------
# Scoping Helpers
# ---------------------------------------------------------------------------

def _get_teacher_accessible_classroom_ids(db: DBSession, user: User) -> List[int]:
    """Return list of classroom IDs assigned to this teacher."""
    teacher = db.query(Teacher).filter_by(user_id=user.id).first()
    if not teacher:
        return []
    return [
        link.classroom_id
        for link in db.query(TeacherClassroom).filter_by(teacher_id=teacher.id).all()
    ]


def _teacher_can_access_alert(db: DBSession, user: User, alert: Alert) -> bool:
    """Verify if a teacher has authorization to view or mutate an alert."""
    if user.role == "admin":
        return True

    # Teachers cannot access system alerts (admin-only)
    if alert.type in ("camera_offline", "ai_offline") or alert.session_id is None:
        return False

    session = db.get(Session, alert.session_id)
    if not session:
        return False

    classroom_ids = _get_teacher_accessible_classroom_ids(db, user)
    return session.classroom_id in classroom_ids


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=List[AlertOut], summary="List Alerts")
def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (New, Viewed, Resolved)"),
    session_id: Optional[int] = Query(None, description="Filter by session ID"),
    type: Optional[str] = Query(None, description="Filter by alert type"),
    limit: Optional[int] = Query(None, description="Max alerts to return (clamped to 100)"),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> List[AlertOut]:
    """Retrieve alerts with role-based scoping (CON §3, APP-26, DOS5)."""
    query = db.query(Alert)

    if current_user.role == "teacher":
        classroom_ids = _get_teacher_accessible_classroom_ids(db, current_user)
        # Find all session IDs for teacher's classrooms
        allowed_sessions = [
            s.id for s in db.query(Session).filter(Session.classroom_id.in_(classroom_ids)).all()
        ]

        # If teacher requested a specific session_id, verify access
        if session_id is not None:
            if session_id not in allowed_sessions:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "FORBIDDEN", "message": "You cannot access alerts for this session."},
                )
            query = query.filter(Alert.session_id == session_id)
        else:
            query = query.filter(Alert.session_id.in_(allowed_sessions))

        # System alerts are strictly admin-only
        query = query.filter(Alert.type.notin_(["camera_offline", "ai_offline"]))
    else:
        # Admin can query all alerts, including system alerts
        if session_id is not None:
            query = query.filter(Alert.session_id == session_id)

    if status:
        query = query.filter(Alert.status == status)

    if type:
        query = query.filter(Alert.type == type)

    query = query.order_by(Alert.created_at.desc())
    if limit is not None:
        effective_limit = min(max(1, limit), 100)
        query = query.offset(offset).limit(effective_limit)

    return query.all()



@router.patch("/alerts/{alert_id}", response_model=AlertOut, summary="Update Alert Status")
def update_alert_status(
    alert_id: int,
    body: AlertStatusUpdate,
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> AlertOut:
    """Transition alert status (New → Viewed → Resolved)."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Alert {alert_id} not found."},
        )

    if not _teacher_can_access_alert(db, current_user, alert):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You do not have access to this alert."},
        )

    try:
        updated = alert_engine.transition_status(alert, body.status)
        db.commit()
        db.refresh(updated)
        return updated
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_STATE", "message": str(exc)},
        )
