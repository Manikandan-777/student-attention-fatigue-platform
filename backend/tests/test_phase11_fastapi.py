"""Phase 11 Test Suite — FastAPI Core & WebSocket Infrastructure.

Spec refs: SYS-10, APP-24, APP-27, CON §4, README_EXECUTION.md Phase 11.
Pass conditions:
- Server boots and exposes /health with status: ok and privacy_mode: true.
- Telemetry WebSocket handles ping -> pong and session subscriptions.
- Concurrent WebSockets are handled simultaneously with broadcast fan-out.
- /ws/video is strictly rejected with close code 4403 when PRIVACY_MODE is true.
- /ws/video is accepted and operable when PRIVACY_MODE is temporarily disabled.
"""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.main import app
from app.ws.manager import ws_manager


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient):
    """Verify /health liveness probe response schema and default privacy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["app"] == "Student Attention & Fatigue Detection API"
    assert data["version"] == "1.0.0"
    assert data["privacy_mode"] is True
    assert "timestamp" in data


def test_telemetry_websocket_ping_pong(client: TestClient):
    """Verify /ws/telemetry heartbeat protocol."""
    with client.websocket_connect("/ws/telemetry") as ws:
        # Send ping
        ws.send_json({"type": "ping"})
        response = ws.receive_json()
        assert response == {"type": "pong"}


def test_telemetry_websocket_subscription(client: TestClient):
    """Verify /ws/telemetry session subscription handling."""
    with client.websocket_connect("/ws/telemetry") as ws:
        # Subscribe to session 42
        ws.send_json({"type": "subscribe", "session_id": 42})
        response = ws.receive_json()

        assert response["type"] == "subscribed"
        assert response["session_id"] == 42
        assert response["status"] == "ok"


def test_telemetry_concurrent_clients_and_broadcast(client: TestClient):
    """Verify multiple concurrent clients receive broadcasted telemetry."""
    import asyncio

    with client.websocket_connect("/ws/telemetry") as ws1, \
         client.websocket_connect("/ws/telemetry") as ws2:

        # Both connect and subscribe to session 10
        ws1.send_json({"type": "subscribe", "session_id": 10})
        _ = ws1.receive_json()

        ws2.send_json({"type": "subscribe", "session_id": 10})
        _ = ws2.receive_json()

        # Simulate backend pipeline broadcasting telemetry for session 10
        test_payload = {
            "type": "telemetry",
            "session_id": 10,
            "ts": "2026-10-01T12:00:00Z",
            "snapshot": {
                "session_id": 10,
                "students_detected": 2,
                "avg_attention_score": 88.5,
            },
            "tracks": [],
        }

        # Run broadcast via event loop
        asyncio.run(ws_manager.broadcast_telemetry(test_payload, session_id=10))

        # Both clients must receive the broadcast payload
        msg1 = ws1.receive_json()
        msg2 = ws2.receive_json()

        assert msg1["session_id"] == 10
        assert msg1["snapshot"]["avg_attention_score"] == 88.5
        assert msg2["session_id"] == 10
        assert msg2["snapshot"]["avg_attention_score"] == 88.5


def test_video_websocket_refused_code_4403_in_privacy_mode(client: TestClient):
    """CRITICAL PRIVACY TEST: /ws/video must be rejected with close code 4403 when PRIVACY_MODE=true."""
    settings.PRIVACY_MODE = True

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/video"):
            pass

    assert exc_info.value.code == 4403, (
        f"Expected close code 4403 for privacy rejection, got {exc_info.value.code}"
    )


def test_video_websocket_accepted_when_privacy_mode_false(client: TestClient):
    """Verify that when PRIVACY_MODE is explicitly disabled, /ws/video connects successfully."""
    settings.PRIVACY_MODE = False
    try:
        with client.websocket_connect("/ws/video") as ws:
            ws.send_json({"type": "ping"})
            resp = ws.receive_json()
            assert resp == {"type": "pong"}
    finally:
        # Restore non-negotiable default
        settings.PRIVACY_MODE = True
