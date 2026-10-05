"""Live Camera WebSocket Handler — Phase LC-3.

Provides isolated real-time live face detection endpoint for Operator Console:
- Path: /ws/live-camera?token=<jwt>
- Authenticates token and role ('teacher' | 'admin').
- Strictly limits concurrency (LIVE_MAX_CONNECTIONS, LIVE_MAX_PER_USER).
- Rate limits frames via LIVE_MAX_FPS and drops excess frames gracefully.
- Runs inference in isolated executor (_live_executor), returning only JSON results.
- NEVER persists or stores frames, alerts, or telemetry.
"""

import asyncio
import base64
import binascii
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
import logging
import threading
import time
from typing import Any, Dict, Optional

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ai.live_runner import LiveRunner
from app.auth.jwt import decode_access_token, is_token_revoked
from app.config import settings

logger = logging.getLogger("app.ws.live_camera")

router = APIRouter(tags=["live-camera"])

_live_executor = ThreadPoolExecutor(
    max_workers=settings.LIVE_WORKERS,
    thread_name_prefix="live-camera-infer",
)


class FrameTooLarge(Exception):
    """Raised when an incoming frame exceeds byte or pixel dimension bounds."""
    pass


class BadFrame(Exception):
    """Raised when an incoming frame payload cannot be decoded."""
    pass


class LiveLimiter:
    """Thread-safe connection counter enforcing global and per-user caps."""

    def __init__(self, max_global: Optional[int] = None, max_per_user: Optional[int] = None) -> None:
        self._max_global = max_global
        self._max_per_user = max_per_user
        self.active_total = 0
        self.user_counts: Dict[str, int] = {}
        self.lock = threading.Lock()

    @property
    def max_global(self) -> int:
        return self._max_global if self._max_global is not None else settings.LIVE_MAX_CONNECTIONS

    @property
    def max_per_user(self) -> int:
        return self._max_per_user if self._max_per_user is not None else settings.LIVE_MAX_PER_USER

    def acquire(self, user_id: str) -> bool:
        with self.lock:
            if self.active_total >= self.max_global:
                return False
            if self.user_counts.get(user_id, 0) >= self.max_per_user:
                return False
            self.active_total += 1
            self.user_counts[user_id] = self.user_counts.get(user_id, 0) + 1
            return True

    def release(self, user_id: str) -> None:
        with self.lock:
            if self.active_total > 0:
                self.active_total -= 1
            if user_id in self.user_counts:
                self.user_counts[user_id] -= 1
                if self.user_counts[user_id] <= 0:
                    del self.user_counts[user_id]


live_limiter = LiveLimiter()


def _is_origin_allowed(origin: Optional[str]) -> bool:
    """Validate WebSocket origin against allowed list (contracts WS1)."""
    if not origin:
        return True
    origin_clean = origin.strip().lower()
    for allowed in settings.ALLOWED_ORIGINS:
        if origin_clean.startswith(allowed.lower()):
            return True
    if "localhost" in origin_clean or "127.0.0.1" in origin_clean:
        return True
    return False


def decode_frame(b64: str) -> np.ndarray:
    """Safely decode base64 JPEG payload, enforcing byte size and dimension caps."""
    if not b64 or not isinstance(b64, str):
        raise BadFrame()

    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise BadFrame()

    if len(raw) > settings.LIVE_MAX_FRAME_BYTES:
        raise FrameTooLarge()

    try:
        with Image.open(io.BytesIO(raw)) as img:
            w, h = img.size
    except Exception:
        raise BadFrame()

    if max(w, h) > settings.LIVE_MAX_DIM:
        raise FrameTooLarge()

    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise BadFrame()

    return frame


@router.websocket("/ws/live-camera")
async def live_camera_ws(websocket: WebSocket, token: Optional[str] = Query(None)):
    """Interactive live camera detection stream."""
    await websocket.accept()

    # 1. Feature Flag check (Isolation guarantee I1)
    if not settings.LIVE_CAMERA_ENABLED:
        await websocket.close(code=4403, reason="Live camera feature is disabled")
        return

    # 2. Origin check (WS1)
    origin = websocket.headers.get("origin")
    if origin and not _is_origin_allowed(origin):
        await websocket.close(code=4403, reason="Origin not permitted")
        return

    # 3. Authentication & Role check
    if not token or is_token_revoked(token):
        await websocket.close(code=4403, reason="Invalid or missing authentication token")
        return

    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub", "")
        role: str = payload.get("role", "")
    except Exception:
        await websocket.close(code=4403, reason="Invalid token claims")
        return

    if not username or role not in ("teacher", "admin"):
        await websocket.close(code=4403, reason="Teacher or admin role required")
        return

    # 4. Concurrency limits (I9)
    if not live_limiter.acquire(username):
        await websocket.close(code=4429, reason="Too many active live camera connections")
        return

    runner = LiveRunner(cfg=settings)
    started_at = time.monotonic()
    last_ok = 0.0

    try:
        while True:
            # Maximum session duration check
            if time.monotonic() - started_at > settings.LIVE_MAX_SESSION_S:
                await websocket.close(code=4408, reason="Max session duration exceeded")
                return

            # Idle timeout receive
            try:
                msg_text = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.LIVE_IDLE_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=4408, reason="Connection timed out due to inactivity")
                return

            try:
                msg: Dict[str, Any] = json.loads(msg_text)
            except Exception:
                await websocket.send_json({
                    "type": "error",
                    "code": "bad_frame",
                    "message": "Malformed JSON payload.",
                })
                continue

            msg_type = msg.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type != "frame":
                continue

            # Rate limit enforcement
            now = time.monotonic()
            if (now - last_ok) < (1.0 / settings.LIVE_MAX_FPS):
                await websocket.send_json({
                    "type": "skipped",
                    "seq": msg.get("seq"),
                    "reason": "rate_limit",
                })
                continue

            # Frame decoding
            try:
                frame = decode_frame(msg.get("jpeg_b64", ""))
            except FrameTooLarge:
                await websocket.close(code=4413, reason="Frame payload exceeds size bounds")
                return
            except BadFrame:
                await websocket.send_json({
                    "type": "error",
                    "code": "bad_frame",
                    "message": "Frame could not be decoded.",
                })
                continue

            # Run inference in worker executor
            loop = asyncio.get_running_loop()
            try:
                out = await loop.run_in_executor(_live_executor, runner.process, frame)
            except Exception as proc_err:
                logger.error("Error executing live inference: %s", proc_err)
                await websocket.send_json({
                    "type": "error",
                    "code": "infer_error",
                    "message": "Error processing video frame.",
                })
                continue

            last_ok = time.monotonic()
            model_mode = runner.models.lstm_aggregator.model_mode if runner.models else "heuristic"

            await websocket.send_json({
                "type": "live_result",
                "seq": msg.get("seq"),
                "ts": datetime.now(timezone.utc).isoformat(),
                "model_mode": model_mode,
                **out,
            })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Unexpected error in live camera connection: %s", exc)
        try:
            await websocket.close(code=4503, reason="Internal server error")
        except Exception:
            pass
    finally:
        runner.close()
        live_limiter.release(username)
