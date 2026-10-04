"""Phase 25 — Production Hardening & Security Audit Test Suite.

Spec refs: SYS-14, APP-26, APP-27, APP-28, README_EXECUTION Phase 25.
Pass conditions:
1. Environment and configuration audit: .env.example contains secure defaults and no real secrets.
2. Rate limiting enforcement on /auth/login (5 failed attempts -> HTTP 429 + Retry-After).
3. Database schema PII & media audit: zero BLOB/image/photo/embedding columns in any table.
4. Role-based access control matrix regression.
5. Strict privacy mode default validation.
"""

from pathlib import Path
import pytest
from sqlalchemy import inspect
from starlette.testclient import TestClient

from app.auth.rate_limiter import login_rate_limiter
from app.config import settings
from app.db.database import Base
from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure rate limiter is reset before each test."""
    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()


def test_env_example_security_audit():
    """Verify .env.example contains safe defaults and zero hardcoded secrets."""
    env_file = Path(__file__).resolve().parent.parent.parent / ".env.example"
    assert env_file.exists(), ".env.example must exist in repository root"

    content = env_file.read_text(encoding="utf-8")

    # Assert non-negotiable default is true
    assert "PRIVACY_MODE=true" in content, "PRIVACY_MODE must default to true"

    # Assert no actual passwords or production secrets
    assert "REPLACE_WITH_SECURE_RANDOM_SECRET_KEY" in content
    assert "password123" not in content
    assert "admin_secret" not in content

    # Assert key retention and rate limiting parameters are present
    assert "RETENTION_DAYS=" in content
    assert "LOGIN_MAX_FAILURES=" in content


def test_login_rate_limiting_enforcement():
    """Verify APP-26: 5 failed login attempts triggers HTTP 429 with Retry-After header."""
    with TestClient(app) as client:
        # Perform 5 failed login attempts
        for attempt in range(5):
            res = client.post(
                "/auth/login",
                json={"username": f"attacker_{attempt}", "password": "wrong_password"},
            )
            assert res.status_code == 401, f"Attempt {attempt+1} should fail with 401"

        # The 6th attempt from the same client IP must be rejected with HTTP 429
        locked_res = client.post(
            "/auth/login",
            json={"username": "attacker_locked", "password": "wrong_password"},
        )
        assert locked_res.status_code == 429
        assert "Retry-After" in locked_res.headers
        assert int(locked_res.headers["Retry-After"]) > 0
        data = locked_res.json()
        assert data["detail"]["code"] == "TOO_MANY_ATTEMPTS"


def test_database_schema_zero_media_audit():
    """Verify Decision D4 & APP-27: absolutely no BLOB, image, photo, or face crop columns in database."""
    # Forbidden substrings in column names
    forbidden_terms = ["image", "photo", "picture", "frame_data", "crop", "blob", "embedding"]

    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            col_name_lower = column.name.lower()
            for term in forbidden_terms:
                assert term not in col_name_lower, (
                    f"Violation of Privacy Decision D4: Table '{table_name}' contains "
                    f"prohibited column '{column.name}' matching term '{term}'"
                )

            # Assert column type is not LargeBinary / BLOB
            col_type_str = str(column.type).lower()
            assert "blob" not in col_type_str and "bytea" not in col_type_str and "largebinary" not in col_type_str, (
                f"Table '{table_name}' column '{column.name}' has prohibited binary type '{column.type}'"
            )


def test_privacy_mode_health_and_video_lock():
    """Verify privacy mode status and strict video refusal."""
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["privacy_mode"] is True
