"""Device Push Token Registration API.

Implements README_MOBILE_ALERT_NOTIFICATIONS.md §6.1 & §7.5:
- POST /devices/push-token: Register or refresh device push token.
- DELETE /devices/push-token: Deactivate device push token on user logout.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_user, require_teacher_or_admin
from app.db.database import get_db
from app.db.models import PushToken, User

router = APIRouter(prefix="/devices", tags=["devices"])

# Expo push token pattern: ExponentPushToken[...] or ExpoPushToken[...] (or TestToken for unit tests)
EXPO_TOKEN_REGEX = re.compile(r"^(ExponentPushToken\[.+\]|ExpoPushToken\[.+\]|TestToken\[.+\])$")


class PushTokenIn(BaseModel):
    token: str = Field(..., description="Expo push token string")
    platform: str = Field("android", description="'android' or 'ios'")


class PushTokenDeleteIn(BaseModel):
    token: str = Field(..., description="Expo push token to deactivate")


def validate_expo_token(token: str) -> None:
    """Validate push token format (S6)."""
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=422,
            detail="Token must be a non-empty string.",
        )
    if not EXPO_TOKEN_REGEX.match(token.strip()):
        raise HTTPException(
            status_code=422,
            detail="Invalid push token format. Expected ExponentPushToken[...] or ExpoPushToken[...].",
        )


@router.post(
    "/push-token",
    summary="Register or Refresh Device Push Token",
    status_code=status.HTTP_200_OK,
)
def register_push_token(
    body: PushTokenIn,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Register or update device push token for authenticated teacher or admin."""
    validate_expo_token(body.token)
    now = datetime.now(timezone.utc)
    clean_platform = body.platform.lower() if body.platform in ("android", "ios") else "android"

    existing = db.query(PushToken).filter_by(token=body.token).first()
    if existing:
        # A token belongs to one user at a time (§7.5): update ownership & activate
        existing.user_id = current_user.id
        existing.platform = clean_platform
        existing.active = True
        existing.last_seen = now
    else:
        new_token = PushToken(
            user_id=current_user.id,
            token=body.token,
            platform=clean_platform,
            created_at=now,
            last_seen=now,
            active=True,
        )
        db.add(new_token)

    db.commit()
    return {"ok": True, "message": "Push token registered successfully."}


@router.delete(
    "/push-token",
    summary="Deactivate Device Push Token on Logout",
    status_code=status.HTTP_200_OK,
)
def delete_push_token(
    body: PushTokenDeleteIn,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Remove or deactivate device push token on logout (S3 & S5)."""
    validate_expo_token(body.token)

    existing = db.query(PushToken).filter_by(token=body.token).first()
    if existing:
        # Security S3: Caller can only deactivate their own token
        if existing.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete another user's push token.",
            )
        existing.active = False
        db.commit()

    return {"ok": True, "message": "Push token deactivated."}
