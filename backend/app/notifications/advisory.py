"""Class Fatigue Advisory Logic and Level Selection.

Implements README_MOBILE_ALERT_NOTIFICATIONS.md §7.2:
- Level selection:
    Level 1: 0% to <25%   ("Continue with the class.")
    Level 2: 25% to <50%  ("Make the session more interactive.")
    Level 3: 50% to <75%  ("Do a short activity or give a short break.")
    Level 4: 75% to 100%  ("Most students show fatigue indicators. Consider continuing the class tomorrow.")
- Stability rules: EMA smoothing (alpha=0.3), hold-time hysteresis (STATUS_HYSTERESIS_S=3s),
  push persistence (ADVISORY_PERSIST_S=60s), and cooldown (ALERT_COOLDOWN_S=300s).
"""

from typing import Any, Dict, Sequence, Tuple

from app.advisory.engine import (
    ADVISORY_LEVELS,
    ClassFatigueAdvisoryEngine,
    SessionAdvisoryState,
    advisory_engine,
    compute_advisory_level as advisory_level,
)

__all__ = [
    "ADVISORY_LEVELS",
    "ClassFatigueAdvisoryEngine",
    "SessionAdvisoryState",
    "advisory_engine",
    "advisory_level",
]
