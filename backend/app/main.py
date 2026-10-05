"""FastAPI Application Core & WebSocket Infrastructure.

Implements SYS-10, APP-24, APP-27, CON §3, CON §4:
- Liveness health probe (/health).
- Telemetry WebSocket channel (/ws/telemetry) with ping/pong and session subscription.
- Video WebSocket channel (/ws/video) strictly enforcing close code 4403 when PRIVACY_MODE=true.
- CORS middleware for Operator Console and Mobile integration.
- Phase 14: Auth + all REST API routers.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.ws.manager import ws_manager
from app.db.database import create_tables
from app.auth.router import router as auth_router
from app.api.classrooms import router as classrooms_router
from app.api.students import router as students_router
from app.api.teachers import router as teachers_router
from app.api.sessions import router as sessions_router
from app.api.system import router as system_router
from app.api.alerts import router as alerts_router
from app.api.reports import router as reports_router
from app.api.camera import router as camera_router
from app.api.devices import router as devices_router
from app.ws.live_camera import router as live_camera_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    create_tables()   # ensure schema exists (Alembic handles prod migrations)
    # Ensure default users exist for console login
    from app.db.database import SessionLocal
    from app.db.models import User
    from app.auth.jwt import hash_password
    db_init = SessionLocal()
    try:
        if not db_init.query(User).filter_by(username="admin").first():
            db_init.add(User(username="admin", password_hash=hash_password("adminpass"), role="admin", active=True))
        if not db_init.query(User).filter_by(username="teacher").first():
            db_init.add(User(username="teacher", password_hash=hash_password("teachpass"), role="teacher", active=True))
        db_init.commit()
    except Exception as exc:
        logger.warning("Could not auto-seed default users: %s", exc)
    finally:
        db_init.close()

    import asyncio
    from app.camera.service import live_camera_service
    try:
        live_camera_service.set_event_loop(asyncio.get_running_loop())
    except Exception as exc:
        logger.warning("Could not register event loop for live_camera_service: %s", exc)

    logger.info(
        "Booting Student Attention & Fatigue Detection API (Privacy Mode: %s)...",
        settings.PRIVACY_MODE,
    )
    yield
    logger.info("Shutting down API server...")


app = FastAPI(
    title="Student Attention & Fatigue Detection System",
    description="Edge-cloud hybrid analytics platform for non-intrusive classroom telemetry.",
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    """Strip server version header (API11) and inject defensive security headers."""
    response = await call_next(request)
    if "server" in response.headers:
        del response.headers["server"]
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


# Enable CORS with explicit origin allow-list (API8: no wildcard with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register Phase 14 routers
app.include_router(auth_router)
app.include_router(classrooms_router)
app.include_router(students_router)
app.include_router(teachers_router)
app.include_router(sessions_router)
app.include_router(system_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(camera_router)
app.include_router(devices_router)
app.include_router(live_camera_router)


def _is_origin_allowed(origin: Optional[str]) -> bool:
    """Validate WebSocket origin against allowed list (WS1)."""
    if not origin:
        return True
    origin_clean = origin.strip().lower()
    for allowed in settings.ALLOWED_ORIGINS:
        if origin_clean.startswith(allowed.lower()):
            return True
    if "localhost" in origin_clean or "127.0.0.1" in origin_clean:
        return True
    return False


@app.get("/health", summary="Service Liveness Probe")
async def health() -> Dict[str, Any]:
    """Liveness probe exposing service status, privacy state, and timestamp (API3)."""
    return {
        "status": "ok",
        "app": "Student Attention & Fatigue Detection API",
        "version": "1.0.0",
        "privacy_mode": settings.PRIVACY_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket, token: Optional[str] = Query(None)):
    """Telemetry stream endpoint (contracts.md §4).

    Consumes validated results only (no image pixels).
    Enforces JWT authentication query parameter (W1, W2, W3).
    Supports:
    - {"type": "ping"} -> responds {"type": "pong"}
    - {"type": "subscribe", "session_id": <id>} -> subscribes to session updates
    """
    origin = websocket.headers.get("origin")
    if origin and not _is_origin_allowed(origin):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not permitted (WS1)")
        return

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return

    from app.auth.jwt import decode_access_token, is_token_revoked
    if is_token_revoked(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token has been revoked (SM1)")
        return

    try:
        payload = decode_access_token(token)
        if not payload.get("sub"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token claims")
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    if len(ws_manager.telemetry_connections) >= settings.MAX_WS_CONNECTIONS:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Connection quota exceeded (DOS2)")
        return

    await ws_manager.connect_telemetry(websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "subscribe":
                session_id = msg.get("session_id")
                if isinstance(session_id, int) and session_id > 0:
                    from app.db.database import SessionLocal
                    from app.db.models import Session as SessionModel, Teacher, TeacherClassroom, User
                    db_ws = SessionLocal()
                    try:
                        user = db_ws.query(User).filter_by(username=payload.get("sub"), active=True).first()
                        allowed = True
                        if user and user.role == "teacher":
                            teacher = db_ws.query(Teacher).filter_by(user_id=user.id).first()
                            if teacher:
                                sess = db_ws.get(SessionModel, session_id)
                                if not sess:
                                    allowed = False
                                else:
                                    link = db_ws.query(TeacherClassroom).filter_by(
                                        teacher_id=teacher.id, classroom_id=sess.classroom_id
                                    ).first()
                                    allowed = link is not None
                            else:
                                allowed = False
                        if allowed:
                            ws_manager.subscribe_session(websocket, session_id)
                            await websocket.send_json({
                                "type": "subscribed",
                                "session_id": session_id,
                                "status": "ok",
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Unauthorized session subscription",
                            })
                    finally:
                        db_ws.close()
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid or missing session_id",
                    })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unsupported message type: {msg_type}",
                })

    except WebSocketDisconnect:
        ws_manager.disconnect_telemetry(websocket)
    except Exception as exc:
        logger.warning("Telemetry websocket exception: %s", exc)
        ws_manager.disconnect_telemetry(websocket)


@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket, token: Optional[str] = Query(None)):
    """Operator Console video stream endpoint (contracts.md §4).

    CRITICAL PRIVACY RULE (SYS-10, APP-24, APP-27, CON §4):
    If PRIVACY_MODE is true, immediately reject with close code 4403.
    Also validates authentication token (W4, W5, W6, WS1).
    """
    origin = websocket.headers.get("origin")
    if origin and not _is_origin_allowed(origin):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not permitted (WS1)")
        return

    if settings.PRIVACY_MODE:
        # Non-negotiable requirement: close with code 4403
        logger.warning(
            "Rejecting /ws/video connection with code 4403: PRIVACY_MODE is enabled."
        )
        await websocket.close(
            code=4403,
            reason="Privacy Mode Active: Video streaming is disabled.",
        )
        return

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return

    from app.auth.jwt import decode_access_token, is_token_revoked
    if is_token_revoked(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token has been revoked (SM1)")
        return

    try:
        payload = decode_access_token(token)
        if not payload.get("sub"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token claims")
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return



    # If privacy mode is false, accept connection
    await ws_manager.connect_video(websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect_video(websocket)
    except Exception as exc:
        logger.warning("Video websocket exception: %s", exc)
        ws_manager.disconnect_video(websocket)
