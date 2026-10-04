"""Security Tests — Section 3: Authentication (A1–A15).

Tests cover:
  A1  Valid login returns 200, JWT, and role.
  A2  Wrong password returns 401 with generic message.
  A3  Unknown user returns 401 with SAME message (no user enumeration).
  A4  Disabled account returns 401 (no token).
  A5  Missing token on protected route → 401.
  A6  Malformed / garbage token → 401.
  A7  Expired token → 401.
  A8  Tampered token signature → 401.
  A9  alg:none unsigned JWT → 401.
  A10 Token signed with wrong secret → 401.
  A11 Role claim forged (payload modified, old signature) → 401.
  A12 Token for a user disabled after issuance → 401/403.
  A13 Password stored as bcrypt hash, never plaintext.
  A14 Login rate limiting: 6th consecutive failure from same IP → 429.
  A15 No hash / stack trace / secret leaks in error responses.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth.jwt import create_access_token, hash_password
from app.auth.rate_limiter import login_rate_limiter
from app.config import settings
from app.db.models import User

from .conftest import _Session, _make_user, _login, _auth


class TestAuthentication:
    """Section 3: Authentication tests A1–A15."""

    # ------------------------------------------------------------------
    # A1 — Valid login
    # ------------------------------------------------------------------
    def test_A1_valid_login_returns_token_and_role(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()

        r = client.post("/auth/login", json={"username": "admin1", "password": "Admin@Pass1"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["role"] == "admin"

    # ------------------------------------------------------------------
    # A2 + A3 — Wrong password and unknown user produce identical 401 responses
    # ------------------------------------------------------------------
    def test_A2_wrong_password_returns_401(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        r = client.post("/auth/login", json={"username": "admin1", "password": "WRONG"})
        assert r.status_code == 401
        assert "access_token" not in r.json()

    def test_A3_unknown_user_same_response_as_wrong_password(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        wrong_pw = client.post("/auth/login", json={"username": "admin1", "password": "bad"})
        no_user = client.post("/auth/login", json={"username": "nobody_ever", "password": "bad"})
        # A2 + A3: identical status and identical response body (no enumeration)
        assert wrong_pw.status_code == no_user.status_code == 401
        assert wrong_pw.json() == no_user.json(), "User enumeration detected — responses differ!"

    # ------------------------------------------------------------------
    # A4 — Disabled account
    # ------------------------------------------------------------------
    def test_A4_disabled_account_rejected(self, client):
        db = _Session()
        _make_user(db, "teacherOff", "PassOff#!", "teacher", active=False)
        db.close()
        r = client.post("/auth/login", json={"username": "teacherOff", "password": "PassOff#!"})
        assert r.status_code in (401, 403)
        assert "access_token" not in r.json()

    # ------------------------------------------------------------------
    # A5 — Missing token
    # ------------------------------------------------------------------
    def test_A5_missing_token_returns_401(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    # ------------------------------------------------------------------
    # A6 — Malformed / garbage token
    # ------------------------------------------------------------------
    def test_A6_malformed_token_returns_401(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
        assert r.status_code == 401

    # ------------------------------------------------------------------
    # A7 — Expired token
    # ------------------------------------------------------------------
    def test_A7_expired_token_returns_401(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        expired = create_access_token(
            subject="admin1",
            role="admin",
            expires_delta=timedelta(seconds=-10),  # already expired
        )
        r = client.get("/auth/me", headers=_auth(expired))
        assert r.status_code == 401

    # ------------------------------------------------------------------
    # A8 — Tampered signature
    # ------------------------------------------------------------------
    def test_A8_tampered_token_signature_rejected(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        token = _login(client, "admin1", "Admin@Pass1")
        # Flip last two chars of signature
        bad = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
        r = client.get("/auth/me", headers=_auth(bad))
        assert r.status_code == 401

    # ------------------------------------------------------------------
    # A9 — alg:none unsigned JWT
    # ------------------------------------------------------------------
    def test_A9_alg_none_unsigned_jwt_rejected(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        # Manually construct a none-alg token
        header = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0"  # {"alg":"none","typ":"JWT"}
        import base64, json as _json
        payload_bytes = base64.urlsafe_b64encode(
            _json.dumps({
                "sub": "admin1",
                "role": "admin",
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            }).encode()
        ).rstrip(b"=").decode()
        alg_none_token = f"{header}.{payload_bytes}."
        r = client.get("/auth/me", headers=_auth(alg_none_token))
        assert r.status_code == 401

    # ------------------------------------------------------------------
    # A10 — Token signed with a different secret
    # ------------------------------------------------------------------
    def test_A10_wrong_secret_token_rejected(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        rogue_token = jwt.encode(
            {"sub": "admin1", "role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            key="completely-different-secret-xyz",
            algorithm="HS256",
        )
        r = client.get("/auth/me", headers=_auth(rogue_token))
        assert r.status_code == 401

    # ------------------------------------------------------------------
    # A11 — Forged role claim (payload modified, old signature)
    # ------------------------------------------------------------------
    def test_A11_forged_role_claim_rejected(self, client):
        db = _Session()
        _make_user(db, "teacherA", "PassA#123", "teacher")
        db.close()
        token = _login(client, "teacherA", "PassA#123")
        # Split and re-encode payload with role=admin, keeping old signature
        import base64 as b64, json as _j
        header_b64, payload_b64, sig = token.split(".")
        # Decode payload
        padding = "=" * (-len(payload_b64) % 4)
        decoded = _j.loads(b64.urlsafe_b64decode(payload_b64 + padding))
        decoded["role"] = "admin"
        new_payload = b64.urlsafe_b64encode(_j.dumps(decoded).encode()).rstrip(b"=").decode()
        forged_token = f"{header_b64}.{new_payload}.{sig}"
        r = client.get("/auth/me", headers=_auth(forged_token))
        assert r.status_code == 401

    # ------------------------------------------------------------------
    # A12 — Token for user disabled after issuance
    # ------------------------------------------------------------------
    def test_A12_token_for_disabled_user_rejected(self, client):
        db = _Session()
        u = _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        token = _login(client, "admin1", "Admin@Pass1")
        # Disable user
        db = _Session()
        user = db.query(User).filter(User.username == "admin1").first()
        user.active = False
        db.commit()
        db.close()
        # Token should now fail
        r = client.get("/auth/me", headers=_auth(token))
        assert r.status_code in (401, 403)

    # ------------------------------------------------------------------
    # A13 — Password stored as bcrypt hash
    # ------------------------------------------------------------------
    def test_A13_password_hash_not_plaintext(self):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        user = db.query(User).filter(User.username == "admin1").first()
        stored_hash = user.password_hash
        db.close()
        assert stored_hash != "Admin@Pass1", "Password stored as plaintext!"
        assert stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"), (
            f"Expected bcrypt hash prefix, got: {stored_hash[:8]}"
        )

    # ------------------------------------------------------------------
    # A14 — Login rate limiting (6 failures → 429)
    # ------------------------------------------------------------------
    def test_A14_login_rate_limiting_triggers_429(self, client):
        db = _Session()
        _make_user(db, "admin1", "Admin@Pass1", "admin")
        db.close()
        # 5 failures allowed; the 6th must be 429
        for _ in range(5):
            client.post("/auth/login", json={"username": "admin1", "password": "badpass"})
        r = client.post("/auth/login", json={"username": "admin1", "password": "badpass"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers

    # ------------------------------------------------------------------
    # A15 — No secrets or stack traces in error responses
    # ------------------------------------------------------------------
    def test_A15_no_secrets_in_error_response(self, client):
        r = client.post("/auth/login", json={"username": "admin1", "password": "bad"})
        body_text = r.text.lower()
        for forbidden in ("traceback", "secret", "password_hash", "sqlalchemy", "stack", "$2b$"):
            assert forbidden not in body_text, f"Sensitive data leaked in error response: '{forbidden}'"
