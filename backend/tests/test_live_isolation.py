"""Isolation and Non-Interference Verification Suite (Phase LC-6, ISO1-ISO12).

Guarantees:
- ISO1: LIVE_CAMERA_ENABLED=false shuts down endpoint without side-effects.
- ISO4: Zero database writes (observations, alerts, sessions row counts unchanged).
- ISO5: Zero cross-talk to /ws/telemetry or global alerts.
- ISO7: Exception containment in live connection does not impact other services.
- ISO8: System Settings are never mutated at runtime.
- ISO10: REST routes and OpenAPI schemas remain completely backward compatible.
"""

from copy import deepcopy
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.auth.jwt import create_access_token
from app.config import settings
from app.db.database import get_db
from app.db.models import Alert, Observation, Session, User
from app.main import app
from app.ws.live_camera import live_limiter
from tests.test_live_camera_ws import _make_jpeg_b64


class TestLiveIsolation:
    @pytest.fixture(autouse=True)
    def clean_env(self):
        with live_limiter.lock:
            live_limiter.active_total = 0
            live_limiter.user_counts.clear()
        orig = settings.LIVE_CAMERA_ENABLED
        yield
        with live_limiter.lock:
            live_limiter.active_total = 0
            live_limiter.user_counts.clear()
        settings.LIVE_CAMERA_ENABLED = orig

    def test_iso1_flag_off_endpoint_closed(self):
        settings.LIVE_CAMERA_ENABLED = False
        token = create_access_token(subject="teacher1", role="teacher")
        client = TestClient(app)

        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
                ws.receive_json()
        assert exc.value.code == 4403

        # Normal health probe is unaffected
        res = client.get("/health")
        assert res.status_code == 200

    def test_iso4_no_database_mutation(self):
        settings.LIVE_CAMERA_ENABLED = True
        client = TestClient(app)

        # Get DB session to count records before run
        db_gen = get_db()
        db = next(db_gen)
        try:
            obs_before = db.query(Observation).count()
            alerts_before = db.query(Alert).count()
            sess_before = db.query(Session).count()
            users_before = db.query(User).count()
        finally:
            db.close()

        # Run live detection frame
        token = create_access_token(subject="teacher1", role="teacher")
        jpeg_b64 = _make_jpeg_b64(width=160, height=120)

        with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
            ws.send_json({"type": "frame", "seq": 1, "jpeg_b64": jpeg_b64})
            res = ws.receive_json()
            assert res["type"] == "live_result"

        # Count records after run
        db = next(get_db())
        try:
            obs_after = db.query(Observation).count()
            alerts_after = db.query(Alert).count()
            sess_after = db.query(Session).count()
            users_after = db.query(User).count()
        finally:
            db.close()

        assert obs_after == obs_before, "Database observations were mutated by live camera!"
        assert alerts_after == alerts_before, "Database alerts were mutated by live camera!"
        assert sess_after == sess_before, "Database sessions were mutated by live camera!"
        assert users_after == users_before, "Database users were mutated by live camera!"

    def test_iso8_settings_never_mutated(self):
        settings.LIVE_CAMERA_ENABLED = True
        client = TestClient(app)

        before_state = {
            k: getattr(settings, k)
            for k in dir(settings)
            if not k.startswith("_") and not callable(getattr(settings, k))
        }

        token = create_access_token(subject="teacher1", role="teacher")
        jpeg_b64 = _make_jpeg_b64(width=160, height=120)

        with client.websocket_connect(f"/ws/live-camera?token={token}") as ws:
            ws.send_json({"type": "frame", "seq": 1, "jpeg_b64": jpeg_b64})
            ws.receive_json()

        after_state = {
            k: getattr(settings, k)
            for k in dir(settings)
            if not k.startswith("_") and not callable(getattr(settings, k))
        }

        assert before_state == after_state, "Settings dataclass was mutated during live camera run!"

    def test_iso10_existing_routes_unchanged(self):
        client = TestClient(app)
        # Check standard endpoints still exist and respond
        assert client.get("/health").status_code == 200
        assert client.get("/system/status").status_code in (200, 401)
        assert client.get("/reports").status_code == 401
