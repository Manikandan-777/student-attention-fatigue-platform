"""System status router — GET /system/status (admin only). CON §2.5, CON §3."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.auth.jwt import require_admin
from app.config import settings
from app.db.database import get_db
from app.db.models import Camera, User

router = APIRouter(tags=["system"])


@router.get("/system/status", response_model=Dict[str, Any])
def system_status(
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> Dict[str, Any]:
    """SystemStatus snapshot (CON §2.5). Admin only."""
    cameras: List[Dict[str, Any]] = [
        {"id": cam.id, "state": cam.state}
        for cam in db.query(Camera).all()
    ]
    return {
        "ai_server": "Online",
        "database": "Online",
        "api": "Online",
        "cameras": cameras,
        "fps": 0.0,
        "model_mode": "heuristic",
        "privacy_mode": settings.PRIVACY_MODE,
    }
