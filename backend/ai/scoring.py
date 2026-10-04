"""Composite Scoring & Validation State Machine.

Implements SYS-8, SYS-9, APP-8, CON §2.1, §5, §6:
- Heuristic scoring formula for Fatigue Index and Attention Score (configurable weights).
- Blended scoring with LSTM model when model_mode == "lstm" (CON §6).
- Exponential Moving Average (EMA, alpha=0.3) score smoothing to dampen transient fluctuations.
- Minimum confidence gating (MIN_CONFIDENCE=0.80) -> sets status to "Unknown".
- Status hysteresis (STATUS_HYSTERESIS_S=3.0s) to prevent single-frame status flips.
- Temporal validation state machine: Normal -> Candidate -> Confirmed -> Alerted -> Cleared.
- Alert generation with cooldown (ALERT_COOLDOWN_S=300s) and privacy/D8 compliant messages.
- Generation of canonical TrackResult (CON §2.1) dictionaries.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ai.scoring")

# Default contract thresholds & weights (contracts.md §5, §6)
DEFAULT_MIN_CONFIDENCE = 0.80
DEFAULT_EMA_ALPHA = 0.30
DEFAULT_STATUS_HYSTERESIS_S = 3.0
DEFAULT_FATIGUE_PERSIST_S = 45.0
DEFAULT_DISTRACTION_PERSIST_S = 30.0
DEFAULT_ALERT_COOLDOWN_S = 300.0

# Formula weights (contracts.md §6)
DEFAULT_W_P_DROWSY = 0.45
DEFAULT_W_PERCLOS = 0.35
DEFAULT_W_YAWN = 0.20

DEFAULT_W_OFF_TASK = 0.65
DEFAULT_W_FATIGUE_IN_DISTRACTION = 0.20
DEFAULT_W_NEG_AFFECT = 0.15

DEFAULT_FATIGUE_THRESHOLD = 0.55
DEFAULT_ATTENTION_THRESHOLD = 55.0  # attention_score <= 55 -> Distracted


class AlertState(str, Enum):
    NORMAL = "Normal"
    CANDIDATE = "Candidate"
    CONFIRMED = "Confirmed"
    ALERTED = "Alerted"
    CLEARED = "Cleared"


@dataclass
class AlertEvent:
    """Emitted alert event conforming to contracts.md §2.3."""
    track_id: int
    label: str
    type: str             # "fatigue" or "distraction"
    status: str           # "New"
    message: str
    confidence: float
    created_at: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "type": self.type,
            "status": self.status,
            "message": self.message,
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "timestamp": self.timestamp,
        }


@dataclass
class ConditionStateMachine:
    """Tracks state machine progression for a single condition (fatigue or distraction)."""
    condition_type: str
    persist_window_s: float
    state: AlertState = AlertState.NORMAL
    candidate_since: Optional[float] = None
    last_alert_time: Optional[float] = None
    false_since: Optional[float] = None

    def update(
        self,
        is_condition_active: bool,
        is_confident: bool,
        timestamp: float,
        cooldown_s: float = DEFAULT_ALERT_COOLDOWN_S,
        hysteresis_s: float = DEFAULT_STATUS_HYSTERESIS_S,
    ) -> Optional[str]:
        """Update state machine and return transition action if alert should trigger."""
        emit_alert = False

        # If confidence is below threshold, cannot be a valid candidate or alert
        if not is_confident:
            if self.state in (AlertState.CANDIDATE, AlertState.CONFIRMED):
                self.state = AlertState.NORMAL
                self.candidate_since = None
            return None

        in_cooldown = (
            self.last_alert_time is not None and
            (timestamp - self.last_alert_time) < cooldown_s
        )

        if is_condition_active:
            self.false_since = None

            if self.state == AlertState.NORMAL:
                if not in_cooldown:
                    self.state = AlertState.CANDIDATE
                    self.candidate_since = timestamp

            elif self.state == AlertState.CANDIDATE:
                if self.candidate_since is not None:
                    duration = timestamp - self.candidate_since
                    if duration >= self.persist_window_s:
                        self.state = AlertState.CONFIRMED
                        if not in_cooldown:
                            self.state = AlertState.ALERTED
                            self.last_alert_time = timestamp
                            emit_alert = True

            elif self.state == AlertState.ALERTED:
                # Still active, wait until condition clears or cooldown resets
                pass

        else:
            # Condition is inactive / resolved
            if self.false_since is None:
                self.false_since = timestamp

            # Must hold false for hysteresis window to clear
            if (timestamp - self.false_since) >= hysteresis_s:
                if self.state in (AlertState.CANDIDATE, AlertState.CONFIRMED, AlertState.ALERTED):
                    self.state = AlertState.NORMAL
                    self.candidate_since = None

        return self.condition_type if emit_alert else None


@dataclass
class TrackState:
    """Maintains smoothed scores, displayed statuses, and alert state machines for one track."""
    track_id: int
    label: str

    # EMA Smoothed metrics
    smoothed_fatigue_index: Optional[float] = None
    smoothed_attention_score: Optional[float] = None
    smoothed_confidence: Optional[float] = None

    # Hysteresis tracking for displayed status
    displayed_fatigue_status: str = "Normal"
    fatigue_candidate_status: str = "Normal"
    fatigue_status_changed_at: float = 0.0

    displayed_attention_status: str = "Attentive"
    attention_candidate_status: str = "Attentive"
    attention_status_changed_at: float = 0.0

    # Validation state machines
    fatigue_sm: ConditionStateMachine = field(
        default_factory=lambda: ConditionStateMachine("fatigue", DEFAULT_FATIGUE_PERSIST_S)
    )
    distraction_sm: ConditionStateMachine = field(
        default_factory=lambda: ConditionStateMachine("distraction", DEFAULT_DISTRACTION_PERSIST_S)
    )


class ScoringEngine:
    """Computes composite scores, runs validation state machines, and generates TrackResult objects."""

    def __init__(
        self,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        ema_alpha: float = DEFAULT_EMA_ALPHA,
        status_hysteresis_s: float = DEFAULT_STATUS_HYSTERESIS_S,
        fatigue_persist_s: float = DEFAULT_FATIGUE_PERSIST_S,
        distraction_persist_s: float = DEFAULT_DISTRACTION_PERSIST_S,
        alert_cooldown_s: float = DEFAULT_ALERT_COOLDOWN_S,
        fatigue_threshold: float = DEFAULT_FATIGUE_THRESHOLD,
        attention_threshold: float = DEFAULT_ATTENTION_THRESHOLD,
        w_p_drowsy: float = DEFAULT_W_P_DROWSY,
        w_perclos: float = DEFAULT_W_PERCLOS,
        w_yawn: float = DEFAULT_W_YAWN,
        w_off_task: float = DEFAULT_W_OFF_TASK,
        w_fatigue_in_distraction: float = DEFAULT_W_FATIGUE_IN_DISTRACTION,
        w_neg_affect: float = DEFAULT_W_NEG_AFFECT,
    ) -> None:
        self.min_confidence = min_confidence
        self.ema_alpha = ema_alpha
        self.status_hysteresis_s = status_hysteresis_s
        self.fatigue_persist_s = fatigue_persist_s
        self.distraction_persist_s = distraction_persist_s
        self.alert_cooldown_s = alert_cooldown_s

        self.fatigue_threshold = fatigue_threshold
        self.attention_threshold = attention_threshold

        self.w_p_drowsy = w_p_drowsy
        self.w_perclos = w_perclos
        self.w_yawn = w_yawn
        self.w_off_task = w_off_task
        self.w_fatigue_in_distraction = w_fatigue_in_distraction
        self.w_neg_affect = w_neg_affect

        self._track_states: Dict[int, TrackState] = {}

    def _get_or_create_state(self, track_id: int, label: str) -> TrackState:
        if track_id not in self._track_states:
            state = TrackState(track_id=track_id, label=label)
            state.fatigue_sm.persist_window_s = self.fatigue_persist_s
            state.distraction_sm.persist_window_s = self.distraction_persist_s
            self._track_states[track_id] = state
        return self._track_states[track_id]

    def compute_heuristic_scores(
        self,
        p_drowsy: float,
        perclos: float,
        yawn_fraction: float,
        off_task_fraction: float,
        neg_affect: float,
    ) -> Tuple[float, float]:
        """Compute raw heuristic fatigue_index [0, 1] and attention_score [0, 100]."""
        # 1. fatigue_index = 0.45*p_drowsy + 0.35*perclos + 0.20*yawn
        fatigue_index = (
            self.w_p_drowsy * p_drowsy +
            self.w_perclos * perclos +
            self.w_yawn * yawn_fraction
        )
        fatigue_index = float(max(0.0, min(1.0, fatigue_index)))

        # 2. distraction = 0.65*off_task + 0.20*fatigue_index + 0.15*neg_affect
        distraction = (
            self.w_off_task * off_task_fraction +
            self.w_fatigue_in_distraction * fatigue_index +
            self.w_neg_affect * neg_affect
        )
        distraction_clamped = float(max(0.0, min(1.0, distraction)))

        # 3. attention_score = 100 * (1 - clamp(distraction, 0, 1))
        attention_score = float(100.0 * (1.0 - distraction_clamped))

        return fatigue_index, attention_score

    def process_frame(
        self,
        track_id: int,
        label: str,
        bbox: List[float],
        landmark_confidence: float,
        ear: float,
        mar: float,
        head_yaw: float,
        head_pitch: float,
        perclos: float,
        yawn_fraction: float,
        off_task_fraction: float,
        p_drowsy: float,
        drowsiness_label: str,
        emotion_probs: Dict[str, float],
        top_emotion: str,
        timestamp: float,
        model_mode: str = "heuristic",
        lstm_fatigue_index: Optional[float] = None,
        lstm_attention_score: Optional[float] = None,
    ) -> Tuple[Dict[str, Any], List[AlertEvent]]:
        """Process a frame observation for one track and produce TrackResult and any Alerts."""
        state = self._get_or_create_state(track_id, label)

        # 1. Compute raw heuristic scores
        neg_affect = (
            emotion_probs.get("Sad", 0.0) +
            emotion_probs.get("Fear", 0.0) +
            emotion_probs.get("Angry", 0.0) +
            emotion_probs.get("Disgust", 0.0)
        )
        raw_fatigue, raw_attention = self.compute_heuristic_scores(
            p_drowsy=p_drowsy,
            perclos=perclos,
            yawn_fraction=yawn_fraction,
            off_task_fraction=off_task_fraction,
            neg_affect=neg_affect,
        )

        # 2. Blend with LSTM if model_mode == "lstm" (contracts.md §6: 0.5*heuristic + 0.5*lstm)
        if model_mode == "lstm" and lstm_fatigue_index is not None and lstm_attention_score is not None:
            raw_fatigue = 0.5 * raw_fatigue + 0.5 * lstm_fatigue_index
            raw_attention = 0.5 * raw_attention + 0.5 * lstm_attention_score

        # 3. Apply Exponential Moving Average (EMA) smoothing
        if state.smoothed_fatigue_index is None:
            state.smoothed_fatigue_index = raw_fatigue
            state.smoothed_attention_score = raw_attention
            state.smoothed_confidence = landmark_confidence
        else:
            alpha = self.ema_alpha
            state.smoothed_fatigue_index = alpha * raw_fatigue + (1.0 - alpha) * state.smoothed_fatigue_index
            state.smoothed_attention_score = alpha * raw_attention + (1.0 - alpha) * state.smoothed_attention_score
            state.smoothed_confidence = alpha * landmark_confidence + (1.0 - alpha) * state.smoothed_confidence

        fatigue_val = state.smoothed_fatigue_index
        attention_val = state.smoothed_attention_score
        confidence_val = state.smoothed_confidence

        # 4. Determine instant target statuses
        is_confident = (confidence_val >= self.min_confidence)

        if not is_confident:
            instant_fatigue = "Unknown"
            instant_attention = "Unknown"
        else:
            instant_fatigue = "Fatigued" if fatigue_val >= self.fatigue_threshold else "Normal"
            instant_attention = "Distracted" if attention_val <= self.attention_threshold else "Attentive"

        # 5. Apply Status Hysteresis (STATUS_HYSTERESIS_S=3.0s)
        # If low confidence, immediately switch to Unknown (contracts.md §5: show Unknown rather than low-quality guess)
        if not is_confident:
            state.displayed_fatigue_status = "Unknown"
            state.displayed_attention_status = "Unknown"
            state.fatigue_candidate_status = "Unknown"
            state.attention_candidate_status = "Unknown"
            state.fatigue_status_changed_at = timestamp
            state.attention_status_changed_at = timestamp
        else:
            # Fatigue hysteresis
            if instant_fatigue != state.displayed_fatigue_status:
                if instant_fatigue != state.fatigue_candidate_status:
                    state.fatigue_candidate_status = instant_fatigue
                    state.fatigue_status_changed_at = timestamp
                elif (timestamp - state.fatigue_status_changed_at) >= self.status_hysteresis_s:
                    state.displayed_fatigue_status = instant_fatigue
            else:
                state.fatigue_candidate_status = instant_fatigue
                state.fatigue_status_changed_at = timestamp

            # Attention hysteresis
            if instant_attention != state.displayed_attention_status:
                if instant_attention != state.attention_candidate_status:
                    state.attention_candidate_status = instant_attention
                    state.attention_status_changed_at = timestamp
                elif (timestamp - state.attention_status_changed_at) >= self.status_hysteresis_s:
                    state.displayed_attention_status = instant_attention
            else:
                state.attention_candidate_status = instant_attention
                state.attention_status_changed_at = timestamp

        # 6. Update Validation State Machines & Emit Alerts
        alerts_emitted: List[AlertEvent] = []
        is_fatigued_cond = (fatigue_val >= self.fatigue_threshold)
        is_distracted_cond = (attention_val <= self.attention_threshold)

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Fatigue state machine
        fatigue_alert = state.fatigue_sm.update(
            is_condition_active=is_fatigued_cond,
            is_confident=is_confident,
            timestamp=timestamp,
            cooldown_s=self.alert_cooldown_s,
            hysteresis_s=self.status_hysteresis_s,
        )
        if fatigue_alert:
            alerts_emitted.append(AlertEvent(
                track_id=track_id,
                label=label,
                type="fatigue",
                status="New",
                message="Repeated fatigue-related indicators during the current session.",
                confidence=confidence_val,
                created_at=now_iso,
                timestamp=timestamp,
            ))

        # Distraction state machine
        distraction_alert = state.distraction_sm.update(
            is_condition_active=is_distracted_cond,
            is_confident=is_confident,
            timestamp=timestamp,
            cooldown_s=self.alert_cooldown_s,
            hysteresis_s=self.status_hysteresis_s,
        )
        if distraction_alert:
            alerts_emitted.append(AlertEvent(
                track_id=track_id,
                label=label,
                type="distraction",
                status="New",
                message="Repeated distraction-related indicators during the current session.",
                confidence=confidence_val,
                created_at=now_iso,
                timestamp=timestamp,
            ))

        # 7. Construct canonical TrackResult dictionary (contracts.md §2.1)
        track_result = {
            "track_id": track_id,
            "label": label,
            "bbox": bbox,
            "bbox_normalized": True,
            "landmark_confidence": round(float(landmark_confidence), 4),
            "features": {
                "ear": round(float(ear), 4),
                "mar": round(float(mar), 4),
                "perclos": round(float(perclos), 4),
                "head_yaw": round(float(head_yaw), 2),
                "head_pitch": round(float(head_pitch), 2),
            },
            "drowsiness": {
                "label": drowsiness_label,
                "p_drowsy": round(float(p_drowsy), 4),
            },
            "emotion": {
                "top": top_emotion,
                "probs": {k: round(float(v), 4) for k, v in emotion_probs.items()},
            },
            "attention_score": round(float(attention_val), 1),
            "fatigue_index": round(float(fatigue_val), 2),
            "attention_status": state.displayed_attention_status,
            "fatigue_status": state.displayed_fatigue_status,
            "confidence": round(float(confidence_val), 2),
            "model_mode": model_mode,
        }

        return track_result, alerts_emitted

    def purge_track(self, track_id: int) -> None:
        """Purge state for a removed or expired track."""
        if track_id in self._track_states:
            del self._track_states[track_id]

    def clear(self) -> None:
        """Clear all active track states."""
        self._track_states.clear()
