# Security Testing Guide: Authentication, Authorization and Privacy

> **Scope:** every security check for the backend (FastAPI), Operator Console (web) and Mobile App (Expo).
> **Follows:** `README.md` (D4, D5, D7, D8, section 7 non-negotiables), `contracts.md` (section 3 REST, section 4 WebSocket, section 7 database), `application_behavior.md` (APP-26, APP-27, APP-28), `implementation.md` (phases 14, 21, 25).
> **Use this guide:** after Phase 14 (auth and roles), again after Phase 21 (mobile), and as the final gate in Phase 25. A release is blocked until every **MUST** test passes.

---

## 1. Security rules being tested

| Rule | Source | What it means |
|------|--------|---------------|
| Backend enforces roles on **every** endpoint | APP-26, README section 7 | The UI hiding a button is never enough. |
| Teachers see only their assigned classrooms | CON section 3 | Server-side check, not client-side. |
| No video to mobile | D4, APP-27 | `/ws/video` is never forwarded to mobile. |
| `/ws/video` closed when `PRIVACY_MODE=true` | CON section 4 | Close code **4403**. |
| No raw video, frames or face crops stored | D4 | No BLOB/image columns, no images in logs. |
| No face recognition, anonymous `S001` labels | D5 | No endpoint returns identity inferred from a face. |
| Secrets only in environment variables | README section 7 | None in code, git or logs. |
| Honest, non-diagnostic copy | D8 | No "sleeping", "sick" in any alert or error text. |

---

## 2. Test environment setup

```bash
cd backend
source .venv/bin/activate
pip install pytest pytest-asyncio httpx websockets pip-audit bandit

# Use a throw-away database and test secrets, never production values
export APP_ENV=test
export DATABASE_URL=sqlite:///./test_security.db
export JWT_SECRET=test-secret-change-me-32-bytes-minimum
export PRIVACY_MODE=true
```

### Seed users for tests

Create these accounts in a pytest fixture (never in production):

| Username | Role | Active | Classrooms |
|----------|------|--------|------------|
| `admin1` | `admin` | yes | all |
| `teacherA` | `teacher` | yes | Room A only |
| `teacherB` | `teacher` | yes | Room B only |
| `teacherOff` | `teacher` | **no** (disabled) | Room A |

Create one active session in Room A and one in Room B, plus a few alerts in each.

Helper used in the examples below:

```python
# tests/conftest.py (sketch)
def login(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    return r.json().get("token") or r.json().get("access_token")

def auth(token):
    return {"Authorization": f"Bearer {token}"}
```

Run everything:

```bash
pytest tests/security -v
```

---

## 3. Authentication tests (who are you?)

| # | Test | Request | Expected | Level |
|---|------|---------|----------|-------|
| A1 | Valid login | `POST /auth/login` correct credentials | 200, JWT and `role` returned | MUST |
| A2 | Wrong password | wrong password | 401, generic message | MUST |
| A3 | Unknown user | username does not exist | 401, **same message** as A2 (no user enumeration) | MUST |
| A4 | Disabled account | `teacherOff` logs in | 401 or 403, no token | MUST |
| A5 | Missing token | `GET /auth/me` with no header | 401 | MUST |
| A6 | Malformed token | `Authorization: Bearer abc` | 401 | MUST |
| A7 | Expired token | token with past `exp` | 401 | MUST |
| A8 | Tampered token | change one character of the signature | 401 | MUST |
| A9 | `alg: none` token | unsigned JWT | 401 | MUST |
| A10 | Wrong secret | token signed with another secret | 401 | MUST |
| A11 | Role claim forged | edit payload to `"role":"admin"`, keep old signature | 401 | MUST |
| A12 | Token for deleted/disabled user | valid token, user disabled afterwards | 401 or 403 | SHOULD |
| A13 | Password storage | inspect `users.password_hash` | Hashed (bcrypt/argon2), never plain text | MUST |
| A14 | Login rate limiting | 10+ wrong passwords quickly | 429 or temporary lockout | MUST (Phase 25) |
| A15 | No secrets in responses | read login and error bodies | No hash, no stack trace, no secret | MUST |

```python
def test_wrong_password_and_unknown_user_look_the_same(client):
    a = client.post("/auth/login", json={"username": "admin1", "password": "bad"})
    b = client.post("/auth/login", json={"username": "nobody", "password": "bad"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()                      # A2 + A3: no enumeration

def test_tampered_token_rejected(client, admin_token):
    bad = admin_token[:-2] + ("AA" if not admin_token.endswith("AA") else "BB")
    assert client.get("/auth/me", headers=auth(bad)).status_code == 401
```

Quick manual check with curl:

```bash
curl -i -X POST localhost:8000/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"username":"admin1","password":"WRONG"}'
curl -i localhost:8000/auth/me                       # expect 401
```

---

## 4. Authorization tests (what may you do?)

### 4.1 Role matrix (REST)

Roles: **T** teacher, **A** admin, **none** no token. The expected status is for the role **not** allowed unless stated.

| Endpoint | none | Teacher | Admin | Test |
|----------|------|---------|-------|------|
| `GET /health` | 200 | 200 | 200 | R1 |
| `POST /auth/login` | 200 | 200 | 200 | R2 |
| `GET /auth/me` | 401 | 200 | 200 | R3 |
| `GET /teacher/dashboard` | 401 | 200 | **403** | R4 |
| `GET /classrooms` | 401 | 200 (own only) | 200 | R5 |
| `POST/PUT/DELETE /classrooms` | 401 | **403** | 200 | R6 |
| `GET /classrooms/{id}/students` | 401 | 200 (own only) | 200 | R7 |
| `GET/POST/PUT/DELETE /students` | 401 | **403** | 200 | R8 |
| `POST /students/{id}/assign` | 401 | **403** | 200 | R9 |
| `GET/POST/PUT /teachers` | 401 | **403** | 200 | R10 |
| `POST /sessions` | 401 | 200 (own class) | 200 | R11 |
| `POST /sessions/{id}/stop` | 401 | 200 (own class) | 200 | R12 |
| `GET /sessions`, `/sessions/{id}`, `/sessions/{id}/tracks` | 401 | 200 (own only) | 200 | R13 |
| `GET /students/{id}/status` | 401 | 200 (own only) | 200 | R14 |
| `GET /alerts`, `PATCH /alerts/{id}` | 401 | 200 (own only) | 200 | R15 |
| `GET /reports`, `/reports/{id}`, `/reports/{id}/export` | 401 | 200 (own only) | 200 | R16 |
| `GET /system/status` | 401 | reduced view | full | R17 |

**MUST:** write one parametrized test that loops over every route registered in the app and fails if any route has no auth dependency (other than `/health` and `/auth/login`). That catches routes added later.

```python
import pytest

ADMIN_ONLY = [
    ("POST", "/classrooms"), ("POST", "/students"), ("POST", "/teachers"),
    ("PUT", "/classrooms/1"), ("DELETE", "/students/1"),
]

@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_teacher_cannot_use_admin_routes(client, teacherA_token, method, path):
    r = client.request(method, path, headers=auth(teacherA_token), json={})
    assert r.status_code == 403

@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_anonymous_gets_401(client, method, path):
    assert client.request(method, path, json={}).status_code == 401
```

### 4.2 Teacher-to-classroom isolation (the most important authorization test)

| # | Test | Expected | Level |
|---|------|----------|-------|
| Z1 | `teacherA` reads Room B session `/sessions/{B}` | 403 (or 404, but be consistent) | MUST |
| Z2 | `teacherA` reads Room B tracks, alerts, reports | 403 | MUST |
| Z3 | `teacherA` lists `/alerts` | Only Room A alerts in the list | MUST |
| Z4 | `teacherA` `PATCH /alerts/{id}` on a Room B alert | 403 | MUST |
| Z5 | `teacherA` starts a session in Room B | 403 | MUST |
| Z6 | `teacherA` stops a Room B session | 403 | MUST |
| Z7 | `teacherA` exports a Room B report | 403 | MUST |
| Z8 | `teacherA` subscribes to Room B over `/ws/telemetry` (`{"type":"subscribe","session_id":B}`) | Refused, no Room B data delivered | MUST |
| Z9 | Change IDs in the URL (IDOR): try sequential `id` values | Never returns another classroom's data | MUST |
| Z10 | `teacherA` opens `/students/{id}/status` for a student in Room B | 403 | MUST |

```python
def test_teacher_cannot_read_other_classroom_session(client, teacherA_token, session_B):
    r = client.get(f"/sessions/{session_B}", headers=auth(teacherA_token))
    assert r.status_code in (403, 404)

def test_alert_list_is_scoped(client, teacherA_token):
    data = client.get("/alerts", headers=auth(teacherA_token)).json()
    assert all(a["session_id"] in ROOM_A_SESSIONS for a in data)
```

### 4.3 Input validation and injection

| # | Test | Expected | Level |
|---|------|----------|-------|
| V1 | Invalid body (missing field, wrong type) | 422 with the standard error shape | MUST |
| V2 | SQL injection strings in login, search, path IDs (`' OR 1=1 --`) | 401 or 422, no 500, no data leak | MUST |
| V3 | Invalid `status` in `PATCH /alerts/{id}` (e.g. `"Deleted"`) | 422 | MUST |
| V4 | Invalid `format` in export (`format=exe`) | 422 | MUST |
| V5 | Oversized body (several MB) | 413 or 422, no crash | SHOULD |
| V6 | Mass assignment: teacher sends `"role":"admin"` in a profile update | Field ignored or 403 | MUST |
| V7 | Error responses use `{ "error": { "code", "message" } }` and contain no stack trace, file path or SQL | Pass | MUST |
| V8 | Alert status transitions: `Resolved` back to `New` | Rejected | SHOULD |

---

## 5. WebSocket security tests

| # | Test | Expected | Level |
|---|------|----------|-------|
| W1 | `/ws/telemetry` without token | Connection refused | MUST |
| W2 | `/ws/telemetry` with expired or tampered token | Refused | MUST |
| W3 | `/ws/telemetry` with a valid token | Accepted; `ping` returns `pong` | MUST |
| W4 | `/ws/video` with `PRIVACY_MODE=true` | Closed with code **4403** | MUST |
| W5 | `/ws/video` with `PRIVACY_MODE=false` and a valid teacher/admin token | Accepted | MUST |
| W6 | `/ws/video` without a token, even with privacy off | Refused | MUST |
| W7 | Telemetry payload sent to mobile contains only `TrackResult-lite` fields | No landmarks, no emotion probabilities, no image data | MUST |
| W8 | Telemetry never contains `jpeg_b64` or any image field | Pass | MUST |
| W9 | Mobile-origin client tries `/ws/video` | Never forwarded; refused | MUST |
| W10 | Message flood (hundreds of messages per second) | Server stays up; connection throttled or closed | SHOULD |
| W11 | Malformed JSON over the socket | Ignored or closed cleanly, no crash | MUST |
| W12 | Token revoked or user disabled while connected | Connection closes at next check, or at least on reconnect | SHOULD |

```python
def test_video_socket_closed_in_privacy_mode(client, admin_token):
    with pytest.raises(Exception) as e:
        with client.websocket_connect(f"/ws/video?token={admin_token}"):
            pass
    assert "4403" in str(e.value)

def test_telemetry_has_no_image_fields(client, teacherA_token):
    with client.websocket_connect(f"/ws/telemetry?token={teacherA_token}") as ws:
        msg = ws.receive_json()
        text = str(msg)
        assert "jpeg_b64" not in text and "landmark" not in text
```

> **Note:** the contract passes the token in the query string (`?token=`). URLs are often logged by proxies, so test S5 below must confirm tokens never appear in logs.

---

## 6. Privacy and data-protection tests

| # | Test | How | Level |
|---|------|-----|-------|
| P1 | No image or BLOB columns | Inspect schema: no `BLOB`, `LargeBinary`, `bytea`, no `image` or `frame` columns | MUST |
| P2 | No frames or face crops on disk | Run a 5-minute session, then search the project and temp folders for `.jpg`, `.png`, `.mp4`, `.npy` created during the run | MUST |
| P3 | No images in logs | Grep logs for `jpeg_b64`, `base64`, `data:image` | MUST |
| P4 | Anonymous identity | API responses expose `S001`-style labels only, never a face-derived identity (D5) | MUST |
| P5 | Mobile gets no video | Mobile code and traffic contain no calls to `/ws/video` | MUST |
| P6 | Retention job | Rows older than `RETENTION_DAYS` are deleted by the job | SHOULD |
| P7 | Reports carry the disclaimer footer | CSV/PDF text includes "not a diagnosis or disciplinary record" | MUST |
| P8 | Alert and UI copy is non-diagnostic | Search all alert messages for "sleeping", "sick", "lazy", "misbehaving" | MUST |

```bash
# P1: schema check (SQLite example)
sqlite3 test_security.db ".schema" | grep -iE "blob|image|frame|jpeg" && echo "FAIL" || echo "PASS"

# P2/P3: leftover images and image data in logs
find . -newer tests/.run_start \( -name "*.jpg" -o -name "*.png" -o -name "*.mp4" \) 
grep -riE "jpeg_b64|data:image|base64," logs/ && echo "FAIL" || echo "PASS"
```

---

## 7. Secrets, configuration and transport

| # | Test | Expected | Level |
|---|------|----------|-------|
| S1 | Search the repo for hard-coded secrets (`JWT_SECRET`, passwords, API keys) | None | MUST |
| S2 | `.env` is git-ignored; `.env.example` has placeholders only | Pass | MUST |
| S3 | App refuses to start in production with a missing or default JWT secret | Startup error | MUST |
| S4 | Default config is secure: `PRIVACY_MODE=true`, debug off | Pass | MUST |
| S5 | Tokens, passwords and `Authorization` headers never appear in logs | Grep logs after a test run | MUST |
| S6 | CORS allow-list contains only the known web origin, not `*`, in production | Check response headers | MUST |
| S7 | TLS in production (HTTPS and `wss://`) | HTTP redirects or is refused | MUST |
| S8 | Security headers on web responses (`X-Content-Type-Options`, `Strict-Transport-Security`, a Content-Security-Policy) | Present | SHOULD |
| S9 | JWT lifetime is reasonable and configurable | Pass | SHOULD |
| S10 | Docker image runs as a non-root user, no secrets baked into the image | Check `Dockerfile` and `docker history` | SHOULD |

```bash
# S1: quick secret scan (works without extra tools)
grep -rnE "(secret|password|api[_-]?key|token)\s*=\s*['\"][^'\"]{6,}" \
     --include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" \
     --exclude-dir=node_modules --exclude-dir=.venv . 

# S6: CORS check
curl -i -H "Origin: https://evil.example" localhost:8000/health | grep -i access-control
```

---

## 8. Dependency and static analysis

```bash
# Python
pip-audit -r requirements.txt            # known vulnerable packages
bandit -r app ai -ll                     # insecure code patterns (medium and above)

# Web console and mobile
cd ../operator-console && npm audit --omit=dev
cd ../mobile            && npm audit --omit=dev
```

| # | Test | Pass condition |
|---|------|----------------|
| D1 | `pip-audit` | No unresolved high or critical findings |
| D2 | `bandit` | No medium or high issues left unexplained |
| D3 | `npm audit` (both apps) | No unresolved high or critical findings |
| D4 | Model licenses checked (`MANIFEST.json`, OQ-4) | Recorded and approved before production |

---

## 9. Web console (Operator Console) checks

| # | Test | Expected | Level |
|---|------|----------|-------|
| C1 | Open a protected page without logging in | Redirected to login | MUST |
| C2 | Teacher opens an admin-only page by typing the URL | Access denied page, and the API calls behind it return 403 | MUST |
| C3 | Logout clears the token | Back button does not reveal data; API calls return 401 | MUST |
| C4 | Token storage | Not in a place readable by third-party scripts if avoidable; never printed to the console | SHOULD |
| C5 | No `dangerouslySetInnerHTML` with API data | Search the code base | MUST |
| C6 | Privacy mode on | Live grid shows the "Video disabled (privacy mode)" tiles, no video requests in the network tab | MUST |
| C7 | Source maps and debug tools off in the production build | Pass | SHOULD |

---

## 10. Mobile app checks

| # | Test | Expected | Level |
|---|------|----------|-------|
| M1 | Token stored in secure storage (`expo-secure-store`), not AsyncStorage or plain files | Verify in code and on device | MUST |
| M2 | Role-based navigation: a teacher cannot reach admin screens | Screens not reachable; the API also returns 403 | MUST |
| M3 | Logout clears secure storage and closes sockets | Pass | MUST |
| M4 | Expired token during use | App returns to login, no data left on screen | MUST |
| M5 | No video or face imagery anywhere in the app (D4) | Pass | MUST |
| M6 | Failed login message matches APP-25 and does not reveal which part was wrong | Pass | MUST |
| M7 | Production build uses `https://` and `wss://` only | Pass | MUST |
| M8 | Push notification content has no student names or sensitive detail | Class-level text only | MUST |
| M9 | Screens with sensitive data are not captured in the app switcher (optional hardening) | Pass | NICE |

---

## 11. Reporting results

For each test run, append to `docs/PROGRESS.md`:

```markdown
## Security test run: <date>
- Status: PASS | FAIL | BLOCKED
- Tests run: A1-A15, R1-R17, Z1-Z10, V1-V8, W1-W12, P1-P8, S1-S10, D1-D4, C1-C7, M1-M9
- Failures: <test id, expected, actual>
- Accepted risks (with owner approval): ...
- Tools and versions: pytest ..., pip-audit ..., bandit ..., npm audit ...
```

### Severity and release rule

| Severity | Examples | Rule |
|----------|----------|------|
| **Critical** | Auth bypass, teacher reads another classroom (Z1-Z10), video reaches mobile (W9, P5), images stored (P1-P3) | Fix before anything else; release blocked |
| **High** | Missing role check on one route, token in logs, default secret accepted | Release blocked |
| **Medium** | Missing rate limit, missing security headers | Fix before production, or record an accepted risk |
| **Low** | Cosmetic or hardening items | Track in `OPEN_QUESTIONS.md` |

---

## 12. Final security gate (Phase 25 checklist)

- [ ] All **MUST** tests in sections 3 to 10 pass.
- [ ] The "every route has an auth dependency" test passes.
- [ ] Z1 to Z10 (teacher isolation) pass, including the WebSocket subscribe test.
- [ ] `/ws/video` returns 4403 in privacy mode and is never reachable from mobile.
- [ ] No images in the database, on disk or in logs.
- [ ] No secrets in the repository, image or logs; production refuses to start without them.
- [ ] `pip-audit`, `bandit` and `npm audit` are clean or each finding is documented.
- [ ] Rate limiting on login is active.
- [ ] Privacy notice and consent checklist completed (OQ-5).
- [ ] Results recorded in `docs/PROGRESS.md`.

> These tests cover the application. For a real deployment, also have someone independent perform a penetration test and review the network setup (firewall, TLS certificates, database access).
