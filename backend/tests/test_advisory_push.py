"""Automated Test Suite for Class Fatigue Advisory and Push Notifications.

Implements README_MOBILE_ALERT_NOTIFICATIONS.md §11.1 & §11.3:
- L1-L4: Level logic and boundary mappings.
- L5: Status hysteresis prevents jitter on momentary spikes.
- L6: Level persistence triggers exactly one push notification.
- L7: Cooldown suppresses repeat push notifications.
- S1: Push payload is class-level only (no student names or PII).
- S2: /devices/push-token requires authentication (401).
- S6: Invalid push token formats rejected (422).
- S3/S5: User token ownership and logout deactivation.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.advisory.engine import (
    ADVISORY_LEVELS,
    ClassFatigueAdvisoryEngine,
    compute_advisory_level,
)
from app.auth.jwt import create_access_token
from app.config import settings
from app.db.database import SessionLocal, create_tables
from app.db.models import PushToken, User
from app.main import app
from app.notifications.expo_push import build_push_payload

client = TestClient(app)


# --------------------------------------------------------------------------
# 11.1 Level Logic Tests
# --------------------------------------------------------------------------

@pytest.mark.parametrize("pct,expected_level", [
    (0.0, 1),
    (10.0, 1),
    (24.9, 1),
    (25.0, 2),
    (40.0, 2),
    (49.9, 2),
    (50.0, 3),
    (60.0, 3),
    (74.9, 3),
    (75.0, 4),
    (90.0, 4),
    (100.0, 4),
])
def test_advisory_level_boundaries(pct: float, expected_level: int):
    """L1-L4: Assert level assignment across canonical thresholds."""
    assert compute_advisory_level(pct, (25.0, 50.0, 75.0)) == expected_level


def test_hysteresis_prevents_spike_jitter():
    """L5: Momentary 1-second spike does not change confirmed advisory level."""
    engine = ClassFatigueAdvisoryEngine(
        bands=(25.0, 50.0, 75.0),
        min_tracks=2,
        hysteresis_s=3.0,
        persist_s=10.0,
    )

    t0 = 1000.0
    # Normal attentive tracks (fatigue_index ~ 0.1) -> 10%
    tracks_normal = [
        {"fatigue_status": "Normal", "fatigue_index": 0.10},
        {"fatigue_status": "Normal", "fatigue_index": 0.10},
    ]
    adv, push = engine.process_class_tracks(session_id=99, tracks=tracks_normal, timestamp=t0)
    assert adv is not None
    assert adv["level"] == 1

    # Sudden 1-second spike to 80% (level 4)
    tracks_spike = [
        {"fatigue_status": "Fatigued", "fatigue_index": 0.80},
        {"fatigue_status": "Fatigued", "fatigue_index": 0.80},
    ]
    adv_spike, _ = engine.process_class_tracks(session_id=99, tracks=tracks_spike, timestamp=t0 + 1.0)
    # Hysteresis requires 3s: level remains 1
    assert adv_spike["level"] == 1

    # Return to normal
    adv_return, _ = engine.process_class_tracks(session_id=99, tracks=tracks_normal, timestamp=t0 + 2.0)
    assert adv_return["level"] == 1


def test_persistence_and_cooldown():
    """L6 & L7: Exactly one push after persist_s, suppressed by cooldown."""
    engine = ClassFatigueAdvisoryEngine(
        bands=(25.0, 50.0, 75.0),
        min_tracks=2,
        hysteresis_s=2.0,
        persist_s=5.0,
        cooldown_s=60.0,
    )

    t0 = 100.0
    tracks_tired = [
        {"fatigue_status": "Fatigued", "fatigue_index": 0.80},
        {"fatigue_status": "Fatigued", "fatigue_index": 0.80},
    ]

    # Establish candidate level 4
    engine.process_class_tracks(session_id=1, tracks=tracks_tired, timestamp=t0)
    # 2s later: confirmed level 4
    adv, push = engine.process_class_tracks(session_id=1, tracks=tracks_tired, timestamp=t0 + 2.5)
    assert adv["level"] == 4
    assert push is None  # Not held for persist_s (5s) yet

    # 5.5s after confirmation: push should trigger
    adv2, push2 = engine.process_class_tracks(session_id=1, tracks=tracks_tired, timestamp=t0 + 8.5)
    assert push2 is not None
    assert push2["data"]["level"] == 4
    assert "Consider continuing the class tomorrow" in push2["body"]

    # Inside cooldown (10s later): no second push
    adv3, push3 = engine.process_class_tracks(session_id=1, tracks=tracks_tired, timestamp=t0 + 18.5)
    assert push3 is None


# --------------------------------------------------------------------------
# 11.3 Security and Privacy Tests
# --------------------------------------------------------------------------

def test_s1_push_payload_no_pii():
    """S1: Push payload contains class-level text only (no student PII)."""
    adv_data = {
        "session_id": 10,
        "class_name": "Room 101",
        "level": 3,
        "code": "SHORT_BREAK",
        "message": ADVISORY_LEVELS[3]["message"],
        "since": "2026-10-05T10:00:00Z",
    }
    payload = build_push_payload("ExponentPushToken[mock_token_123]", adv_data)

    assert payload["to"] == "ExponentPushToken[mock_token_123]"
    assert payload["channelId"] == "fatigue-l3-v1"
    assert payload["interruptionLevel"] == "time-sensitive"
    assert payload["sound"] == "alert_high.wav"
    assert "Room 101" in payload["title"]
    assert "short break" in payload["body"]

    # Verify no student identifiers exist in payload
    str_dump = str(payload).lower()
    for forbidden in ["student", "track_id", "s00", "face", "image", "bbox"]:
        assert forbidden not in str_dump


def test_s2_push_token_unauthenticated():
    """S2: POST /devices/push-token without auth returns 401."""
    res = client.post("/devices/push-token", json={"token": "ExponentPushToken[test]", "platform": "android"})
    assert res.status_code == 401


def test_s6_invalid_token_format():
    """S6: Invalid push token format rejected with 422."""
    token = create_access_token("teacher", "teacher")
    res = client.post(
        "/devices/push-token",
        headers={"Authorization": f"Bearer {token}"},
        json={"token": "invalid_raw_token", "platform": "android"},
    )
    assert res.status_code == 422


def test_push_token_lifecycle():
    """S3/S5: Register and deactivate push token on user logout."""
    create_tables()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username="teacher").first()
        if not user:
            user = User(username="teacher_test", password_hash="dummy", role="teacher", active=True)
            db.add(user)
            db.commit()
            db.refresh(user)

        auth_token = create_access_token(user.username, user.role)
        valid_expo_token = "ExponentPushToken[abc1234567890xyz]"

        # 1. Register token
        reg_res = client.post(
            "/devices/push-token",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"token": valid_expo_token, "platform": "android"},
        )
        assert reg_res.status_code == 200
        assert reg_res.json()["ok"] is True

        tok_in_db = db.query(PushToken).filter_by(token=valid_expo_token).first()
        assert tok_in_db is not None
        assert tok_in_db.active is True
        assert tok_in_db.user_id == user.id

        # 2. Deactivate token (Logout)
        del_res = client.request(
            "DELETE",
            "/devices/push-token",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"token": valid_expo_token},
        )
        assert del_res.status_code == 200
        db.refresh(tok_in_db)
        assert tok_in_db.active is False

    finally:
        db.close()
