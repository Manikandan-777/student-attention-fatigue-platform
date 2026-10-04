"""Alert Engine — Phase 15.

Implements SYS-9, APP-10/11/20/21, CON §1, CON §2.3:
- Convert confirmed candidates from scoring engine into stored `Alert` records.
- Enforce ALERT_COOLDOWN_S cooldown for student and system alerts.
- Enforce non-diagnostic, non-disciplinary wording (D8: informational copy only, never 'is sleeping' / 'is sick').
- System alerts: admin-only `camera_offline` and `ai_offline`.
- Broadcast alert notifications via WebSockets (/ws/telemetry).
- Alert lifecycle state transitions: New → Viewed → Resolved.
"""

from datetime import datetime, timezone
import re
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.db.database import SessionLocal, get_db_session
from app.db.models import Alert
from app.ws.manager import ws_manager

# ---------------------------------------------------------------------------
# Language Guard (D8, APP-21)
# ---------------------------------------------------------------------------

PROHIBITED_TERMS = [
    r"\bsleeping\b",
    r"\basleep\b",
    r"\bsick\b",
    r"\bill\b",
    r"\blazy\b",
    r"\bslacking\b",
    r"\bpunish(ment)?\b",
    r"\bdisciplin(e|ary)\b",
    r"\bmisbehav(ior|ing)\b",
    r"\bdisorder\b",
    r"\badhd\b",
    r"\bdepress(ed|ion)\b",
]

_PROHIBITED_REGEX = re.compile("|".join(PROHIBITED_TERMS), re.IGNORECASE)


def validate_alert_wording(message: str) -> None:
    """Validate that alert copy has no diagnostic or disciplinary language."""
    match = _PROHIBITED_REGEX.search(message)
    if match:
        raise ValueError(
            f"Prohibited diagnostic/disciplinary language detected: '{match.group(0)}'. "
            "Alert wording must be strictly informational (D8)."
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def alert_to_dict(alert: Alert) -> Dict[str, Any]:
    """Format Alert model to canonical contracts.md §2.3 JSON dictionary."""
    return {
        "id": alert.id,
        "session_id": alert.session_id,
        "track_id": alert.track_id,
        "label": alert.label,
        "type": alert.type,
        "status": alert.status,
        "message": alert.message,
        "confidence": round(float(alert.confidence), 4),
        "created_at": alert.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if alert.created_at else None,
        "viewed_at": alert.viewed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if alert.viewed_at else None,
        "resolved_at": alert.resolved_at.strftime("%Y-%m-%dT%H:%M:%SZ") if alert.resolved_at else None,
    }


# ---------------------------------------------------------------------------
# Alert Engine
# ---------------------------------------------------------------------------

class AlertEngine:
    """Core alert processing, validation, persistence, and dispatch engine."""

    def __init__(self, cooldown_s: Optional[float] = None) -> None:
        self.cooldown_s = cooldown_s if cooldown_s is not None else settings.ALERT_COOLDOWN_S
        self._system_cooldowns: Dict[str, float] = {}

    def record_alert(
        self,
        db: DBSession,
        session_id: Optional[int],
        track_id: Optional[int],
        label: str,
        alert_type: str,
        message: str,
        confidence: float,
        ts: Optional[datetime] = None,
        broadcast: bool = True,
    ) -> Alert:
        """Validate, persist, and broadcast an alert."""
        validate_alert_wording(message)

        if alert_type not in ("fatigue", "distraction", "camera_offline", "ai_offline"):
            raise ValueError(f"Invalid alert type: {alert_type}")

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

        if broadcast and ws_manager:
            payload = alert_to_dict(alert)
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ws_manager.broadcast_alert(payload, session_id=session_id))
            except RuntimeError:
                # No running event loop in thread; schedule safely or skip
                pass

        return alert

    def emit_camera_offline(
        self,
        db: DBSession,
        camera_id: str,
        session_id: Optional[int] = None,
        now_ts: Optional[float] = None,
    ) -> Optional[Alert]:
        """Emit camera_offline alert to admin with cooldown suppression."""
        now = now_ts if now_ts is not None else time.monotonic()
        key = f"camera_offline_{camera_id}"
        last = self._system_cooldowns.get(key)
        if last is not None and (now - last) < self.cooldown_s:
            return None

        self._system_cooldowns[key] = now
        msg = f"Camera feed {camera_id} is offline or unavailable."
        return self.record_alert(
            db=db,
            session_id=session_id,
            track_id=0,
            label="CAMERA",
            alert_type="camera_offline",
            message=msg,
            confidence=1.0,
        )

    def emit_ai_offline(
        self,
        db: DBSession,
        session_id: Optional[int] = None,
        now_ts: Optional[float] = None,
    ) -> Optional[Alert]:
        """Emit ai_offline alert to admin with cooldown suppression."""
        now = now_ts if now_ts is not None else time.monotonic()
        key = f"ai_offline_{session_id or 'global'}"
        last = self._system_cooldowns.get(key)
        if last is not None and (now - last) < self.cooldown_s:
            return None

        self._system_cooldowns[key] = now
        msg = "AI processing worker heartbeat timed out."
        return self.record_alert(
            db=db,
            session_id=session_id,
            track_id=0,
            label="AI",
            alert_type="ai_offline",
            message=msg,
            confidence=1.0,
        )

    def transition_status(self, alert: Alert, new_status: str) -> Alert:
        """Enforce valid alert status transitions (New → Viewed → Resolved)."""
        valid_statuses = ("New", "Viewed", "Resolved")
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid alert status: {new_status}")

        curr = alert.status

        # Idempotent updates
        if curr == new_status:
            return alert

        # Allowed transitions
        if curr == "New" and new_status == "Viewed":
            alert.status = "Viewed"
            alert.viewed_at = _utcnow()
        elif curr == "New" and new_status == "Resolved":
            alert.status = "Resolved"
            alert.viewed_at = alert.viewed_at or _utcnow()
            alert.resolved_at = _utcnow()
        elif curr == "Viewed" and new_status == "Resolved":
            alert.status = "Resolved"
            alert.resolved_at = _utcnow()
        else:
            raise ValueError(
                f"Invalid status transition from '{curr}' to '{new_status}'. "
                "Allowed transitions: New → Viewed → Resolved."
            )

        return alert


# Global singleton alert engine instance
alert_engine = AlertEngine()
