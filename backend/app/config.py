"""Application Configuration and Environment Settings.

Implements SYS-10, APP-24, CON §4, CON §5:
- Centralized configuration with environment variable overrides.
- Defaults strictly aligned with contracts.md.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _get_bool(env_var: str, default: bool) -> bool:
    val = os.getenv(env_var)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on")


def _get_float(env_var: str, default: float) -> float:
    val = os.getenv(env_var)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _get_int(env_var: str, default: int) -> int:
    val = os.getenv(env_var)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass
class Settings:
    """System settings loaded from environment or contracts.md defaults."""

    # Server & Privacy
    HOST: str = os.getenv("HOST", "0.0.0.0")  # nosec B104 - container network binding
    PORT: int = _get_int("PORT", 8000)
    PRIVACY_MODE: bool = _get_bool("PRIVACY_MODE", True)  # Non-negotiable default: True (CON §5)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-contracts-d4")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480)

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{Path(__file__).resolve().parent.parent / 'app.db'}"
    )

    # Rate & Thresholds (contracts.md §5)
    TELEMETRY_HZ: int = _get_int("TELEMETRY_HZ", 2)
    TARGET_FPS: int = _get_int("TARGET_FPS", 20)
    MIN_CONFIDENCE: float = _get_float("MIN_CONFIDENCE", 0.80)
    WINDOW_FRAMES: int = _get_int("WINDOW_FRAMES", 30)
    STATUS_HYSTERESIS_S: float = _get_float("STATUS_HYSTERESIS_S", 3.0)
    FATIGUE_PERSIST_S: float = _get_float("FATIGUE_PERSIST_S", 45.0)
    DISTRACTION_PERSIST_S: float = _get_float("DISTRACTION_PERSIST_S", 30.0)
    ALERT_COOLDOWN_S: float = _get_float("ALERT_COOLDOWN_S", 300.0)
    OBSERVATION_INTERVAL_S: int = _get_int("OBSERVATION_INTERVAL_S", 5)
    CAMERA_TIMEOUT_S: float = _get_float("CAMERA_TIMEOUT_S", 10.0)
    AI_HEARTBEAT_TIMEOUT_S: float = _get_float("AI_HEARTBEAT_TIMEOUT_S", 10.0)
    RETENTION_DAYS: int = _get_int("RETENTION_DAYS", 180)
    ADVISORY_BANDS: tuple[float, float, float] = (25.0, 50.0, 75.0)
    ADVISORY_MIN_TRACKS: int = _get_int("ADVISORY_MIN_TRACKS", 5)
    ADVISORY_PERSIST_S: float = _get_float("ADVISORY_PERSIST_S", 60.0)

    # Mobile Push Notification Settings (README_MOBILE_ALERT_NOTIFICATIONS.md §6.4)
    PUSH_ENABLED: bool = _get_bool("PUSH_ENABLED", True)
    PUSH_TTL_S: int = _get_int("PUSH_TTL_S", 120)
    PUSH_NOTIFY_LEVEL1: bool = _get_bool("PUSH_NOTIFY_LEVEL1", True)
    EXPO_ACCESS_TOKEN: Optional[str] = os.getenv("EXPO_ACCESS_TOKEN", None)

    # Environment & Security
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ALLOWED_ORIGINS: list[str] = field(
        default_factory=lambda: (
            [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
            if os.getenv("ALLOWED_ORIGINS")
            else [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8081",
                "http://localhost:8082",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8081",
                "http://127.0.0.1:8082",
            ]
        )
    )
    MAX_WS_CONNECTIONS: int = _get_int("MAX_WS_CONNECTIONS", 100)
    MAX_PAGE_SIZE: int = _get_int("MAX_PAGE_SIZE", 100)
    PASSWORD_POLICY_STRICT: bool = _get_bool("PASSWORD_POLICY_STRICT", False)

    # Live Camera Detection Settings (LC-1, contracts.md §6.5)
    LIVE_CAMERA_ENABLED: bool = _get_bool("LIVE_CAMERA_ENABLED", True)
    LIVE_MAX_CONNECTIONS: int = _get_int("LIVE_MAX_CONNECTIONS", 2)
    LIVE_MAX_PER_USER: int = _get_int("LIVE_MAX_PER_USER", 1)
    LIVE_WORKERS: int = _get_int("LIVE_WORKERS", 1)
    LIVE_TARGET_FPS: int = _get_int("LIVE_TARGET_FPS", 10)
    LIVE_MAX_FPS: int = _get_int("LIVE_MAX_FPS", 15)
    LIVE_MAX_FACES: int = _get_int("LIVE_MAX_FACES", 10)
    LIVE_WINDOW_FRAMES: int = _get_int("LIVE_WINDOW_FRAMES", 30)
    LIVE_MAX_FRAME_BYTES: int = _get_int("LIVE_MAX_FRAME_BYTES", 300000)
    LIVE_MAX_DIM: int = _get_int("LIVE_MAX_DIM", 1280)
    LIVE_IDLE_TIMEOUT_S: int = _get_int("LIVE_IDLE_TIMEOUT_S", 300)
    LIVE_MAX_SESSION_S: int = _get_int("LIVE_MAX_SESSION_S", 1800)
    LIVE_EMOTION_MIN_CONF: float = _get_float("LIVE_EMOTION_MIN_CONF", 0.50)


settings = Settings()
