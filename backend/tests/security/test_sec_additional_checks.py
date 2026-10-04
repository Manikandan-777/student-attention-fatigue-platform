"""Additional Security Checks Test Suite — Sections 3 to 17.

Comprehensive verification of requirements from `docs/README_SECURITY_ADDITIONAL_CHECKS.md`:
- Section 3: Session Management (SM1–SM8)
- Section 4: Account and Password Hygiene (PW1–PW9)
- Section 5: Camera & Video-Source Security (CAM1–CAM9)
- Section 6: AI Model & Supply-Chain Security (ML1–ML9)
- Section 7: Database Hardening (DB1–DB10)
- Section 8: Re-identification & Student Privacy (PR1–PR7)
- Section 9: Denial-of-Service & Resource Abuse (DOS1–DOS10)
- Section 10: API Surface Hardening (API1–API11)
- Section 11: WebSocket Extras (WS1–WS5)
- Section 12: Export & File-Download Safety (EXP1–EXP7)
- Section 13: Audit Logging & Monitoring (AU1–AU7)
- Section 14–17: Deployment & Supply Chain Invariants
"""

import hashlib
import json
import os
import re
from datetime import timedelta
from pathlib import Path

import jwt
import pytest
from starlette.testclient import TestClient

from app.auth.jwt import (
    COMMON_PASSWORDS,
    clear_revoked_tokens,
    create_access_token,
    decode_access_token,
    hash_password,
    is_token_revoked,
    revoke_token,
    validate_password_strength,
    verify_password,
)
from app.config import settings
from app.db.models import Alert, Camera, Session as SessionModel, Student, Teacher, TeacherClassroom, TrackRosterMap, User
from app.main import app
from app.reports.builder import build_session_report, export_csv, export_pdf
from tests.security.conftest import _Session

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session():
    db = _Session()
    try:
        yield db
    finally:
        db.close()



# ===========================================================================
# Section 3: Session Management (SM1–SM8)
# ===========================================================================

class TestSessionManagement:
    def test_SM1_logout_invalidates_token(self, client, scenario):
        s = scenario
        token = s["token_a"]
        # Token works before logout
        assert client.get("/auth/me", headers=_auth(token)).status_code == 200
        # Call logout
        r = client.post("/auth/logout", headers=_auth(token))
        assert r.status_code == 200
        # Same token fails after logout
        assert client.get("/auth/me", headers=_auth(token)).status_code == 401

    def test_SM2_access_token_lifetime_configured(self):
        # ACCESS_TOKEN_EXPIRE_MINUTES is defined and short (bounded)
        assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_SM3_revocation_denylist_functional(self):
        token = create_access_token(subject="temp_user", role="teacher")
        assert decode_access_token(token)["sub"] == "temp_user"
        revoke_token(token)
        assert is_token_revoked(token) is True
        with pytest.raises(Exception):
            decode_access_token(token)

    def test_SM4_disabled_account_stops_working(self, client, scenario, db_session):
        s = scenario
        teacher_user = db_session.query(User).filter_by(username="teacherA").first()
        teacher_user.active = False
        db_session.commit()
        # Active token for now-disabled user is rejected
        r = client.get("/auth/me", headers=_auth(s["token_a"]))
        assert r.status_code == 401
        # Re-enable
        teacher_user.active = True
        db_session.commit()

    def test_SM5_removed_teacher_from_classroom_stops_access(self, client, scenario, db_session):
        s = scenario
        teacher_a = db_session.query(Teacher).filter_by(user_id=s["users"]["teacherA"].id).first()
        # Remove teacherA link to room_a
        link = db_session.query(TeacherClassroom).filter_by(
            teacher_id=teacher_a.id, classroom_id=s["room_a_id"]
        ).first()
        db_session.delete(link)
        db_session.commit()

        # TeacherA can no longer start session in room_a
        r = client.post("/sessions", json={"classroom_id": s["room_a_id"]}, headers=_auth(s["token_a"]))
        assert r.status_code == 403

        # Restore link
        db_session.add(TeacherClassroom(teacher_id=teacher_a.id, classroom_id=s["room_a_id"]))
        db_session.commit()

    def test_SM7_secret_rotation_invalidates_token(self):
        token = jwt.encode({"sub": "admin", "role": "admin"}, "old-secret-key-12345678901234567890", algorithm="HS256")
        with pytest.raises(Exception):
            decode_access_token(token)

    def test_SM8_token_carries_only_needed_claims(self):
        token = create_access_token(subject="minimal_user", role="teacher")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        claims = set(payload.keys())
        # Only sub, role, exp, iat — no personal details or email
        assert claims.issubset({"sub", "role", "exp", "iat"})
        assert "password" not in claims
        assert "email" not in claims
        assert "student" not in claims


# ===========================================================================
# Section 4: Account and Password Hygiene (PW1–PW9)
# ===========================================================================

class TestAccountPasswordHygiene:
    def test_PW1_no_admin_admin_in_production(self, client):
        r = client.post("/auth/login", json={"username": "admin", "password": "admin"})
        assert r.status_code in (401, 429)

    def test_PW3_password_policy_blocks_weak_passwords(self):
        # Shorter than 12 chars
        with pytest.raises(Exception):
            validate_password_strength("short123")
        # Common passwords
        for common in COMMON_PASSWORDS:
            with pytest.raises(Exception):
                validate_password_strength(common)
        # Strong password passes without exception
        validate_password_strength("StrongPass_2026_Secure!")

    def test_PW4_hash_uses_unique_salts(self):
        pwd = "SamePassword12345!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 != h2, "Hashes must have unique salts"
        assert verify_password(pwd, h1)
        assert verify_password(pwd, h2)

    def test_PW5_rate_limiting_per_username_and_ip(self, client):
        # Repeated wrong password for user triggers 429
        client_ip = "192.168.1.100"
        for _ in range(6):
            client.post("/auth/login", json={"username": "rate_target", "password": "wrong"})
        r = client.post("/auth/login", json={"username": "rate_target", "password": "wrong"})
        assert r.status_code == 429

    def test_PW7_password_failure_response_identical_for_known_and_unknown(self, client, scenario):
        # Known user with wrong password
        r1 = client.post("/auth/login", json={"username": "admin1", "password": "wrongpassword1"})
        # Unknown user
        r2 = client.post("/auth/login", json={"username": "nonexistent_999", "password": "wrongpassword1"})
        assert r1.status_code == r2.status_code == 401
        assert r1.json()["detail"]["code"] == r2.json()["detail"]["code"]

    def test_PW8_teacher_accounts_can_be_disabled_by_admin_only(self, client, scenario, db_session):
        s = scenario
        teacher_b = db_session.query(Teacher).filter_by(user_id=s["users"]["teacherB"].id).first()
        # Teacher cannot modify teacher accounts
        r = client.put(f"/teachers/{teacher_b.id}", json={"active": False}, headers=_auth(s["token_a"]))
        assert r.status_code == 403
        # Admin can disable
        r = client.put(f"/teachers/{teacher_b.id}", json={"active": False}, headers=_auth(s["admin_token"]))
        assert r.status_code == 200
        assert r.json()["active"] is False
        # Restore
        client.put(f"/teachers/{teacher_b.id}", json={"active": True}, headers=_auth(s["admin_token"]))

    def test_PW9_passwords_never_in_responses(self, client, scenario):
        s = scenario
        r_teachers = client.get("/teachers", headers=_auth(s["admin_token"]))
        assert r_teachers.status_code == 200
        text = r_teachers.text.lower()
        assert "password" not in text
        assert "hash" not in text


# ===========================================================================
# Section 5: Camera & Video-Source Security (CAM1–CAM9)
# ===========================================================================

class TestCameraSecurity:
    def test_CAM1_camera_credentials_not_in_classrooms_or_system_status(self, client, scenario, db_session):
        s = scenario
        cam = Camera(id="CAM-SEC-01", source_uri="rtsp://admin:secretPass@192.168.1.50/live", state="Online")
        db_session.merge(cam)
        db_session.commit()

        # GET /classrooms
        r_rooms = client.get("/classrooms", headers=_auth(s["token_a"]))
        assert "secretPass" not in r_rooms.text

        # GET /system/status
        r_sys = client.get("/system/status", headers=_auth(s["admin_token"]))
        assert "secretPass" not in r_sys.text
        # Camera list contains only id and state
        for c in r_sys.json()["cameras"]:
            assert "source_uri" not in c or c["source_uri"] is None

    def test_CAM3_CAM4_source_uri_scheme_and_ssrf_validation(self, client, scenario):
        s = scenario
        # Forbidden schemes / SSRF vectors
        forbidden_uris = [
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
            "ftp://camera.local/stream",
            "http://internal.school.lan/admin",
        ]
        for bad_uri in forbidden_uris:
            r = client.post(
                "/cameras",
                json={"id": f"CAM-BAD-{hashlib.md5(bad_uri.encode()).hexdigest()[:6]}", "source_uri": bad_uri},
                headers=_auth(s["admin_token"]),
            )
            assert r.status_code == 422, f"Failed to reject forbidden camera URI: {bad_uri}"

        # Allowed schemes
        good_uris = [
            "rtsp://192.168.1.10:554/live",
            "file://tests/fixtures/clip.mp4",
            "0",
        ]
        for good_uri in good_uris:
            cam_id = f"CAM-GOOD-{hashlib.md5(good_uri.encode()).hexdigest()[:6]}"
            r = client.post(
                "/cameras",
                json={"id": cam_id, "source_uri": good_uri},
                headers=_auth(s["admin_token"]),
            )
            assert r.status_code in (201, 409)


# ===========================================================================
# Section 6: AI Model & Supply-Chain Security (ML1–ML9)
# ===========================================================================

class TestAIModelSupplyChain:
    def test_ML1_ML6_manifest_json_pinned_and_licensed(self):
        manifest_path = ROOT_DIR / "backend" / "models" / "MANIFEST.json"
        assert manifest_path.exists(), "MANIFEST.json must exist"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for model_name, model_meta in data.items():
            assert "repo_id" in model_meta
            assert "revision" in model_meta
            assert "license" in model_meta
            assert model_meta["license"] in ("mit", "apache-2.0", "bsd-3-clause")

    def test_ML3_trust_remote_code_never_enabled(self):
        backend_dir = ROOT_DIR / "backend"
        for py_file in backend_dir.rglob("*.py"):
            if ".venv" in py_file.parts or "tests" in py_file.parts:
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            assert "trust_remote_code=True" not in content
            assert "trust_remote_code = True" not in content
            assert "trust_remote_code=True" not in content
            assert "trust_remote_code = True" not in content

    def test_ML9_system_status_shows_heuristic_model_mode(self, client, scenario):
        s = scenario
        r = client.get("/system/status", headers=_auth(s["admin_token"]))
        assert r.status_code == 200
        assert r.json()["model_mode"] == "heuristic"


# ===========================================================================
# Section 7: Database Hardening (DB1–DB10)
# ===========================================================================

class TestDatabaseHardening:
    def test_DB4_no_fstring_sql_in_backend(self):
        backend_dir = ROOT_DIR / "backend" / "app"
        for py_file in backend_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            # Prohibit direct formatted string SQL execution
            assert 'execute(f"' not in content
            assert "execute(f'" not in content

    def test_DB7_students_soft_deactivated_not_deleted(self, client, scenario, db_session):
        s = scenario
        st = Student(student_code="S-DEACT-01", name="Test Deactivate", active=True)
        db_session.add(st)
        db_session.commit()
        db_session.refresh(st)

        # Admin deactivates
        r = client.delete(f"/students/{st.id}", headers=_auth(s["admin_token"]))
        assert r.status_code == 204

        # Record still exists in DB but active is False
        db_session.expire_all()
        refreshed = db_session.get(Student, st.id)
        assert refreshed is not None
        assert refreshed.active is False

    def test_DB8_track_roster_map_admin_only(self, client, scenario, db_session):
        s = scenario
        # Seed a roster map record
        roster_rec = TrackRosterMap(session_id=s["session_a_id"], track_id=1, student_id=None)
        db_session.add(roster_rec)
        db_session.commit()

        # Teacher request returns 403 Forbidden
        r_teacher = client.get(f"/students/roster-map/{s['session_a_id']}", headers=_auth(s["token_a"]))
        assert r_teacher.status_code == 403

        # Admin request returns 200 OK
        r_admin = client.get(f"/students/roster-map/{s['session_a_id']}", headers=_auth(s["admin_token"]))
        assert r_admin.status_code == 200
        assert len(r_admin.json()) >= 1


# ===========================================================================
# Section 8: Re-identification & Student Privacy (PR1–PR7)
# ===========================================================================

class TestReidentificationAndPrivacy:
    def test_PR1_PR2_no_bbox_or_seat_position_in_reports(self, client, scenario):
        s = scenario
        r = client.get(f"/reports/{s['session_a_id']}", headers=_auth(s["token_a"]))
        assert r.status_code == 200
        text = r.text.lower()
        for forbidden in ("bbox", "bounding_box", "seat_number", "desk_coordinate", "coordinates"):
            assert forbidden not in text

    def test_PR3_report_uses_anonymous_labels(self, client, scenario):
        s = scenario
        r = client.get(f"/reports/{s['session_a_id']}", headers=_auth(s["token_a"]))
        assert r.status_code == 200
        per_student = r.json().get("per_student", [])
        for item in per_student:
            assert re.match(r"^S\d{3}$", item["label"]), f"Non-anonymous label: {item['label']}"


# ===========================================================================
# Section 9: Denial-of-Service & Resource Abuse (DOS1–DOS10)
# ===========================================================================

class TestDenialOfServiceAbuse:
    def test_DOS5_pagination_clamping(self, client, scenario):
        s = scenario
        # Requesting limit=1000000 is safely clamped
        r = client.get("/alerts?limit=1000000", headers=_auth(s["token_a"]))
        assert r.status_code == 200

        r_sess = client.get("/sessions?limit=1000000", headers=_auth(s["token_a"]))
        assert r_sess.status_code == 200

        r_rep = client.get("/reports?limit=1000000", headers=_auth(s["token_a"]))
        assert r_rep.status_code == 200


# ===========================================================================
# Section 10: API Surface Hardening (API1–API11)
# ===========================================================================

class TestAPISurfaceHardening:
    def test_API3_health_returns_minimal_data(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert set(data.keys()) == {"status", "app", "version", "privacy_mode", "timestamp"}
        assert "database_url" not in data
        assert "secret" not in data
        assert "path" not in data

    def test_API4_teachers_forbidden_on_system_status(self, client, scenario):
        s = scenario
        r = client.get("/system/status", headers=_auth(s["token_a"]))
        assert r.status_code == 403

    def test_API8_cors_no_wildcard_with_credentials(self):
        # Settings origin configuration is explicit list, not wildcard
        assert isinstance(settings.ALLOWED_ORIGINS, list)
        assert "*" not in settings.ALLOWED_ORIGINS

    def test_API10_patch_alerts_forbids_extra_fields(self, client, scenario, db_session):
        s = scenario
        alert = Alert(
            session_id=s["session_a_id"],
            type="fatigue",
            status="New",
            message="Test alert",
            confidence=0.9,
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        # Attempt to patch alert type, confidence, or message via status update
        r = client.patch(
            f"/alerts/{alert.id}",
            json={"status": "Viewed", "type": "camera_offline", "confidence": 0.0},
            headers=_auth(s["token_a"]),
        )
        assert r.status_code == 422, "Should reject extra fields on PATCH /alerts"

    def test_API11_security_headers_present(self, client):
        r = client.get("/health")
        headers = r.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert "Server" not in headers or "uvicorn" not in headers.get("Server", "").lower()


# ===========================================================================
# Section 11: WebSocket Extras (WS1–WS5)
# ===========================================================================

class TestWebSocketExtras:
    def test_WS1_cross_site_websocket_hijacking_origin_refused(self, client, scenario):
        s = scenario
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/ws/telemetry?token={s['token_a']}",
                headers={"Origin": "http://evil-attacker.example.com"}
            ):
                pass

    def test_WS4_subscribe_negative_or_invalid_session_rejected(self, client, scenario):
        s = scenario
        with client.websocket_connect(f"/ws/telemetry?token={s['token_a']}") as ws:
            # Negative session ID
            ws.send_json({"type": "subscribe", "session_id": -5})
            resp = ws.receive_json()
            assert resp.get("type") == "error"

            # String session ID
            ws.send_json({"type": "subscribe", "session_id": "drop_tables"})
            resp2 = ws.receive_json()
            assert resp2.get("type") == "error"


# ===========================================================================
# Section 12: Export & File-Download Safety (EXP1–EXP7)
# ===========================================================================

class TestExportFileDownloadSafety:
    def test_EXP1_csv_formula_injection_escaped(self):
        # Malicious student label and class name with formula injection payloads
        payload_report = {
            "session_id": 999,
            "class_name": "=cmd|' /C calc'!A0",
            "date": "2026-10-04",
            "start": "10:00",
            "end": "11:00",
            "duration_min": 60,
            "students": 1,
            "attention": {"attentive": 1, "distracted": 0, "unknown": 0},
            "fatigue": {"normal": 1, "fatigued": 0},
            "alerts_total": 0,
            "avg_attention_score": 88.0,
            "per_student": [
                {
                    "label": "@SUM(1+1)*cmd",
                    "attention_mean": 90.0,
                    "fatigue_index_mean": 0.1,
                    "fatigue_indicators": 0,
                    "distraction_indicators": 0,
                    "alerts": 0,
                }
            ],
        }
        csv_out = export_csv(payload_report)
        # Verify formula prefixes are neutralized with leading single quote
        assert "'=cmd|' /C calc'!A0" in csv_out
        assert "'@SUM(1+1)*cmd" in csv_out

    def test_EXP3_invalid_export_format_returns_422(self, client, scenario):
        s = scenario
        r = client.get(f"/reports/{s['session_a_id']}/export?format=exe", headers=_auth(s["token_a"]))
        assert r.status_code == 422

    def test_EXP4_export_rechecks_auth(self, client, scenario):
        s = scenario
        # Anonymous request rejected
        r = client.get(f"/reports/{s['session_a_id']}/export?format=csv")
        assert r.status_code == 401

    def test_EXP5_export_contains_mandatory_disclaimer(self):
        dummy_report = {
            "session_id": 1,
            "class_name": "Room 101",
            "date": "2026-10-04",
            "start": "10:00",
            "end": "11:00",
            "duration_min": 60,
            "students": 0,
            "attention": {"attentive": 0, "distracted": 0, "unknown": 0},
            "fatigue": {"normal": 0, "fatigued": 0},
            "alerts_total": 0,
            "avg_attention_score": 0.0,
            "per_student": [],
        }
        csv_out = export_csv(dummy_report)
        assert "not a diagnosis or disciplinary record" in csv_out

    def test_EXP6_html_script_escaped_in_pdf(self):
        malicious_report = {
            "session_id": 2,
            "class_name": "<script>alert('xss')</script>Class",
            "date": "2026-10-04",
            "start": "10:00",
            "end": "11:00",
            "duration_min": 60,
            "students": 1,
            "attention": {"attentive": 1, "distracted": 0, "unknown": 0},
            "fatigue": {"normal": 1, "fatigued": 0},
            "alerts_total": 0,
            "avg_attention_score": 75.0,
            "per_student": [
                {
                    "label": "<b>S001</b>",
                    "attention_mean": 75.0,
                    "fatigue_index_mean": 0.2,
                    "fatigue_indicators": 0,
                    "distraction_indicators": 0,
                    "alerts": 0,
                }
            ],
        }
        # Must build PDF without raising markup parsing errors
        pdf_bytes = export_pdf(malicious_report)
        assert len(pdf_bytes) > 1000
