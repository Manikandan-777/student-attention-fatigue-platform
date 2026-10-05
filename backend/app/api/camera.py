"""Live Camera API Router — 1,000 Faces and Physical Webcam Stream.

Provides:
- POST /camera/start — Start the live camera (1000_faces mode or webcam mode).
- POST /camera/stop — Stop the live camera.
- GET  /camera/status — Operational health and telemetry summary.
- GET  /camera/feed — Real-time MJPEG live video stream (viewable in browser or <img> tags).
- POST /camera/toggle-privacy — Toggle privacy mode on/off for live video inspection.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.camera.service import live_camera_service
from app.config import settings

router = APIRouter(prefix="/camera", tags=["camera"])


class CameraStartRequest(BaseModel):
    mode: str = "webcam"           # "webcam" | "1000_faces"
    camera_index: int = 0
    session_id: int = 1
    privacy_mode: Optional[bool] = None


@router.post("/start", summary="Start Live Camera Detection Pipeline")
async def start_camera(body: CameraStartRequest = CameraStartRequest()) -> Dict[str, Any]:
    """Start live camera detection for 1,000 faces or physical webcam."""
    import asyncio
    try:
        live_camera_service.set_event_loop(asyncio.get_running_loop())
    except Exception:
        pass

    if body.privacy_mode is not None:
        settings.PRIVACY_MODE = body.privacy_mode

    status_data = live_camera_service.start(
        mode=body.mode,
        camera_index=body.camera_index,
        session_id=body.session_id,
    )
    return {
        "status": "started",
        "details": status_data,
    }


@router.post("/stop", summary="Stop Live Camera Pipeline")
def stop_camera() -> Dict[str, Any]:
    """Stop active live camera pipeline."""
    status_data = live_camera_service.stop()
    return {
        "status": "stopped",
        "details": status_data,
    }


@router.get("/status", summary="Get Live Camera Telemetry & Detection Status")
def get_camera_status() -> Dict[str, Any]:
    """Return operational state, detected face counts, and average attention score."""
    return live_camera_service.get_status()


@router.post("/toggle-privacy", summary="Toggle Privacy Mode for Live Video Stream")
def toggle_privacy() -> Dict[str, Any]:
    """Toggle system privacy mode. When false, live video stream (/camera/feed) is enabled."""
    settings.PRIVACY_MODE = not settings.PRIVACY_MODE
    return {
        "privacy_mode": settings.PRIVACY_MODE,
        "message": "Live video streaming enabled." if not settings.PRIVACY_MODE else "Privacy mode active (video streaming blocked).",
    }


@router.get("/feed", summary="Real-Time MJPEG Camera Video Stream")
async def live_camera_feed(token: Optional[str] = Query(None)):
    """Stream live annotated video feed as MJPEG multipart stream.
    
    Renders tracked students with real-time green/red/amber bounding boxes
    and fatigue predictions. Viewable directly in any web browser or HTML <img> tag.
    """
    import asyncio
    try:
        live_camera_service.set_event_loop(asyncio.get_running_loop())
    except Exception:
        pass

    if not live_camera_service.is_running:
        # Default to real webcam mode
        live_camera_service.start(mode="webcam")

    return StreamingResponse(
        live_camera_service.mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
