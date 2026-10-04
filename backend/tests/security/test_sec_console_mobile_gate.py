"""Security Tests — Sections 9–10 & 12: Web Console, Mobile, Final Gate (C1–C7, M1–M9, Gate).

Tests cover:
  C1  Protected web routes redirect to login (source-level check).
  C2  Admin-only screens protected by role check in source.
  C5  No dangerouslySetInnerHTML with API data in web console.
  C6  Privacy mode: no video requests in operator console code.
  M1  Token in mobile uses SecureStore, not AsyncStorage.
  M2  Role-based navigation: teacher cannot reach admin screens.
  M5  No video/face imagery in mobile (D4).
  M6  Login error message is generic (no enumeration).
  M8  Push notification content class-level only (no student names).
  GATE  Final Phase 25 checklist: all non-negotiables verified.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
MOBILE = ROOT / "mobile"
OPERATOR = ROOT / "operator-console"



class TestWebConsole:
    """Section 9: Operator Console (web) checks C1–C7."""

    # C1 — Protected pages behind auth guard in source
    def test_C1_protected_routes_use_auth_guard(self):
        """Web console routes must use an auth guard / PrivateRoute pattern."""
        if not OPERATOR.exists():
            pytest.skip("operator-console not found")
        src = OPERATOR / "src"
        if not src.exists():
            pytest.skip("operator-console/src not found")

        # Look for auth guard patterns in route definitions
        auth_patterns = [
            r"PrivateRoute", r"RequireAuth", r"isAuthenticated", r"useAuth", r"AuthGuard",
            r"token\s*&&", r"isLoggedIn", r"protected", r"authContext",
        ]
        pattern = re.compile("|".join(auth_patterns), re.I)

        auth_guard_found = False
        for fpath in src.rglob("*.tsx"):
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                auth_guard_found = True
                break
        for fpath in src.rglob("*.ts"):
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                auth_guard_found = True
                break

        assert auth_guard_found, (
            "No auth guard found in operator-console — protected routes may be exposed!"
        )

    # C2 — Admin-only screens protected
    def test_C2_admin_screens_role_protected(self):
        """Admin screens must check role before rendering."""
        if not OPERATOR.exists():
            pytest.skip("operator-console not found")
        src = OPERATOR / "src"
        if not src.exists():
            pytest.skip("operator-console/src not found")

        role_patterns = [r"role\s*===\s*['\"]admin['\"]", r"isAdmin", r"role.*admin", r"admin.*role"]
        pattern = re.compile("|".join(role_patterns), re.I)
        found = any(
            pattern.search(fpath.read_text(encoding="utf-8", errors="ignore"))
            for fpath in list(src.rglob("*.tsx")) + list(src.rglob("*.ts"))
        )
        assert found, "No admin role check found in operator-console source"

    # C5 — No dangerouslySetInnerHTML with API data
    def test_C5_no_dangerous_inner_html_with_api_data(self):
        """dangerouslySetInnerHTML must not be used with user/API-supplied data."""
        if not OPERATOR.exists():
            pytest.skip("operator-console not found")
        src = OPERATOR / "src"
        if not src.exists():
            pytest.skip("operator-console/src not found")

        # Look for dangerouslySetInnerHTML — if found, flag as warning (not auto-pass)
        dangerous_pattern = re.compile(r"dangerouslySetInnerHTML", re.I)
        violations = []
        for fpath in list(src.rglob("*.tsx")) + list(src.rglob("*.ts")):
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if dangerous_pattern.search(text):
                violations.append(str(fpath.relative_to(ROOT)))

        assert not violations, (
            f"dangerouslySetInnerHTML found — verify no API data is injected: {violations}"
        )

    # C6 — No video requests in operator console when privacy mode is default-on
    def test_C6_privacy_mode_no_unconditional_video_calls(self):
        """Operator console video calls must be guarded by privacy mode check."""
        if not OPERATOR.exists():
            pytest.skip("operator-console not found")
        src = OPERATOR / "src"
        if not src.exists():
            pytest.skip("operator-console/src not found")

        for fpath in list(src.rglob("*.tsx")) + list(src.rglob("*.ts")):
            if fpath.name == "config.ts":
                continue
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if "ws/video" in text or "/ws/video" in text or "WS_VIDEO_URL" in text:
                assert "privacy" in text.lower() or "PRIVACY" in text or "privacyMode" in text, (
                    f"{fpath.relative_to(ROOT)}: video stream used without privacy mode check!"
                )


class TestMobileApp:
    """Section 10: Mobile app checks M1–M9."""

    # M1 — Token stored in SecureStore, not AsyncStorage
    def test_M1_token_uses_secure_store_not_async_storage(self):
        """Mobile token storage must use expo-secure-store, not plain AsyncStorage."""
        if not MOBILE.exists():
            pytest.skip("mobile not found")
        src = MOBILE / "src"
        if not src.exists():
            pytest.skip("mobile/src not found")

        secure_store_found = False
        async_storage_for_token = False

        for fpath in list(src.rglob("*.ts")) + list(src.rglob("*.tsx")):
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if "SecureStore" in text or "expo-secure-store" in text:
                secure_store_found = True
            # Flag if AsyncStorage is used for something that looks like a token
            if "AsyncStorage" in text and (
                "token" in text.lower() or "jwt" in text.lower() or "access_token" in text
            ):
                async_storage_for_token = True

        assert secure_store_found, (
            "M1: expo-secure-store not found in mobile code — token may be stored insecurely!"
        )
        assert not async_storage_for_token, (
            "M1: AsyncStorage appears to be used for token storage — use expo-secure-store instead!"
        )

    # M2 — Role-based navigation in mobile
    def test_M2_role_based_navigation_in_mobile(self):
        """Mobile must restrict admin screens from teachers."""
        if not MOBILE.exists():
            pytest.skip("mobile not found")
        src = MOBILE / "src"
        if not src.exists():
            pytest.skip("mobile/src not found")

        role_patterns = [r"role\s*===\s*['\"]admin['\"]", r"isAdmin", r"role.*admin"]
        pattern = re.compile("|".join(role_patterns), re.I)
        found = any(
            pattern.search(fpath.read_text(encoding="utf-8", errors="ignore"))
            for fpath in list(src.rglob("*.tsx")) + list(src.rglob("*.ts"))
        )
        assert found, "M2: No role-based navigation guard found in mobile source"

    # M5 — No video or face imagery in mobile (D4)
    def test_M5_mobile_has_no_video_face_imagery(self):
        """Mobile must not reference video stream endpoints, video cameras, or face crops."""
        if not MOBILE.exists():
            pytest.skip("mobile not found")
        src = MOBILE / "src"
        if not src.exists():
            pytest.skip("mobile/src not found")

        forbidden = [r"/ws/video", r"ws/video", r"face_crop", r"jpeg_b64", r"expo-camera"]
        pattern = re.compile("|".join(forbidden), re.I)
        violations = []
        for fpath in list(src.rglob("*.tsx")) + list(src.rglob("*.ts")):
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                violations.append(str(fpath.relative_to(ROOT)))

        assert not violations, f"M5/D4 VIOLATION — Video/face imagery in mobile: {violations}"

    # M6 — Mobile login error is generic (no enumeration)
    def test_M6_mobile_login_error_is_generic(self):
        """Mobile must show a generic login error, not reveal 'wrong password' vs 'no user'."""
        if not MOBILE.exists():
            pytest.skip("mobile not found")
        src = MOBILE / "src"
        if not src.exists():
            pytest.skip("mobile/src not found")

        # Check for specific discriminating error messages (revealing account existence)
        bad_patterns = [r"user.*not.*found", r"user.*does.*not.*exist", r"incorrect.*password", r"password.*incorrect"]
        bad_re = re.compile("|".join(bad_patterns), re.I)
        violations = []
        for fpath in list(src.rglob("*.tsx")) + list(src.rglob("*.ts")):
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                if bad_re.search(line):
                    violations.append(f"{fpath.relative_to(ROOT)}:{lineno}: {line.strip()}")

        assert not violations, (
            f"M6: Discriminating login error messages found:\n" + "\n".join(violations)
        )

    # M8 — Push notification body is class-level only
    def test_M8_push_notification_content_class_level_only(self):
        """Advisory push notifications must contain class-level text only — no student names/IDs."""
        if not BACKEND.exists():
            pytest.skip("backend not found")

        # Check advisory engine push payload does not include student-level fields
        advisory_engine = BACKEND / "app" / "advisory" / "engine.py"
        if not advisory_engine.exists():
            pytest.skip("advisory engine not found")

        text = advisory_engine.read_text(encoding="utf-8", errors="ignore")
        # The push payload should NOT contain student_id, track_id, student_name, etc.
        bad_patterns = ["student_id", "student_name", "track_id", "person_name", "face_id"]
        push_section_start = text.find("push_payload") if "push_payload" in text else -1
        if push_section_start == -1:
            push_section_start = text.find("notification") if "notification" in text else 0

        relevant = text[push_section_start:push_section_start + 500]
        for bp in bad_patterns:
            assert bp not in relevant, (
                f"M8: Push notification payload contains student-level field '{bp}'"
            )


class TestSecurityGate:
    """Section 12: Final security gate — Phase 25 checklist."""

    def test_GATE_no_routes_without_auth_dependency(self):
        """MUST: Every route other than /health and /auth/* must have an auth dependency."""
        from app.main import app as fastapi_app

        OPEN_PATHS = {"/health", "/auth/login", "/auth/me", "/docs", "/openapi.json", "/redoc", "/ws/telemetry", "/ws/video"}

        violations = []
        for route in fastapi_app.routes:
            path = getattr(route, "path", "")
            if path in OPEN_PATHS or path.startswith("/auth/"):
                continue
            if not hasattr(route, "dependencies"):
                continue
            endpoint = getattr(route, "endpoint", None)
            if endpoint is None:
                continue
            module = getattr(endpoint, "__module__", "")
            source_file = None
            try:
                import inspect
                source_file = inspect.getfile(endpoint)
            except (TypeError, OSError):
                pass

            if source_file:
                try:
                    source = open(source_file, encoding="utf-8").read()
                    has_auth = any(
                        kw in source for kw in (
                            "get_current_user", "require_admin", "require_teacher",
                            "require_teacher_or_admin", "Depends(get_current_user)"
                        )
                    )
                    if not has_auth:
                        violations.append(f"{path} ({source_file})")
                except OSError:
                    pass

        assert not violations, (
            f"Routes without auth dependency detected:\n" + "\n".join(violations)
        )

    def test_GATE_privacy_mode_default_true(self):
        """PRIVACY_MODE must default to True — non-negotiable SYS-10."""
        from app.config import Settings
        assert Settings().PRIVACY_MODE is True

    def test_GATE_no_images_in_schema(self):
        """Database schema must be free of image/BLOB columns — non-negotiable D4."""
        from app.db.models import Base
        from sqlalchemy import create_engine, inspect as sa_inspect

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        inspector = sa_inspect(engine)

        forbidden_types = re.compile(r"blob|image|bytea|largebinary|jpeg|photo", re.I)
        forbidden_names = re.compile(r"^(image|photo|jpeg|face_crop|embedding|pixel|frame_data|raw_frame|video_frame)$", re.I)
        violations = []
        for t in inspector.get_table_names():
            for c in inspector.get_columns(t):
                if forbidden_types.search(str(c["type"])) or forbidden_names.search(c["name"]):
                    violations.append(f"{t}.{c['name']}")
        assert not violations, f"CRITICAL: Image/BLOB columns in schema: {violations}"


    def test_GATE_privacy_notice_exists(self):
        """Privacy consent policy checklist must exist (OQ-5)."""
        privacy_doc = ROOT / "docs" / "PRIVACY_CONSENT_POLICY.md"
        assert privacy_doc.exists(), (
            f"Missing: docs/PRIVACY_CONSENT_POLICY.md — required by OQ-5"
        )
        text = privacy_doc.read_text(encoding="utf-8", errors="ignore")
        assert len(text) > 100, "PRIVACY_CONSENT_POLICY.md appears empty"

    def test_GATE_deployment_doc_references_tls(self):
        """DEPLOYMENT.md must mention TLS/HTTPS (S7)."""
        deploy_doc = ROOT / "docs" / "DEPLOYMENT.md"
        if not deploy_doc.exists():
            pytest.skip("DEPLOYMENT.md not found")
        text = deploy_doc.read_text(encoding="utf-8", errors="ignore").lower()
        assert any(kw in text for kw in ("tls", "https", "wss", "ssl")), (
            "DEPLOYMENT.md must reference TLS/HTTPS for production (S7)"
        )

    def test_GATE_model_licenses_approved(self):
        """Model licenses must be recorded and approved (D4, OQ-4)."""
        manifest = BACKEND / "models" / "MANIFEST.json"
        if not manifest.exists():
            pytest.skip("MANIFEST.json not found")
        text = manifest.read_text(encoding="utf-8", errors="ignore").lower()
        assert "license" in text
        assert any(lic in text for lic in ("apache", "mit", "bsd"))
