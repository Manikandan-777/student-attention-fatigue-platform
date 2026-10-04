"""Unit and Integration Tests for Class Fatigue Advisory Alerts.

Tests the 11 scenarios from docs/README_MOBILE_FATIGUE_ALERTS.md:
1. Score <25% -> Level 1 (CONTINUE)
2. Score 25%..<50% -> Level 2 (INTERACTIVE)
3. Score 50%..<75% -> Level 3 (SHORT_BREAK)
4. Score >=75% -> Level 4 (RESCHEDULE)
5. Hysteresis: Sudden spike for 1s does not change confirmed level (D7)
6. Push notification persistence and cooldown
7. Fewer than 5 usable tracks yields null advisory ("Not enough data")
8. Tracks with fatigue_status='Unknown' are excluded from the average
11. Non-diagnostic phrasing check (Decision D8)
"""

import time
import pytest
from app.advisory.engine import (
    ADVISORY_LEVELS,
    ClassFatigueAdvisoryEngine,
    compute_advisory_level,
)


def test_advisory_level_bands():
    """Scenarios 1-4: Band boundary mapping."""
    assert compute_advisory_level(0.0) == 1
    assert compute_advisory_level(10.0) == 1
    assert compute_advisory_level(24.9) == 1

    assert compute_advisory_level(25.0) == 2
    assert compute_advisory_level(40.0) == 2
    assert compute_advisory_level(49.9) == 2

    assert compute_advisory_level(50.0) == 3
    assert compute_advisory_level(62.4) == 3
    assert compute_advisory_level(74.9) == 3

    assert compute_advisory_level(75.0) == 4
    assert compute_advisory_level(90.0) == 4
    assert compute_advisory_level(100.0) == 4


def test_fewer_than_min_tracks_returns_none():
    """Scenario 7: Fewer than 5 usable tracks returns None."""
    engine = ClassFatigueAdvisoryEngine(min_tracks=5)
    tracks = [
        {"fatigue_status": "Normal", "fatigue_index": 0.10},
        {"fatigue_status": "Normal", "fatigue_index": 0.15},
        {"fatigue_status": "Fatigued", "fatigue_index": 0.85},
    ]  # only 3 tracks (< 5)

    advisory, push = engine.process_class_tracks(session_id=1, tracks=tracks)
    assert advisory is None
    assert push is None


def test_unknown_tracks_excluded():
    """Scenario 8: Unknown tracks are excluded from the class average."""
    engine = ClassFatigueAdvisoryEngine(min_tracks=5)
    # 5 usable normal tracks with fatigue_index=0.20, plus 10 Unknown tracks
    tracks = [
        {"fatigue_status": "Normal", "fatigue_index": 0.20} for _ in range(5)
    ] + [
        {"fatigue_status": "Unknown", "fatigue_index": 0.99} for _ in range(10)
    ]

    advisory, _ = engine.process_class_tracks(session_id=2, tracks=tracks)
    assert advisory is not None
    assert advisory["usable_tracks"] == 5
    # Since all 5 usable tracks are 0.20, raw percentage is 20.0% -> Level 1
    assert advisory["class_fatigue_pct"] == 20.0
    assert advisory["level"] == 1
    assert advisory["code"] == "CONTINUE"


def test_hysteresis_spike_does_not_change_level():
    """Scenario 5: Score jumps from 20% to 80% for 1s, then returns to 20% -> No level change (D7)."""
    engine = ClassFatigueAdvisoryEngine(
        min_tracks=5,
        hysteresis_s=3.0,
        alpha=1.0,  # disable EMA for direct step test
    )

    t0 = 1000.0
    normal_tracks = [{"fatigue_status": "Normal", "fatigue_index": 0.20} for _ in range(10)]
    spike_tracks = [{"fatigue_status": "Fatigued", "fatigue_index": 0.80} for _ in range(10)]

    # Initial state at t0
    adv, push = engine.process_class_tracks(session_id=3, tracks=normal_tracks, timestamp=t0)
    assert adv["level"] == 1

    # Sudden spike at t0 + 1s (held for only 1s < hysteresis 3s)
    adv_spike, push_spike = engine.process_class_tracks(session_id=3, tracks=spike_tracks, timestamp=t0 + 1.0)
    # Level must remain 1 because it has not held for 3s
    assert adv_spike["level"] == 1
    assert push_spike is None

    # Returns to normal at t0 + 2s
    adv_return, push_return = engine.process_class_tracks(session_id=3, tracks=normal_tracks, timestamp=t0 + 2.0)
    assert adv_return["level"] == 1
    assert push_return is None


def test_push_notification_persistence_and_cooldown():
    """Scenario 6: Push notification is sent only after holding for persist_s, with cooldown."""
    engine = ClassFatigueAdvisoryEngine(
        min_tracks=5,
        hysteresis_s=3.0,
        persist_s=60.0,
        cooldown_s=300.0,
        alpha=1.0,
    )

    fatigued_tracks = [{"fatigue_status": "Fatigued", "fatigue_index": 0.85} for _ in range(10)]

    t0 = 1000.0
    # Step 1: Initial detection at t0 (level 4)
    adv, push = engine.process_class_tracks(session_id=4, tracks=fatigued_tracks, timestamp=t0)
    assert push is None  # no push yet (0s < 60s)

    # Step 2: Hysteresis confirms level 4 at t0 + 4s
    adv, push = engine.process_class_tracks(session_id=4, tracks=fatigued_tracks, timestamp=t0 + 4.0)
    assert adv["level"] == 4
    assert push is None  # only 0s at level 4 (< 60s)

    # Step 3: After holding level 4 for 61s (at t0 + 65.0s)
    adv, push = engine.process_class_tracks(session_id=4, tracks=fatigued_tracks, timestamp=t0 + 65.0)
    assert push is not None
    assert push["data"]["level"] == 4
    assert push["data"]["code"] == "RESCHEDULE"

    # Step 4: Within cooldown (e.g. at t0 + 120s, which is < 300s cooldown)
    adv, push2 = engine.process_class_tracks(session_id=4, tracks=fatigued_tracks, timestamp=t0 + 120.0)
    assert push2 is None  # blocked by cooldown

    # Step 5: After cooldown expires (at t0 + 380s > 365s)
    adv, push3 = engine.process_class_tracks(session_id=4, tracks=fatigued_tracks, timestamp=t0 + 380.0)
    assert push3 is not None


def test_non_diagnostic_copy():
    """Scenario 11: Copy check (D8 non-diagnostic)."""
    forbidden_words = ["sick", "lazy", "sleeping", "diagnosed", "depressed", "ill", "disorder"]
    for level, data in ADVISORY_LEVELS.items():
        msg = data["message"].lower()
        for word in forbidden_words:
            assert word not in msg, f"Forbidden word '{word}' found in advisory level {level}"
