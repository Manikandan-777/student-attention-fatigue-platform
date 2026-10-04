# Additional Security Checks (beyond login, roles and privacy)

> **Companion to:** `README_SECURITY_TESTING.md`. That file covers authentication, role/classroom authorization, WebSocket tokens, privacy basics, secrets and dependency scans. **This file covers everything else.** Do not repeat tests from that file here.
> **Follows:** `README.md` (D4, D5, D7, D8, section 7), `contracts.md`, `application_behavior.md`, `implementation.md` (phases 12, 14, 24, 25).
> **Levels:** **MUST** = release blocked if it fails. **SHOULD** = fix before production or record an accepted risk. **NICE** = hardening.

---

## 1. What is already covered vs. what this file adds

| Already in `README_SECURITY_TESTING.md` | Added here |
|------------------------------------------|------------|
| Login, JWT tampering, expiry | Session lifecycle, token revocation, password policy, bootstrap admin |
| Role matrix, teacher/classroom isolation | Role changes while connected, roster-mapping re-identification risk |
| WebSocket token, 4403, no images to mobile | Cross-site WebSocket hijacking, connection limits, replay |
| No image columns, no secrets, `pip-audit` | Camera/RTSP security, model supply chain, DB hardening |
| Basic input validation | Export/CSV injection, file download safety, API surface hardening |
| | DoS/resource abuse, audit logging, infrastructure, mobile hardening, process and legal |

---

## 2. Threat model first (do this before testing)

Write a one-page threat model in `docs/THREAT_MODEL.md`. Use STRIDE per component and tick off each row with a test ID from these two guides.

| Component | Spoofing | Tampering | Repudiation | Info disclosure | Denial of service | Elevation of privilege |
|-----------|----------|-----------|-------------|-----------------|-------------------|------------------------|
| Camera / RTSP feed | fake camera feed | altered frames | no log of source | stream credentials leak | feed flood | n/a |
| AI worker | fake worker heartbeat | model file swap | n/a | model/log leak | GPU/CPU exhaustion | n/a |
| FastAPI backend | stolen token | request tampering | missing audit trail | verbose errors | request flood | role bypass |
| WebSocket | token reuse | message injection | n/a | video/telemetry leak | connection flood | subscribe to other class |
| Database | n/a | row edits | no change history | data dump | disk fill | over-privileged DB user |
| Web console / Mobile | phishing, stolen device | local storage edits | n/a | local data cache | n/a | client-side role bypass |

**Pass condition (MUST):** every cell is either mitigated, covered by a named test, or recorded as an accepted risk.

---

## 3. Session management

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| SM1 | Logout invalidates the token server-side (deny-list) or tokens are short-lived with refresh | Old token no longer works after logout | MUST |
| SM2 | Access token lifetime is short (for example 15-60 min); refresh token, if used, is rotated | Verified in config | SHOULD |
| SM3 | Password change invalidates existing tokens | Old token returns 401 | SHOULD |
| SM4 | Admin disables a teacher: existing tokens and sockets stop working | 401/403 on next call, socket closed | MUST |
| SM5 | Admin removes a teacher from a classroom while that teacher is connected | Telemetry for that room stops; REST returns 403 | MUST |
| SM6 | Same token used from many IPs at once | Logged; optional alert | NICE |
| SM7 | Token is not accepted after server secret rotation | 401 | SHOULD |
| SM8 | Token carries only needed claims (id, role, exp), no personal data | Decode and inspect | MUST |

---

## 4. Account and password hygiene

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| PW1 | No default or demo credentials (`admin/admin`, seed users) in production | None exist | MUST |
| PW2 | The first admin is created by a one-time setup step using an env-provided password, not a hard-coded one | Verified | MUST |
| PW3 | Password policy: minimum length (12+), blocks common passwords | Weak password rejected with 422 | SHOULD |
| PW4 | Hash uses bcrypt/argon2 with a work factor; each hash has a unique salt | Inspect two identical passwords: hashes differ | MUST |
| PW5 | Account lockout or progressive delay after repeated failures (per username **and** per IP) | 429 or timed lock | MUST |
| PW6 | Lockout cannot be abused to lock out the admin permanently | Admin recovery path documented | SHOULD |
| PW7 | No password reset that reveals whether an account exists | Same response for known/unknown users | SHOULD |
| PW8 | Teacher accounts can be disabled and re-enabled by admin only | Teacher call returns 403 | MUST |
| PW9 | Passwords never appear in logs, URLs, error messages or API responses | Grep logs and responses | MUST |

---

## 5. Camera and video-source security

The `cameras` table stores `source_uri`. RTSP URLs often contain `user:password@host`, so that field is sensitive.

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| CAM1 | Camera credentials are not stored in plain text in the DB or returned by `/classrooms` or `/system/status` | Responses show camera `id` and `state` only | MUST |
| CAM2 | Camera credentials come from env/secret store, not from the repo or `docker-compose.yml` | Grep passes | MUST |
| CAM3 | `source_uri` accepts only allowed schemes (`rtsp://`, `file://` for tests, device index); rejects `http://169.254.169.254`, `file:///etc/passwd` and similar | 422 | MUST |
| CAM4 | Admin-supplied `source_uri` cannot be used to scan the internal network (SSRF) | Allow-list of hosts/subnets | SHOULD |
| CAM5 | Mock/test video generator is disabled in production config | Config check | MUST |
| CAM6 | Camera feed is only on the internal network; the camera's own web UI is not exposed to the internet | Network check | MUST |
| CAM7 | A camera that stops sending frames shows `Offline` after `CAMERA_TIMEOUT_S` and raises `camera_offline` (never silent) | Unplug test | MUST |
| CAM8 | A second source cannot impersonate an existing camera id | Only one writer per camera id | SHOULD |
| CAM9 | The AI worker rejects frames with unexpected size/format instead of crashing | Fuzz test with corrupt frames | MUST |

---

## 6. AI model and supply-chain security

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| ML1 | Models are pinned to the exact revision in `backend/models/MANIFEST.json` | Revision hash matches | MUST |
| ML2 | Prefer `model.safetensors`. A `pytorch_model.bin` file is a pickle and can run code when loaded | Use safetensors where available; otherwise load only from the pinned, trusted download | MUST |
| ML3 | `trust_remote_code` is **never** enabled when loading the Hugging Face models | Code search finds none | MUST |
| ML4 | Model files are checksummed after download and verified at startup | Mismatch stops startup | SHOULD |
| ML5 | `backend/models/` is writable only by the deployment user (a swapped model file is a tampering risk) | File permissions check | SHOULD |
| ML6 | Model licenses recorded and approved (OQ-4) | `MANIFEST.json` reviewed | MUST |
| ML7 | The AI output cannot be forced by an attacker holding up a printed face or image (spoof/adversarial input) | Documented limitation; alerts need persistence (D7) | NICE |
| ML8 | One bad frame or unusual input never produces an alert (D7) | Scenario tests from Phase 10 | MUST |
| ML9 | Output is labeled `heuristic` until trained weights exist (D10); the app never presents untrained LSTM output as real | `model_mode` shown | MUST |

---

## 7. Database hardening

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| DB1 | Production uses PostgreSQL with a **least-privilege** app user (no superuser, no `DROP`) | Verified with a privileged-action test | MUST |
| DB2 | Database port is not exposed outside the Docker network/host | Port scan | MUST |
| DB3 | SQLite file (dev) has restricted permissions and is not committed | `ls -l`, `.gitignore` | SHOULD |
| DB4 | Only parameterized queries/ORM are used; no string-built SQL | Code search for `execute(f"` | MUST |
| DB5 | Backups are encrypted, access-controlled and tested for restore | Restore drill | SHOULD |
| DB6 | Retention job deletes data older than `RETENTION_DAYS` including from backups' lifecycle | Verified | SHOULD |
| DB7 | Students are deactivated, not hard-deleted, and cascade rules are documented | Schema review | MUST |
| DB8 | `track_roster_map` (the link between `S003` and a real student, OQ-1) is readable only by admins | Teacher request returns 403 | MUST |
| DB9 | Database connection uses TLS in production | Config check | SHOULD |
| DB10 | Migrations are reviewed and run by the deployment user, not by the app at runtime in production | Process check | SHOULD |

---

## 8. Re-identification and student-privacy risks

Anonymous labels are only anonymous if nothing else lets someone work out who `S003` is.

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| PR1 | Reports for small classes do not let a viewer infer identity from seat or position | No seat/position data in reports or telemetry | MUST |
| PR2 | `bbox` coordinates are not sent to mobile (only `TrackResult-lite`) | W7 from the first guide plus a payload diff | MUST |
| PR3 | Per-student report rows use anonymous labels unless an admin has mapped them (OQ-1) | Check export | MUST |
| PR4 | Exports and reports are accessible only to the teacher of that session and to admins | Z7 from the first guide plus link-guessing test | MUST |
| PR5 | A deleted/deactivated student's data can be removed on request | Documented deletion procedure tested once | SHOULD |
| PR6 | Consent and notification policy exists before any real classroom use (OQ-5) | Signed-off document | MUST |
| PR7 | No emotion probabilities leave the backend except in the operator console debug view, and never alone trigger an alert | Payload check, rule check | MUST |

---

## 9. Denial-of-service and resource abuse

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| DOS1 | Rate limiting on **all** endpoints (not only login), with stricter limits on write endpoints | 429 after the threshold | MUST |
| DOS2 | Maximum WebSocket connections per user and in total | Extra connections refused | MUST |
| DOS3 | WebSocket idle timeout and ping/pong enforcement | Dead connections closed | SHOULD |
| DOS4 | Maximum request body size and maximum message size on sockets | 413 / socket closed | MUST |
| DOS5 | Pagination with a maximum page size on list endpoints (`/sessions`, `/alerts`, `/reports`) | `limit=1000000` is clamped | MUST |
| DOS6 | Report export cannot be triggered repeatedly to exhaust CPU/memory (queue or rate limit) | 429 | SHOULD |
| DOS7 | The inference queue drops old frames instead of growing without bound (Phase 12) | Memory stays flat in the soak test | MUST |
| DOS8 | Many faces in a frame cannot crash the AI worker (`max_num_faces` honored) | 100+ face fixture | MUST |
| DOS9 | Slow clients cannot block telemetry broadcast to other clients | One stalled socket test | MUST |
| DOS10 | Disk usage is bounded: logs rotate, no unbounded temp files | Soak test | SHOULD |

```bash
# Simple load/abuse checks (adapt host and token)
for i in $(seq 1 200); do curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" localhost:8000/alerts; done | sort | uniq -c
# Expect a mix of 200 and 429 once the limit is reached
```

---

## 10. API surface hardening

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| API1 | Swagger/OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) are disabled or protected in production | 404 or 401 | MUST |
| API2 | Only the methods the contract defines are allowed per route | Other methods return 405 | SHOULD |
| API3 | `/health` returns minimal data (no versions, paths, DB details) | Inspect response | MUST |
| API4 | `/system/status` gives teachers the reduced view only (AI/camera availability) | Teacher response lacks DB/api details | MUST |
| API5 | Responses do not leak other users' IDs, usernames or internal paths | Inspect | MUST |
| API6 | ID enumeration does not reveal which IDs exist (consistent 403/404) | Compare responses | SHOULD |
| API7 | `Content-Type` is enforced (`application/json`) | Others return 415/422 | SHOULD |
| API8 | CORS: no wildcard with credentials; origin allow-list only | Header check | MUST |
| API9 | Concurrent `PATCH /alerts/{id}` and double `POST /sessions/{id}/stop` are safe (no duplicate or corrupt state) | Race test | SHOULD |
| API10 | `PATCH /alerts/{id}` cannot change fields other than `status` | Extra fields ignored/rejected | MUST |
| API11 | Server version header is hidden | `Server:` header trimmed | NICE |

---

## 11. WebSocket extras

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| WS1 | Cross-site WebSocket hijacking: the server validates the `Origin` header against the allow-list | Connection from `evil.example` refused | MUST |
| WS2 | Replaying an old telemetry message to the server has no effect (server ignores client data except `ping`/`subscribe`) | Pass | MUST |
| WS3 | A client cannot send messages that appear to other clients (no client-to-client relay) | Pass | MUST |
| WS4 | `subscribe` accepts only integer session IDs the user may access | Strings, negatives, huge numbers rejected | MUST |
| WS5 | Close codes are consistent (4403 for forbidden video) and do not leak internals | Inspect | SHOULD |

---

## 12. Export and file-download safety

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| EXP1 | **CSV/formula injection:** any exported text starting with `=`, `+`, `-`, `@` is prefixed or escaped, so Excel does not execute it | Cell shows text, not a formula | MUST |
| EXP2 | Filenames are generated by the server (for example `session_12.csv`), never from user input | No path traversal | MUST |
| EXP3 | `format=` accepts only `csv` or `pdf` | Others return 422 | MUST |
| EXP4 | Download endpoint re-checks authorization on every request (no public or guessable links) | Anonymous request returns 401 | MUST |
| EXP5 | Exports contain the disclaimer footer and counts equal the report JSON (Phase 16) | Matches | MUST |
| EXP6 | Class names or labels containing HTML/script do not execute in the PDF, web console or mobile | Rendered as text | MUST |
| EXP7 | Temporary export files are deleted after sending | No leftovers on disk | SHOULD |

---

## 13. Audit logging and monitoring

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| AU1 | Log these events with user, time and IP: login success/failure, logout, account changes, role/classroom changes, session start/stop, alert status changes, report exports, admin CRUD | Entries present | MUST |
| AU2 | Logs never contain passwords, tokens, images or student identity | Grep (see first guide, P3, S5) | MUST |
| AU3 | Audit entries cannot be edited or deleted by the app user | Append-only or separate store | SHOULD |
| AU4 | Failed-login spikes and repeated 403s generate a visible warning | Alert or dashboard | SHOULD |
| AU5 | Health status for AI server, DB, API and each camera is monitored so "no alerts" is never mistaken for "AI is offline" | `ai_offline` and `camera_offline` tests | MUST |
| AU6 | Log rotation and retention are configured | Verified | SHOULD |
| AU7 | Log timestamps use UTC and the server clock is synced (NTP) | Check | SHOULD |

---

## 14. Infrastructure and deployment (Docker Compose, phase 24)

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| INF1 | Only the reverse proxy / web port is published; DB and AI worker ports are internal | `docker compose ps` shows no extra ports | MUST |
| INF2 | The system is reachable only on the school LAN/VPN, not the public internet | External scan | MUST |
| INF3 | Containers run as non-root, with a read-only filesystem where possible | Dockerfile review | SHOULD |
| INF4 | Secrets are passed through env/Docker secrets, not baked into images or committed Compose files | `docker history`, repo grep | MUST |
| INF5 | Base images are pinned and scanned (for example `trivy image <name>`) | No high/critical findings | SHOULD |
| INF6 | Resource limits (CPU/memory) set per container | Compose config | SHOULD |
| INF7 | TLS certificates valid; HTTP redirects to HTTPS; WebSockets use `wss://` | Browser and `curl -I` checks | MUST |
| INF8 | Firewall allows only needed ports; camera VLAN separated from user devices if possible | Network review | SHOULD |
| INF9 | Debug mode, auto-reload and verbose logging are off in production | Config check | MUST |
| INF10 | Restart policy and health checks defined, so a crashed AI worker is visible and recovers | Kill-process test | SHOULD |

```bash
trivy image project-backend:latest          # container vulnerability scan
docker compose ps                            # confirm published ports
nmap -p- <server-ip>                         # from another machine on the LAN
```

---

## 15. Web console extras

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| WEB1 | XSS: student labels, class names and alert text are rendered as text, never HTML | Inject `<script>` strings | MUST |
| WEB2 | CSRF: if cookies are used for auth, `SameSite` and CSRF tokens are in place; if bearer tokens are used, they are not auto-sent by the browser | Verified | MUST |
| WEB3 | Clickjacking protection (`X-Frame-Options` or CSP `frame-ancestors`) | Header present | SHOULD |
| WEB4 | Content-Security-Policy restricts scripts to your own origin | Header present | SHOULD |
| WEB5 | No open redirects after login | `?next=` only allows internal paths | SHOULD |
| WEB6 | Third-party scripts and fonts are loaded from trusted sources, pinned or self-hosted | Review | SHOULD |
| WEB7 | Browser caching: sensitive API responses use `Cache-Control: no-store` | Header check | SHOULD |
| WEB8 | Session timeout on idle | Auto logout | SHOULD |

---

## 16. Mobile app extras

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| MOB1 | Certificate pinning or at least strict TLS validation; no `allowsArbitraryLoads`/cleartext in production | Config review | SHOULD |
| MOB2 | Android `allowBackup` disabled so tokens/data are not copied into backups | Manifest check | SHOULD |
| MOB3 | Deep links cannot open screens that skip authentication or role checks | Test links as logged-out and as teacher | MUST |
| MOB4 | App does not log tokens, responses or push payloads in release builds | Release log review | MUST |
| MOB5 | Push tokens are tied to the authenticated user and removed on logout | Verify on backend | MUST |
| MOB6 | Optional: biometric unlock or app lock after inactivity | Works | NICE |
| MOB7 | Optional: block screenshots/app-switcher previews on sensitive screens | Works | NICE |
| MOB8 | Rooted/jailbroken device warning (optional policy decision) | Documented decision | NICE |
| MOB9 | Build is signed; release builds use production endpoints only | Check build config | MUST |
| MOB10 | Mobile never calls `/ws/video` or renders face imagery (D4) | Code search, traffic capture | MUST |

---

## 17. Software supply chain and development process

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| SC1 | Lock files committed (`requirements.txt` with pins, `package-lock.json`) | Present | MUST |
| SC2 | Pre-commit or CI secret scanning (for example `gitleaks`) | Blocks a test secret | SHOULD |
| SC3 | Dependency updates reviewed; automated alerts enabled | Configured | SHOULD |
| SC4 | CI runs the security tests from both guides on every merge | Pipeline green | SHOULD |
| SC5 | Token lint from `ui.md` plus a lint for forbidden patterns (`dangerouslySetInnerHTML`, `eval`, `trust_remote_code`) | CI fails on a test violation | SHOULD |
| SC6 | SBOM generated for each release (for example `pip-audit`/`cyclonedx`) | Stored with the release | NICE |
| SC7 | Code review required for changes to auth, roles and privacy code | Branch rules | SHOULD |

---

## 18. Ethics, legal and operational readiness

These are not automated tests, but each one is a go/no-go item.

| ID | Check | Expected | Level |
|----|-------|----------|-------|
| LEG1 | Institutional consent and notification for students and parents/guardians (OQ-5) | Written policy approved | MUST |
| LEG2 | Data retention period approved and configured (`RETENTION_DAYS`) | Documented | MUST |
| LEG3 | Human in the loop: no automatic disciplinary, academic or health action (D8) | Policy and UI copy reviewed | MUST |
| LEG4 | Bias and accuracy limits documented (lighting, angle, masks, skin tone, glasses) and shown to users as indicators only | Limitations page | MUST |
| LEG5 | Complaint/appeal process for students or parents | Documented | SHOULD |
| LEG6 | Incident response plan: who is told, how tokens are revoked, how secrets are rotated | Written and rehearsed once | MUST |
| LEG7 | Vulnerability reporting contact for staff | Published internally | NICE |
| LEG8 | Applicable local data-protection rules reviewed with the institution's legal contact | Sign-off | MUST |

---

## 19. How to run and record

1. Complete `docs/THREAT_MODEL.md` (section 2).
2. Run the automated checks (pytest, `trivy`, `npm audit`, secret scan, load loops) and the manual checks.
3. Record the results in `docs/PROGRESS.md`:

```markdown
## Additional security checks: <date>
- Status: PASS | FAIL | BLOCKED
- Sections run: 3-18
- Failures: <ID, expected, actual, severity>
- Accepted risks (owner-approved): ...
- Tools and versions: trivy ..., gitleaks ..., nmap ...
```

### Release rule

| Severity | Examples | Rule |
|----------|----------|------|
| **Critical** | SSRF to internal network, model loaded from untrusted source, camera credentials exposed, teacher reads `track_roster_map` | Release blocked |
| **High** | No rate limiting, docs exposed in production, CSV injection, DB/port exposed | Release blocked |
| **Medium** | Missing headers, no audit alerting | Fix or accept the risk in writing |
| **Low** | Optional hardening items | Track in `OPEN_QUESTIONS.md` |

---

## 20. Final checklist

- [ ] Threat model written; every STRIDE cell covered.
- [ ] All **MUST** items in sections 3-18 pass.
- [ ] Camera credentials and `source_uri` handling reviewed (section 5).
- [ ] Models pinned, checksummed, loaded without `trust_remote_code` (section 6).
- [ ] DB least-privilege user, port closed, roster mapping admin-only (section 7).
- [ ] Rate limits, connection limits and size limits active (section 9).
- [ ] API docs closed in production; CORS and Origin checks in place (sections 10-11).
- [ ] CSV/PDF export safe (section 12).
- [ ] Audit logging covers all listed events (section 13).
- [ ] Only the web port is published; LAN/VPN only; TLS on (section 14).
- [ ] Consent policy, incident plan and legal sign-off completed (section 18).
- [ ] Results recorded in `docs/PROGRESS.md`.

> Automated tests cannot replace an independent penetration test. Before a real classroom deployment, arrange one together with a network and legal review.
