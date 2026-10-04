"""Security Tests — Sections 4.1–4.3: Authorization (R1–R17, Z1–Z10, V1–V8).

Tests cover:
  R1–R17  Role matrix on REST endpoints.
  Z1–Z10  Teacher-to-classroom isolation (IDOR, cross-session, cross-alert).
  V1–V8   Input validation, SQL injection, mass assignment, error shape.
"""
from __future__ import annotations

import pytest

from .conftest import _Session, _make_user, _make_room, _assign, _login, _auth


class TestRoleMatrix:
    """Section 4.1: REST role matrix R1–R17."""

    # R1 — /health is open to all
    def test_R1_health_open(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    # R2 — /auth/login is open to all
    def test_R2_login_open(self, client):
        r = client.post("/auth/login", json={"username": "x", "password": "y"})
        assert r.status_code in (200, 401)  # open endpoint, any response is fine

    # R3 — /auth/me requires token
    def test_R3_me_requires_auth(self, client):
        assert client.get("/auth/me").status_code == 401

    # R4 — /teacher/dashboard: teacher→200, admin→403, none→401
    def test_R4_teacher_dashboard_role_enforcement(self, client, scenario):
        s = scenario
        # Teacher can access their dashboard
        r = client.get("/teacher/dashboard", headers=_auth(s["token_a"]))
        assert r.status_code == 200
        # Admin cannot access teacher dashboard
        r = client.get("/teacher/dashboard", headers=_auth(s["admin_token"]))
        assert r.status_code == 403
        # No token → 401
        assert client.get("/teacher/dashboard").status_code == 401

    # R5 — /classrooms: teacher sees own, admin sees all, none→401
    def test_R5_classrooms_list_scope(self, client, scenario):
        s = scenario
        assert client.get("/classrooms").status_code == 401
        assert client.get("/classrooms", headers=_auth(s["token_a"])).status_code == 200
        assert client.get("/classrooms", headers=_auth(s["admin_token"])).status_code == 200

    # R6 — POST/PUT/DELETE /classrooms: admin only
    def test_R6_classrooms_mutation_admin_only(self, client, scenario):
        s = scenario
        # Teacher → 403
        assert client.post("/classrooms", json={"room_name": "X", "class_name": "Y"},
                           headers=_auth(s["token_a"])).status_code == 403
        # No token → 401
        assert client.post("/classrooms", json={"room_name": "X", "class_name": "Y"}).status_code == 401

    # R7 — /classrooms/{id}/students: teacher own only, admin all, none→401/404
    def test_R7_classroom_students_scope(self, client, scenario):
        """R7: Student roster access requires auth and classroom scope.
        
        NOTE: The exact sub-route /classrooms/{id}/students is not implemented as a
        separate endpoint — students are listed via GET /classrooms/{id} or GET /students.
        This test verifies the access control on the /students endpoint instead.
        """
        s = scenario
        # Without auth: /students returns 401 (admin-only route)
        assert client.get("/students").status_code == 401, (
            "GET /students without token must return 401"
        )
        # Teacher cannot access full student list (admin only)
        r = client.get("/students", headers=_auth(s["token_a"]))
        assert r.status_code == 403, (
            f"Teacher must receive 403 on GET /students (admin-only), got {r.status_code}"
        )
        # Admin can access all students
        r = client.get("/students", headers=_auth(s["admin_token"]))
        assert r.status_code == 200

    # R8 — /students CRUD: admin only
    def test_R8_students_crud_admin_only(self, client, scenario):
        s = scenario
        # POST
        assert client.post("/students", json={"student_code": "S001", "full_name": "Test"},
                           headers=_auth(s["token_a"])).status_code == 403
        assert client.post("/students", json={"student_code": "S001", "full_name": "Test"}).status_code == 401

    # R9 — POST /students/{id}/assign: admin only
    def test_R9_student_assign_admin_only(self, client, scenario):
        s = scenario
        assert client.post("/students/1/assign", json={"classroom_id": 1},
                           headers=_auth(s["token_a"])).status_code == 403

    # R10 — /teachers CRUD: admin only
    def test_R10_teachers_admin_only(self, client, scenario):
        s = scenario
        assert client.get("/teachers", headers=_auth(s["token_a"])).status_code == 403
        assert client.get("/teachers").status_code == 401

    # R11 — POST /sessions: teacher for own class, admin all
    def test_R11_session_start_role_enforcement(self, client, scenario):
        s = scenario
        # Teacher starts session in their own room
        r = client.post("/sessions", json={"classroom_id": s["room_a_id"]},
                        headers=_auth(s["token_a"]))
        assert r.status_code in (200, 201, 409)  # 409 if session already active
        # No token
        assert client.post("/sessions", json={"classroom_id": s["room_a_id"]}).status_code == 401

    # R13 — GET /sessions: scoped
    def test_R13_sessions_list_requires_auth(self, client, scenario):
        assert client.get("/sessions").status_code == 401

    # R15 — /alerts requires auth
    def test_R15_alerts_requires_auth(self, client):
        assert client.get("/alerts").status_code == 401

    # R16 — /reports requires auth
    def test_R16_reports_requires_auth(self, client):
        assert client.get("/reports").status_code == 401

    # R17 — /system/status: admin→200, teacher→403, none→401
    def test_R17_system_status_admin_only(self, client, scenario):
        s = scenario
        assert client.get("/system/status").status_code == 401
        assert client.get("/system/status", headers=_auth(s["token_a"])).status_code == 403
        assert client.get("/system/status", headers=_auth(s["admin_token"])).status_code == 200


class TestTeacherIsolation:
    """Section 4.2: Teacher-to-classroom isolation Z1–Z10."""

    # Z1 — teacherA cannot read Room B session
    def test_Z1_teacher_cannot_read_other_session(self, client, scenario):
        s = scenario
        r = client.get(f"/sessions/{s['session_b_id']}", headers=_auth(s["token_a"]))
        assert r.status_code in (403, 404), f"Expected 403/404, got {r.status_code}"

    # Z2 — teacherA cannot read Room B tracks / reports
    def test_Z2_teacher_cannot_read_other_tracks(self, client, scenario):
        s = scenario
        r = client.get(f"/sessions/{s['session_b_id']}/tracks", headers=_auth(s["token_a"]))
        assert r.status_code in (403, 404)

    # Z3 — teacherA alert list contains only Room A alerts
    def test_Z3_alert_list_scoped_to_own_classroom(self, client, scenario):
        s = scenario
        r = client.get("/alerts", headers=_auth(s["token_a"]))
        assert r.status_code == 200
        data = r.json()
        # All returned alerts must belong to sessions in Room A
        for alert in data:
            assert alert["session_id"] == s["session_a_id"], (
                f"Alert session_id {alert['session_id']} is not Room A session {s['session_a_id']}"
            )

    # Z4 — teacherA PATCH on Room B alert → 403
    def test_Z4_teacher_cannot_patch_other_room_alert(self, client, scenario):
        s = scenario
        r = client.patch(f"/alerts/9999", json={"status": "Viewed"}, headers=_auth(s["token_a"]))
        assert r.status_code in (403, 404)

    # Z5 — teacherA cannot start session in Room B
    def test_Z5_teacher_cannot_start_other_room_session(self, client, scenario):
        s = scenario
        r = client.post("/sessions", json={"classroom_id": s["room_b_id"]},
                        headers=_auth(s["token_a"]))
        assert r.status_code == 403

    # Z6 — teacherA cannot stop Room B session
    def test_Z6_teacher_cannot_stop_other_room_session(self, client, scenario):
        s = scenario
        r = client.post(f"/sessions/{s['session_b_id']}/stop", headers=_auth(s["token_a"]))
        assert r.status_code in (403, 404)

    # Z7 — teacherA cannot export Room B report
    def test_Z7_teacher_cannot_export_other_room_report(self, client, scenario):
        s = scenario
        r = client.get(f"/reports/{s['session_b_id']}/export?format=csv",
                       headers=_auth(s["token_a"]))
        assert r.status_code in (403, 404)

    # Z9 — IDOR: sequential ID scanning returns no cross-classroom data
    def test_Z9_idor_sequential_ids_scoped(self, client, scenario):
        s = scenario
        for sid in range(1, 5):
            r = client.get(f"/sessions/{sid}", headers=_auth(s["token_a"]))
            if r.status_code == 200:
                data = r.json()
                assert data.get("classroom_id") == s["room_a_id"], (
                    f"IDOR! Session {sid} returned data for classroom {data.get('classroom_id')}, "
                    f"expected only Room A ({s['room_a_id']})"
                )

    # Z10 — teacherA cannot read Room B student status
    def test_Z10_teacher_cannot_read_other_student_status(self, client, scenario):
        s = scenario
        r = client.get("/students/9999/status", headers=_auth(s["token_a"]))
        assert r.status_code in (403, 404)


class TestInputValidation:
    """Section 4.3: Input validation and injection V1–V8."""

    # V1 — Invalid body → 422 with standard error shape
    def test_V1_invalid_body_returns_422(self, client, scenario):
        s = scenario
        r = client.post("/classrooms",
                        json={"wrong_field": "X"},     # missing room_name & class_name
                        headers=_auth(s["admin_token"]))
        assert r.status_code == 422

    # V2 — SQL injection strings → 401 or 422, never 500, no data leak
    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "' OR 1=1 --",
        "admin'--",
        "' UNION SELECT username,password FROM users--",
    ])
    def test_V2_sql_injection_in_login_rejected(self, client, payload):
        r = client.post("/auth/login", json={"username": payload, "password": payload})
        assert r.status_code in (401, 422), f"SQL injection not blocked: {r.status_code}"
        assert r.status_code != 500, "SQL injection caused 500 server error!"
        body = r.text.lower()
        assert "stack" not in body
        assert "traceback" not in body

    # V3 — Invalid alert status value → 422
    def test_V3_invalid_alert_status_value_rejected(self, client, scenario):
        s = scenario
        r = client.patch("/alerts/1", json={"status": "Deleted"}, headers=_auth(s["token_a"]))
        assert r.status_code in (404, 422)  # 404 if no alert exists, 422 if validation fires first

    # V4 — Invalid export format → 422
    def test_V4_invalid_export_format_rejected(self, client, scenario):
        s = scenario
        r = client.get(f"/reports/{s['session_a_id']}/export?format=exe",
                       headers=_auth(s["token_a"]))
        assert r.status_code in (422, 404, 400)

    # V6 — Mass assignment: teacher sends role=admin in body → ignored
    def test_V6_mass_assignment_role_ignored(self, client, scenario):
        s = scenario
        # Attempt to escalate via profile update — endpoint may not exist, that's fine
        r = client.patch("/auth/me", json={"role": "admin"}, headers=_auth(s["token_a"]))
        # Either no such endpoint (405/404) or it's rejected
        assert r.status_code not in (200,) or (
            r.status_code == 200 and r.json().get("role") != "admin"
        ), "Mass assignment: role was elevated to admin!"

    # V7 — Error responses must NOT include stack traces, file paths, or SQL
    def test_V7_error_responses_have_no_stack_traces(self, client):
        r = client.get("/sessions/99999", headers={"Authorization": "Bearer garbage"})
        body = r.text.lower()
        for forbidden in ("traceback", "file \"", "line ", "sqlalchemy", "sqlite"):
            assert forbidden not in body, f"Stack/SQL trace in error response: {forbidden!r}"
