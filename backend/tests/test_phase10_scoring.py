"""Phase 10 Test Suite — Composite Scoring & Validation State Machine.

Spec refs: SYS-8, SYS-9, APP-8, CON §2.1, §5, §6, README_EXECUTION.md Phase 10.
Pass conditions:
- Baseline produces Attentive / Normal with high attention score and low fatigue index.
- A single closed-eye frame NEVER changes displayed status or creates an alert.
- Sustained eye closure (> 45s) triggers a 'fatigue' alert with non-diagnostic copy.
- Sustained look-away (> 30s) triggers a 'distraction' alert with non-diagnostic copy.
- Landmark confidence < MIN_CONFIDENCE immediately yields 'Unknown' status and suppresses alerts.
- Alert cooldown (300s) suppresses duplicate alerts within cooldown window.
- Recovery clears status back to Normal / Attentive after hysteresis.
- 50/50 LSTM blend works when model_mode == 'lstm'.
- TrackResult dictionary strictly conforms to contracts.md §2.1.
"""

import pytest

from ai.scoring import (
    DEFAULT_ALERT_COOLDOWN_S,
    DEFAULT_DISTRACTION_PERSIST_S,
    DEFAULT_FATIGUE_PERSIST_S,
    DEFAULT_STATUS_HYSTERESIS_S,
    AlertEvent,
    AlertState,
    ScoringEngine,
)

DUMMY_NEUTRAL_EMOTIONS = {
    "Angry": 0.01,
    "Disgust": 0.0,
    "Fear": 0.01,
    "Happy": 0.10,
    "Sad": 0.03,
    "Surprise": 0.02,
    "Neutral": 0.83,
}

DUMMY_NEG_EMOTIONS = {
    "Angry": 0.20,
    "Disgust": 0.10,
    "Fear": 0.20,
    "Happy": 0.0,
    "Sad": 0.40,
    "Surprise": 0.0,
    "Neutral": 0.10,
}


def test_baseline_scenario():
    """Verify standard attentive student scenario."""
    engine = ScoringEngine()

    result, alerts = engine.process_frame(
        track_id=1,
        label="S001",
        bbox=[0.2, 0.2, 0.3, 0.3],
        landmark_confidence=0.98,
        ear=0.28,
        mar=0.15,
        head_yaw=1.5,
        head_pitch=-1.0,
        perclos=0.02,
        yawn_fraction=0.0,
        off_task_fraction=0.0,
        p_drowsy=0.05,
        drowsiness_label="Non Drowsy",
        emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
        top_emotion="Neutral",
        timestamp=1.0,
    )

    assert result["attention_status"] == "Attentive"
    assert result["fatigue_status"] == "Normal"
    assert result["attention_score"] >= 85.0
    assert result["fatigue_index"] <= 0.15
    assert result["confidence"] >= 0.90
    assert len(alerts) == 0


def test_single_closed_eye_frame_never_flips_status_or_alerts():
    """Verify that a transient blink / single closed-eye frame never flips status or alerts."""
    engine = ScoringEngine()

    # Step 1: 10 baseline frames (t = 0.0 to 1.0s)
    for i in range(10):
        t = i * 0.1
        result, alerts = engine.process_frame(
            track_id=2,
            label="S002",
            bbox=[0.1, 0.1, 0.2, 0.2],
            landmark_confidence=0.95,
            ear=0.28,
            mar=0.15,
            head_yaw=0.0,
            head_pitch=0.0,
            perclos=0.0,
            yawn_fraction=0.0,
            off_task_fraction=0.0,
            p_drowsy=0.05,
            drowsiness_label="Non Drowsy",
            emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
            top_emotion="Neutral",
            timestamp=t,
        )
        assert result["attention_status"] == "Attentive"
        assert result["fatigue_status"] == "Normal"
        assert len(alerts) == 0

    # Step 2: Inject exactly ONE closed-eye frame (t = 1.1s)
    result_anomaly, alerts_anomaly = engine.process_frame(
        track_id=2,
        label="S002",
        bbox=[0.1, 0.1, 0.2, 0.2],
        landmark_confidence=0.95,
        ear=0.02,                   # Eyes fully closed
        mar=0.15,
        head_yaw=0.0,
        head_pitch=0.0,
        perclos=1.0 / 30.0,         # 1 closed frame in window
        yawn_fraction=0.0,
        off_task_fraction=0.0,
        p_drowsy=1.0,               # Model flags drowsy
        drowsiness_label="Drowsy",
        emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
        top_emotion="Neutral",
        timestamp=1.1,
    )

    # CRITICAL SPEC CHECK: A single closed frame must NEVER change displayed status or emit alerts!
    assert result_anomaly["fatigue_status"] == "Normal", (
        f"Single closed frame improperly changed status to {result_anomaly['fatigue_status']}"
    )
    assert result_anomaly["attention_status"] == "Attentive"
    assert len(alerts_anomaly) == 0

    # Step 3: Return to baseline (t = 1.2s to 3.0s)
    for i in range(12, 30):
        t = i * 0.1
        result, alerts = engine.process_frame(
            track_id=2,
            label="S002",
            bbox=[0.1, 0.1, 0.2, 0.2],
            landmark_confidence=0.95,
            ear=0.28,
            mar=0.15,
            head_yaw=0.0,
            head_pitch=0.0,
            perclos=0.0,
            yawn_fraction=0.0,
            off_task_fraction=0.0,
            p_drowsy=0.05,
            drowsiness_label="Non Drowsy",
            emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
            top_emotion="Neutral",
            timestamp=t,
        )
        assert result["attention_status"] == "Attentive"
        assert result["fatigue_status"] == "Normal"
        assert len(alerts) == 0


def test_sustained_eye_closure_triggers_fatigue_alert():
    """Verify sustained eye closure (> 45s) transitions status and triggers a fatigue alert."""
    engine = ScoringEngine()

    all_emitted_alerts = []
    statuses = []

    # Run for 55 simulated seconds at 1.0s steps
    for step in range(55):
        t = float(step)
        res, alerts = engine.process_frame(
            track_id=3,
            label="S003",
            bbox=[0.2, 0.2, 0.3, 0.3],
            landmark_confidence=0.96,
            ear=0.05,
            mar=0.20,
            head_yaw=-5.0,
            head_pitch=-10.0,
            perclos=0.90,
            yawn_fraction=0.20,
            off_task_fraction=0.10,
            p_drowsy=0.95,
            drowsiness_label="Drowsy",
            emotion_probs=DUMMY_NEG_EMOTIONS,
            top_emotion="Sad",
            timestamp=t,
        )
        statuses.append((t, res["fatigue_status"]))
        all_emitted_alerts.extend(alerts)

    # 1. Status flips to 'Fatigued' after status hysteresis (3s)
    # At t=0s status is Normal (candidate set). At t >= 3s, status becomes Fatigued.
    status_at_5s = next(s for t, s in statuses if t == 5.0)
    assert status_at_5s == "Fatigued"

    # 2. Alert emitted when persist window (45s) is reached
    assert len(all_emitted_alerts) == 1, f"Expected 1 alert, got {len(all_emitted_alerts)}"
    alert = all_emitted_alerts[0]

    assert alert.track_id == 3
    assert alert.label == "S003"
    assert alert.type == "fatigue"
    assert alert.status == "New"
    # D8 Copy verification: informational indicator, non-diagnostic
    assert "Repeated fatigue-related indicators" in alert.message
    assert alert.timestamp == 45.0  # Emitted exactly at persist window


def test_sustained_look_away_triggers_distraction_alert():
    """Verify sustained head turn (> 30s) triggers distraction status and alert."""
    engine = ScoringEngine()

    all_emitted_alerts = []
    statuses = []

    for step in range(40):
        t = float(step)
        res, alerts = engine.process_frame(
            track_id=4,
            label="S004",
            bbox=[0.3, 0.3, 0.2, 0.2],
            landmark_confidence=0.94,
            ear=0.25,
            mar=0.15,
            head_yaw=45.0,  # Looking far away
            head_pitch=0.0,
            perclos=0.05,
            yawn_fraction=0.0,
            off_task_fraction=1.0,  # Entire window looking away
            p_drowsy=0.10,
            drowsiness_label="Non Drowsy",
            emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
            top_emotion="Neutral",
            timestamp=t,
        )
        statuses.append((t, res["attention_status"]))
        all_emitted_alerts.extend(alerts)

    # 1. Attention status flips to 'Distracted' after hysteresis (3s)
    status_at_5s = next(s for t, s in statuses if t == 5.0)
    assert status_at_5s == "Distracted"

    # 2. Alert emitted at persist window (30s)
    assert len(all_emitted_alerts) == 1
    alert = all_emitted_alerts[0]
    assert alert.type == "distraction"
    assert "Repeated distraction-related indicators" in alert.message
    assert alert.timestamp == 30.0


def test_low_confidence_frames_yield_unknown_and_prevent_alerts():
    """Verify that landmark confidence below MIN_CONFIDENCE (0.80) yields 'Unknown' and suppresses alerts."""
    engine = ScoringEngine(min_confidence=0.80)

    for step in range(50):
        t = float(step)
        res, alerts = engine.process_frame(
            track_id=5,
            label="S005",
            bbox=[0.1, 0.1, 0.2, 0.2],
            landmark_confidence=0.60,  # Below MIN_CONFIDENCE (0.80)
            ear=0.01,                  # Severe closure
            mar=0.60,
            head_yaw=50.0,
            head_pitch=50.0,
            perclos=1.0,
            yawn_fraction=1.0,
            off_task_fraction=1.0,
            p_drowsy=1.0,
            drowsiness_label="Drowsy",
            emotion_probs=DUMMY_NEG_EMOTIONS,
            top_emotion="Sad",
            timestamp=t,
        )

        # Must report Unknown
        assert res["attention_status"] == "Unknown"
        assert res["fatigue_status"] == "Unknown"
        # Must NEVER emit an alert on low-confidence data
        assert len(alerts) == 0


def test_cooldown_and_recovery():
    """Verify alert cooldown suppresses rapid re-alerting and recovery clears status."""
    engine = ScoringEngine()

    # Step 1: Trigger fatigue alert at t = 45s
    for step in range(46):
        t = float(step)
        engine.process_frame(
            track_id=6,
            label="S006",
            bbox=[0.2, 0.2, 0.2, 0.2],
            landmark_confidence=0.95,
            ear=0.05,
            mar=0.10,
            head_yaw=0.0,
            head_pitch=0.0,
            perclos=0.90,
            yawn_fraction=0.0,
            off_task_fraction=0.0,
            p_drowsy=0.95,
            drowsiness_label="Drowsy",
            emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
            top_emotion="Neutral",
            timestamp=t,
        )

    # Step 2: Student recovers (t = 46s to 60s)
    for step in range(46, 61):
        t = float(step)
        res, alerts = engine.process_frame(
            track_id=6,
            label="S006",
            bbox=[0.2, 0.2, 0.2, 0.2],
            landmark_confidence=0.95,
            ear=0.28,
            mar=0.15,
            head_yaw=0.0,
            head_pitch=0.0,
            perclos=0.0,
            yawn_fraction=0.0,
            off_task_fraction=0.0,
            p_drowsy=0.05,
            drowsiness_label="Non Drowsy",
            emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
            top_emotion="Neutral",
            timestamp=t,
        )
        assert len(alerts) == 0

    # At t=60s, student has recovered for 14s (> 3s hysteresis), so status must be Normal
    assert res["fatigue_status"] == "Normal"

    # Step 3: Fatigue recurs at t = 70s to 120s (within 300s cooldown)
    reoccur_alerts = []
    for step in range(70, 125):
        t = float(step)
        res, alerts = engine.process_frame(
            track_id=6,
            label="S006",
            bbox=[0.2, 0.2, 0.2, 0.2],
            landmark_confidence=0.95,
            ear=0.05,
            mar=0.10,
            head_yaw=0.0,
            head_pitch=0.0,
            perclos=0.90,
            yawn_fraction=0.0,
            off_task_fraction=0.0,
            p_drowsy=0.95,
            drowsiness_label="Drowsy",
            emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
            top_emotion="Neutral",
            timestamp=t,
        )
        reoccur_alerts.extend(alerts)

    # Cooldown (300s) must prevent duplicate alert during this period
    assert len(reoccur_alerts) == 0


def test_lstm_blend_mode():
    """Verify 50/50 blending when model_mode == 'lstm'."""
    engine = ScoringEngine()

    res_heuristic, _ = engine.process_frame(
        track_id=7,
        label="S007",
        bbox=[0.2, 0.2, 0.2, 0.2],
        landmark_confidence=0.95,
        ear=0.28,
        mar=0.15,
        head_yaw=0.0,
        head_pitch=0.0,
        perclos=0.0,
        yawn_fraction=0.0,
        off_task_fraction=0.0,
        p_drowsy=0.10,
        drowsiness_label="Non Drowsy",
        emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
        top_emotion="Neutral",
        timestamp=1.0,
        model_mode="heuristic",
    )

    # Heuristic raw fatigue: 0.45 * 0.10 = 0.045
    # Blend with LSTM: 0.5 * 0.045 + 0.5 * 0.80 = 0.0225 + 0.40 = 0.4225
    engine_lstm = ScoringEngine()
    res_lstm, _ = engine_lstm.process_frame(
        track_id=8,
        label="S008",
        bbox=[0.2, 0.2, 0.2, 0.2],
        landmark_confidence=0.95,
        ear=0.28,
        mar=0.15,
        head_yaw=0.0,
        head_pitch=0.0,
        perclos=0.0,
        yawn_fraction=0.0,
        off_task_fraction=0.0,
        p_drowsy=0.10,
        drowsiness_label="Non Drowsy",
        emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
        top_emotion="Neutral",
        timestamp=1.0,
        model_mode="lstm",
        lstm_fatigue_index=0.80,
        lstm_attention_score=40.0,
    )

    assert res_lstm["model_mode"] == "lstm"
    assert res_lstm["fatigue_index"] > res_heuristic["fatigue_index"]
    assert res_lstm["fatigue_index"] == pytest.approx(0.42, abs=0.02)


def test_contracts_schema_compliance():
    """Verify that TrackResult dictionary satisfies contracts.md §2.1 exactly."""
    engine = ScoringEngine()

    result, _ = engine.process_frame(
        track_id=9,
        label="S009",
        bbox=[0.12, 0.15, 0.35, 0.40],
        landmark_confidence=0.97,
        ear=0.27,
        mar=0.31,
        head_yaw=-4.2,
        head_pitch=6.1,
        perclos=0.08,
        yawn_fraction=0.0,
        off_task_fraction=0.0,
        p_drowsy=0.12,
        drowsiness_label="Non Drowsy",
        emotion_probs=DUMMY_NEUTRAL_EMOTIONS,
        top_emotion="Neutral",
        timestamp=1.0,
    )

    # Check all keys in contracts.md §2.1
    expected_keys = {
        "track_id", "label", "bbox", "bbox_normalized", "landmark_confidence",
        "features", "drowsiness", "emotion", "attention_score", "fatigue_index",
        "attention_status", "fatigue_status", "confidence", "model_mode",
    }
    assert set(result.keys()) == expected_keys

    # Check nested structures
    assert set(result["features"].keys()) == {"ear", "mar", "perclos", "head_yaw", "head_pitch"}
    assert set(result["drowsiness"].keys()) == {"label", "p_drowsy"}
    assert set(result["emotion"].keys()) == {"top", "probs"}
    assert len(result["emotion"]["probs"]) == 7

    # Check bounds
    assert 0.0 <= result["attention_score"] <= 100.0
    assert 0.0 <= result["fatigue_index"] <= 1.0
    assert result["bbox_normalized"] is True
