"""Integration & Security tests for /ws/live-camera (Phase LC-3, LS1-LS12).

Verifies:
- LS1: Connect without token or invalid token -> 4403
- LS2: Role other than teacher/admin -> 4403
- LS3: Origin not in allow-list -> 4403
- LS4: LIVE_CAMERA_ENABLED=False -> 4403
- LS5: Concurrency per user cap -> 4429
- LS6: Global concurrency cap -> 4429
- LS7: Oversized payload bytes -> 4413
- LS8: Pixel dimension bomb -> 4413
- LS9: Malformed base64 / non-image -> {"type": "error", "code": "bad_frame"}
- LS10: Exceeding LIVE_MAX_FPS -> {"type": "skipped", "reason": "rate_limit"}
- Ping / Pong mechanics
"""

import base64
import io
import pytest
from PIL import Image
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.auth.jwt import create_access_token
from app.config import settings
from app.main import app
from app.ws.live_camera import live_limiter


def _make_jpeg_b64(width=320, height=240, color=(100, 150, 200)) -> str:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.fixture(autouse=True)
def reset_limiter_and_settings():
    # Ensure fresh limiter state
    with live_limiter.lock:
        live_limiter.active_total = 0
        live_limiter.user_counts.clear()

    orig_flag = settings.LIVE_CAMERA_ENABLED
    orig_max_global = settings.LIVE_MAX_CONNECTIONS
    orig_max_user = settings.LIVE_MAX_PER_USER
    orig_max_fps = settings.LIVE_MAX_FPS
    orig_max_dim = settings.LIVE_MAX_DIM
    orig_max_bytes = settings.LIVE_MAX_FRAME_BYTES

    yield

    with live_limiter.lock:
        live_limiter.active_total = 0
        live_limiter.user_counts.clear()

    settings.LIVE_CAMERA_ENABLED = orig_flag
    settings.LIVE_MAX_CONNECTIONS = orig_max_global
    settings.LIVE_MAX_PER_USER = orig_max_user
    settings.LIVE_MAX_FPS = orig_max_fps
    settings.LIVE_MAX_DIM = orig_max_dim
    settings.LIVE_MAX_FRAME_BYTES = orig_max_bytes


class TestLiveCameraWebSocket:
    def test_ls4_flag_off_closes_with_4403(self):
        settings.LIVE_CAMERA_ENABLED = False
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
                ws.receive_json()
        assert exc_info.value.code == 4403

    def test_ls1_missing_or_bad_token_closes_with_4403(self):
        settings.LIVE_CAMERA_ENABLED = True
        client = TestClient(app)

        # Missing token
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/live-camera") as ws:
                ws.receive_json()
        assert exc_info.value.code == 4403

        # Invalid token
        with pytest.raises(WebSocketDisconnect) as exc_info2:
            with client.websocket_connect("/ws/live-camera?token=garbage_token_value") as ws:
                ws.receive_json()
        assert exc_info2.value.code == 4403

    def test_ls2_non_teacher_admin_role_closes_with_4403(self):
        settings.LIVE_CAMERA_ENABLED = True
        token = create_access_token(subject="student1", role="student")
        client = TestClient(app)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
                ws.receive_json()
        assert exc_info.value.code == 4403

    def test_ls3_disallowed_origin_closes_with_4403(self):
        settings.LIVE_CAMERA_ENABLED = True
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                f"/ws/live-camera?token={token}",
                headers={"Origin": "https://malicious-site.example.com"},
            ) as ws:
                ws.receive_json()
        assert exc_info.value.code == 4403

    def test_ls5_per_user_concurrency_limit_closes_with_4429(self):
        settings.LIVE_CAMERA_ENABLED = True
        settings.LIVE_MAX_PER_USER = 1
        settings.LIVE_MAX_CONNECTIONS = 10
        token = create_access_token(subject="teacher_concurrent", role="teacher")
        client = TestClient(app)

        with client.websocket_connect(f"/ws/live-camera?token={token}") as ws1:
            ws1.send_json({"type": "ping"})
            assert ws1.receive_json() == {"type": "pong"}

            # Second concurrent connection from same user
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect(f"/ws/live-camera?token={token}") as ws2:
                    ws2.receive_json()
            assert exc_info.value.code == 4429

    def test_ls6_global_concurrency_limit_closes_with_4429(self):
        settings.LIVE_CAMERA_ENABLED = True
        settings.LIVE_MAX_CONNECTIONS = 1
        settings.LIVE_MAX_PER_USER = 2
        token1 = create_access_token(subject="teacher_a", role="teacher")
        token2 = create_access_token(subject="teacher_b", role="teacher")
        client = TestClient(app)

        with client.websocket_connect(f"/ws/live-camera?token={token1}") as ws1:
            ws1.send_json({"type": "ping"})
            assert ws1.receive_json() == {"type": "pong"}

            # Second connection from different user exceeds global cap (1)
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect(f"/ws/live-camera?token={token2}") as ws2:
                    ws2.receive_json()
            assert exc_info.value.code == 4429

    def test_ping_pong(self):
        settings.LIVE_CAMERA_ENABLED = True
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
            ws.send_json({"type": "ping"})
            res = ws.receive_json()
            assert res == {"type": "pong"}

    def test_ls9_bad_frame_payload_returns_error_message(self):
        settings.LIVE_CAMERA_ENABLED = True
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
            # Send invalid base64
            ws.send_json({"type": "frame", "seq": 1, "jpeg_b64": "not_a_valid_b64!!!"})
            res = ws.receive_json()
            assert res["type"] == "error"
            assert res["code"] == "bad_frame"

            # Connection must remain alive and responsive
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}

    def test_ls8_pixel_dimension_bomb_closes_with_4413(self):
        settings.LIVE_CAMERA_ENABLED = True
        settings.LIVE_MAX_DIM = 640
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        huge_jpeg = _make_jpeg_b64(width=800, height=600)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
                ws.send_json({"type": "frame", "seq": 1, "jpeg_b64": huge_jpeg})
                ws.receive_json()
        assert exc_info.value.code == 4413

    def test_ls7_oversized_payload_bytes_closes_with_4413(self):
        settings.LIVE_CAMERA_ENABLED = True
        settings.LIVE_MAX_FRAME_BYTES = 500  # Strict 500 bytes cap
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        jpeg_b64 = _make_jpeg_b64(width=320, height=240)  # > 500 bytes

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
                ws.send_json({"type": "frame", "seq": 1, "jpeg_b64": jpeg_b64})
                ws.receive_json()
        assert exc_info.value.code == 4413

    def test_ls10_rate_limiting_sends_skipped(self):
        settings.LIVE_CAMERA_ENABLED = True
        settings.LIVE_MAX_FPS = 5
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        jpeg_b64 = _make_jpeg_b64(width=160, height=120)

        with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
            # 1st frame
            ws.send_json({"type": "frame", "seq": 1, "jpeg_b64": jpeg_b64})
            res1 = ws.receive_json()
            assert res1["type"] == "live_result"
            assert res1["seq"] == 1

            # 2nd frame sent immediately without delay
            ws.send_json({"type": "frame", "seq": 2, "jpeg_b64": jpeg_b64})
            res2 = ws.receive_json()
            assert res2["type"] == "skipped"
            assert res2["seq"] == 2
            assert res2["reason"] == "rate_limit"
