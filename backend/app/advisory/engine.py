"""Class Fatigue Advisory Engine — Phase 21-23 Mobile App Support.

Implements docs/README_MOBILE_FATIGUE_ALERTS.md:
1. Calculates class_fatigue_pct = 100 * mean(fatigue_index of all non-Unknown tracks).
2. Maps percentage to advisory levels 1-4 with exact copy (D8 non-diagnostic).
3. Applies EMA smoothing (alpha=0.3), hold-time hysteresis (STATUS_HYSTERESIS_S=3s),
   push persistence (ADVISORY_PERSIST_S=60s), and cooldown (ALERT_COOLDOWN_S=300s).
4. Emits additive fatigue_advisory dictionary for ClassSnapshot and push notifications.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.config import settings

ADVISORY_LEVELS = {
    1: {
        "code": "CONTINUE",
        "message": "Continue with the class.",
    },
    2: {
        "code": "INTERACTIVE",
        "message": "Make the session more interactive.",
    },
    3: {
        "code": "SHORT_BREAK",
        "message": "Do a short activity or give a short break.",
    },
    4: {
        "code": "RESCHEDULE",
        "message": "Most students show fatigue indicators. Consider continuing the class tomorrow.",
    },
}


def compute_advisory_level(
    pct: float,
    bands: Tuple[float, float, float] = (25.0, 50.0, 75.0),
) -> int:
    """Return advisory level 1..4 based on configured band thresholds."""
    if pct < bands[0]:
        return 1
    if pct < bands[1]:
        return 2
    if pct < bands[2]:
        return 3
    return 4


@dataclass
class SessionAdvisoryState:
    """Maintains temporal stability state for a specific session's advisory."""
    session_id: int
    smoothed_pct: Optional[float] = None
    current_level: int = 1
    candidate_level: Optional[int] = None
    candidate_since: Optional[float] = None
    level_confirmed_since: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    last_push_times: Dict[int, float] = field(default_factory=dict)  # level -> timestamp


class ClassFatigueAdvisoryEngine:
    """Stateful engine calculating smoothed class advisory alerts and push notifications."""

    def __init__(
        self,
        bands: Tuple[float, float, float] = (25.0, 50.0, 75.0),
        min_tracks: int = 5,
        hysteresis_s: float = 3.0,
        persist_s: float = 60.0,
        cooldown_s: float = 300.0,
        alpha: float = 0.3,
    ) -> None:
        self.bands = bands
        self.min_tracks = min_tracks
        self.hysteresis_s = hysteresis_s
        self.persist_s = persist_s
        self.cooldown_s = cooldown_s
        self.alpha = alpha
        self._states: Dict[int, SessionAdvisoryState] = {}

    def _get_state(self, session_id: int) -> SessionAdvisoryState:
        if session_id not in self._states:
            self._states[session_id] = SessionAdvisoryState(session_id=session_id)
        return self._states[session_id]

    def process_class_tracks(
        self,
        session_id: int,
        tracks: Sequence[Dict[str, Any]],
        timestamp: Optional[float] = None,
        class_name: str = "Classroom",
        min_tracks: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Compute advisory from student tracks.
        
        Args:
            session_id: Active session id
            tracks: Sequence of dicts with {"fatigue_status": str, "fatigue_index": float}
            timestamp: Monotonic or epoch timestamp in seconds
            class_name: Human readable classroom name
            min_tracks: Optional override for usable track threshold

        Returns:
            Tuple of (fatigue_advisory_payload or None, push_notification_payload or None)
        """
        now = timestamp if timestamp is not None else datetime.now(timezone.utc).timestamp()
        state = self._get_state(session_id)

        # 1. Filter usable tracks: status != 'Unknown' and fatigue_index is numeric
        usable_indices = [
            t.get("fatigue_index", 0.0)
            for t in tracks
            if t.get("fatigue_status") != "Unknown" and t.get("fatigue_index") is not None
        ]

        threshold = min_tracks if min_tracks is not None else self.min_tracks
        if len(usable_indices) < threshold:
            # Rule: Not enough usable tracks -> null advisory
            return None, None

        # 2. Raw class fatigue percentage
        raw_pct = float(100.0 * (sum(usable_indices) / len(usable_indices)))

        # 3. EMA smoothing: alpha=0.3
        if state.smoothed_pct is None:
            state.smoothed_pct = raw_pct
        else:
            state.smoothed_pct = self.alpha * raw_pct + (1.0 - self.alpha) * state.smoothed_pct

        raw_level = compute_advisory_level(state.smoothed_pct, self.bands)

        # 4. Hysteresis: new level must hold for hysteresis_s before displayed level changes
        if raw_level != state.current_level:
            if state.candidate_level == raw_level:
                if state.candidate_since and (now - state.candidate_since >= self.hysteresis_s):
                    state.current_level = raw_level
                    state.level_confirmed_since = now
                    state.candidate_level = None
                    state.candidate_since = None
            else:
                state.candidate_level = raw_level
                state.candidate_since = now
        else:
            state.candidate_level = None
            state.candidate_since = None

        # 5. Format advisory payload
        active_level = state.current_level
        level_info = ADVISORY_LEVELS[active_level]
        since_iso = datetime.fromtimestamp(state.level_confirmed_since, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        advisory_payload = {
            "class_fatigue_pct": round(state.smoothed_pct, 1),
            "level": active_level,
            "code": level_info["code"],
            "message": level_info["message"],
            "usable_tracks": len(usable_indices),
            "since": since_iso,
        }

        # 6. Push notification evaluation (rules 3, 4, 5)
        # Push requires:
        # - Level held for persist_s (or longer)
        # - Cooldown: at most 1 push per level within cooldown_s
        # - Level 4 requires persist_s and min_tracks (satisfied)
        push_payload = None
        duration_at_level = now - state.level_confirmed_since
        last_push = state.last_push_times.get(active_level)

        if duration_at_level >= self.persist_s:
            if last_push is None or (now - last_push >= self.cooldown_s):
                state.last_push_times[active_level] = now
                push_payload = {
                    "title": f"{class_name}: fatigue indicator",
                    "body": level_info["message"],
                    "data": {
                        "session_id": session_id,
                        "level": active_level,
                        "code": level_info["code"],
                    },
                }

        return advisory_payload, push_payload


# Global singleton advisory engine initialized with configured parameters
advisory_engine = ClassFatigueAdvisoryEngine(
    bands=settings.ADVISORY_BANDS,
    min_tracks=settings.ADVISORY_MIN_TRACKS,
    hysteresis_s=settings.STATUS_HYSTERESIS_S,
    persist_s=settings.ADVISORY_PERSIST_S,
    cooldown_s=settings.ALERT_COOLDOWN_S,
)
