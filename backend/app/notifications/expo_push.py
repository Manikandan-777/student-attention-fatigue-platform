"""Expo Push Notification Service for Mobile Class Fatigue Alerts.

Implements README_MOBILE_ALERT_NOTIFICATIONS.md §6.3 & §7.3:
- Builds compliant push payloads with loud sound ("alert_high.wav"), channel IDs,
  interruption levels, high priority, and TTL.
- Sends batches of up to 100 messages to Expo Push API.
- Cleans up invalid/unregistered device tokens ("DeviceNotRegistered").
- Strictly adheres to Privacy S1 (class-level text only, no student data)
  and S7 (tokens and bodies never logged in clear text).
- Failures are handled gracefully without ever blocking telemetry or the AI loop.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import PushToken, Session as SessionModel, Teacher, TeacherClassroom, User

logger = logging.getLogger("app.notifications.expo_push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"


def build_push_payload(token: str, adv_data: Dict[str, Any]) -> Dict[str, Any]:
    """Construct canonical Expo push notification payload conforming to §6.3."""
    level = int(adv_data.get("level", 1))
    class_name = adv_data.get("class_name", "Classroom")
    message = adv_data.get("message", "Continue with the class.")
    session_id = adv_data.get("session_id", 0)
    code = adv_data.get("code", "CONTINUE")
    since = adv_data.get("since") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Time-sensitive for levels 3 and 4, active for levels 1 and 2
    interruption_level = "time-sensitive" if level >= 3 else "active"

    return {
        "to": token,
        "title": f"{class_name}: fatigue indicator",
        "body": message,
        "data": {
            "session_id": session_id,
            "level": level,
            "code": code,
            "since": since,
        },
        "sound": "alert_high.wav",
        "priority": "high",
        "channelId": f"fatigue-l{level}-v1",
        "interruptionLevel": interruption_level,
        "ttl": settings.PUSH_TTL_S,
    }


def handle_tickets(tickets: List[Dict[str, Any]], tokens: List[str], db: Optional[Session] = None) -> None:
    """Process ticket responses from Expo Push service, deactivating invalid tokens (S7 compliant)."""
    for i, ticket in enumerate(tickets):
        status = ticket.get("status")
        if status == "error":
            err_code = ticket.get("details", {}).get("error")
            # Log failure reason without exposing token or message content (Privacy S7)
            logger.warning("Push delivery ticket error: %s", err_code or "UnknownError")
            if err_code == "DeviceNotRegistered" and db is not None and i < len(tokens):
                target_token = tokens[i]
                try:
                    tok_row = db.query(PushToken).filter_by(token=target_token).first()
                    if tok_row:
                        tok_row.active = False
                        db.commit()
                except Exception as exc:
                    logger.debug("Could not deactivate unregistered token: %s", exc)


async def send_expo_messages(messages: List[Dict[str, Any]], tokens: List[str], db: Optional[Session] = None) -> None:
    """Async dispatch of push messages to Expo in chunks of 100."""
    if not messages:
        return

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
    }
    if settings.EXPO_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(0, len(messages), 100):
            batch_messages = messages[i:i + 100]
            batch_tokens = tokens[i:i + 100]
            try:
                resp = await client.post(EXPO_PUSH_URL, json=batch_messages, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    handle_tickets(data, batch_tokens, db)
                else:
                    logger.warning("Expo push service returned HTTP %d", resp.status_code)
            except Exception as exc:
                logger.warning("Push network dispatch error: %s", exc)


def get_classroom_teacher_tokens(session_id: int, db: Session) -> List[str]:
    """Retrieve active push tokens for teachers assigned to the session's classroom (S4)."""
    sess = db.get(SessionModel, session_id)
    if not sess or not sess.classroom_id:
        return []

    # Find teachers assigned to this classroom
    classroom_links = db.query(TeacherClassroom).filter_by(classroom_id=sess.classroom_id).all()
    teacher_ids = [link.teacher_id for link in classroom_links]
    if not teacher_ids:
        return []

    teachers = db.query(Teacher).filter(Teacher.id.in_(teacher_ids)).all()
    user_ids = [t.user_id for t in teachers if t.user_id is not None]
    if not user_ids:
        return []

    # Active push tokens for these users
    tokens = (
        db.query(PushToken.token)
        .filter(PushToken.user_id.in_(user_ids), PushToken.active == True)
        .all()
    )
    return [t[0] for t in tokens]


async def dispatch_advisory_push(
    session_id: int,
    advisory_data: Dict[str, Any],
    db: Session,
) -> Dict[str, Any]:
    """Look up recipients, build payloads, and send push notifications for an advisory event."""
    if not settings.PUSH_ENABLED:
        return {"status": "disabled", "sent": 0}

    level = int(advisory_data.get("level", 1))
    if level == 1 and not settings.PUSH_NOTIFY_LEVEL1:
        return {"status": "skipped_level_1", "sent": 0}

    tokens = get_classroom_teacher_tokens(session_id, db)
    if not tokens:
        return {"status": "no_active_tokens", "sent": 0}

    messages = [build_push_payload(tok, advisory_data) for tok in tokens]
    await send_expo_messages(messages, tokens, db)
    return {"status": "sent", "sent": len(messages)}
