"""Tests for Live Camera 1,000-Face Detection & Fatigue Prediction Engine."""

import pytest
from starlette.testclient import TestClient

from app.camera.service import live_camera_service
from app.config import settings
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_camera_service_1000_faces_detection_and_fatigue_prediction():
    """Verify live camera detects 1,000 faces and accurately predicts fatigue."""
    # Start in 1,000 faces mode
    status_data = live_camera_service.start(mode="1000_faces")
    assert status_data["is_running"] is True
    assert status_data["mode"] == "1000_faces"

    # Wait briefly for worker loop to process first frame
    import time
    for _ in range(30):
        if live_camera_service.total_processed_frames >= 1:
            break
        time.sleep(0.1)

    status = live_camera_service.get_status()
    assert status["is_running"] is True
    assert status["students_detected"] == 1000

    # Verify fatigue predictions are populated correctly
    counts = status["counts"]
    assert counts["attentive"] > 700, f"Expected >700 attentive students, got {counts['attentive']}"
    assert counts["fatigued"] > 50, f"Expected >50 fatigued students, got {counts['fatigued']}"
    assert counts["distracted"] > 20, f"Expected >20 distracted students, got {counts['distracted']}"
    assert 60.0 <= status["average_attention_score"] <= 95.0

    # Verify encoded JPEG frame is generated
    jpeg = live_camera_service.get_latest_jpeg()
    assert jpeg is not None
    assert len(jpeg) > 1000
    assert jpeg[:2] == b"\xff\xd8"  # Valid JPEG SOI marker

    # Stop service
    stop_data = live_camera_service.stop()
    assert stop_data["is_running"] is False


def test_camera_api_endpoints(client: TestClient):
    """Verify camera REST endpoints (/camera/start, /camera/status, /camera/stop, /camera/toggle-privacy)."""
    # 1. Start camera via API
    res_start = client.post("/camera/start", json={"mode": "1000_faces"})
    assert res_start.status_code == 200
    data_start = res_start.json()
    assert data_start["status"] == "started"

    # 2. Query status
    res_status = client.get("/camera/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["mode"] == "1000_faces"

    # 3. Toggle privacy mode
    initial_privacy = settings.PRIVACY_MODE
    res_priv = client.post("/camera/toggle-privacy")
    assert res_priv.status_code == 200
    assert res_priv.json()["privacy_mode"] != initial_privacy

    # Restore privacy mode
    client.post("/camera/toggle-privacy")

    # 4. Stop camera
    res_stop = client.post("/camera/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "stopped"
