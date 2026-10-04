# Threat Model: Student Attention & Fatigue Detection Platform

> **Document ID:** SEC-TM-001  
> **Status:** Active / Approved  
> **Compliance:** `docs/README_SECURITY_ADDITIONAL_CHECKS.md` §2, `docs/README_SECURITY_TESTING.md`, `docs/contracts.md`, `docs/system_work.md`.  
> **Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) evaluated per architectural component.

---

## 1. System Architecture & Trust Boundaries

```
[ Classroom Camera (RTSP / USB) ]
              │ (Internal School LAN / VLAN)
              ▼
    [ AI Inference Worker ] ───(ZMQ / Internal IPC)───┐
                                                      │
[ Mobile App (Teacher) ] ◄──(HTTPS / WSS Bearer)──► [ FastAPI Backend ] ◄──► [ PostgreSQL / SQLite DB ]
                                                      │
[ Operator Console (Admin) ] ◄──(HTTPS / WSS Bearer)──┘
```

### Trust Zones:
1. **Zone 0 (Physical / Sensor):** Camera hardware and RTSP video feeds on physical school premises.
2. **Zone 1 (Internal Inference Network):** AI Worker, model artifacts, internal frame queues, GPU/CPU resources.
3. **Zone 2 (Application Boundary):** FastAPI backend, REST endpoints, WebSocket channels, JWT session validator.
4. **Zone 3 (Data Persistence):** Relational database containing structured telemetry, alerts, and user accounts.
5. **Zone 4 (Client Tier):** Teacher Mobile App (React Native) and Admin Operator Console (React/Vite).

---

## 2. STRIDE Threat Matrix & Verification Mapping

Every cell in this threat matrix maps directly to an automated verification test ID from `README_SECURITY_TESTING.md` or `README_SECURITY_ADDITIONAL_CHECKS.md`, or documents a technical mitigation and accepted risk.

| Component | Spoofing | Tampering | Repudiation | Information Disclosure | Denial of Service | Elevation of Privilege |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Camera / RTSP feed** | **Threat:** Fake camera feed injection.<br>**Mitigation:** Strict `source_uri` scheme validation, single-writer per camera ID.<br>**Test:** `CAM3`, `CAM8` | **Threat:** Altered video frames.<br>**Mitigation:** Transport over isolated school VLAN; corrupt frame rejection.<br>**Test:** `CAM9` | **Threat:** No audit log of camera source.<br>**Mitigation:** Connection lifecycle & disconnect logged with timestamp.<br>**Test:** `CAM7`, `AU1` | **Threat:** Stream credentials leaked in API.<br>**Mitigation:** Plaintext passwords stripped from responses; `source_uri` hidden from client.<br>**Test:** `CAM1`, `CAM2` | **Threat:** Feed flood / socket saturation.<br>**Mitigation:** Camera timeout watchdog and reconnect circuit breakers.<br>**Test:** `CAM7`, `DOS7` | **Threat:** Privilege escalation via camera.<br>**Mitigation:** N/A (Camera is a passive input sensor without execution privilege).<br>**Status:** Mitigated / N/A |
| **AI Worker** | **Threat:** Fake worker heartbeat / rogue worker.<br>**Mitigation:** Heartbeat timeout detection (`ai_offline` alert raised).<br>**Test:** `AU5`, `CAM7` | **Threat:** Model file swap or deserialization exploit.<br>**Mitigation:** SHA-256 manifest pinning, safetensors format, no `trust_remote_code`.<br>**Test:** `ML1`, `ML2`, `ML3`, `ML4` | **Threat:** Unlogged inference anomalies.<br>**Mitigation:** Worker stderr/stdout aggregated in append-only logs with ISO UTC timestamps.<br>**Test:** `AU1`, `AU7` | **Threat:** Model or frame leakage.<br>**Mitigation:** Frames kept in ephemeral memory only; zero disk/cloud caching.<br>**Test:** `P1`, `P3`, `ML5` | **Threat:** GPU/CPU exhaustion via dense crowds.<br>**Mitigation:** `max_num_faces` cap, inference queue frame-dropping.<br>**Test:** `DOS7`, `DOS8` | **Threat:** Privilege escalation in inference runtime.<br>**Mitigation:** Worker runs as unprivileged non-root service account with read-only model dir.<br>**Test:** `ML5`, `INF3` |
| **FastAPI Backend** | **Threat:** Stolen or forged JWT token.<br>**Mitigation:** HS256 signature verification, server-side token revocation / deny-list on logout.<br>**Test:** `A4`, `A5`, `SM1`, `SM7` | **Threat:** Request payload tampering / injection.<br>**Mitigation:** Strict Pydantic input schemas, extra field forbidding, parameterized queries.<br>**Test:** `V1`, `V2`, `DB4`, `API10` | **Threat:** Missing audit trail for actions.<br>**Mitigation:** Structured audit logging for all auth, session, and alert lifecycle transitions.<br>**Test:** `AU1`, `AU2` | **Threat:** Verbose error / stack trace leaks.<br>**Mitigation:** Custom error handlers strip stack traces, DB details, and internal paths.<br>**Test:** `V7`, `API3`, `API5` | **Threat:** Request flood / brute force.<br>**Mitigation:** IP & username sliding-window rate limiting, clamped pagination limits.<br>**Test:** `A1`, `A10`, `DOS1`, `DOS5` | **Threat:** Role bypass (Teacher accessing Admin).<br>**Mitigation:** Declarative FastAPI dependency role guards (`require_admin`, `require_teacher`).<br>**Test:** `R1`, `R2`, `R3`, `R4`, `API4` |
| **WebSocket (`/ws/telemetry`, `/ws/video`)** | **Threat:** Token reuse or unauthenticated connection.<br>**Mitigation:** Mandatory query parameter JWT validation with instant close on failure.<br>**Test:** `W1`, `W4`, `SM4` | **Threat:** Message injection / replay attacks.<br>**Mitigation:** Server ignores unsolicited inbound frames; allows only validated client ping/subscribe.<br>**Test:** `WS2`, `WS3` | **Threat:** Unaudited connection events.<br>**Mitigation:** Connect and disconnect timestamps logged with client IP.<br>**Test:** `AU1` | **Threat:** Video or raw telemetry leakage.<br>**Mitigation:** Non-negotiable code 4403 rejection on `/ws/video` when `PRIVACY_MODE=true`.<br>**Test:** `W4`, `W5`, `W6`, `W7` | **Threat:** Connection flood / slowloris.<br>**Mitigation:** Max connections per IP and total; non-blocking broadcast with timeout.<br>**Test:** `DOS2`, `DOS9` | **Threat:** Cross-class subscription / CSWSH.<br>**Mitigation:** Origin header allow-list; session ownership authorization verification on subscribe.<br>**Test:** `WS1`, `WS4` |
| **Database (PostgreSQL / SQLite)** | **Threat:** Unauthorized connection / impersonation.<br>**Mitigation:** Password-authenticated app user over local Unix socket / TLS network.<br>**Test:** `DB1`, `DB9` | **Threat:** Row tampering / data corruption.<br>**Mitigation:** Foreign key CASCADE/RESTRICT rules, DB check constraints, soft-deletes.<br>**Test:** `DB4`, `DB7` | **Threat:** Untracked data mutation.<br>**Mitigation:** Schema change management via tracked Alembic migrations.<br>**Test:** `DB10` | **Threat:** Unauthorized data dump / roster map leak.<br>**Mitigation:** Zero biometric/image columns in schema; `track_roster_map` restricted to Admin.<br>**Test:** `P1`, `P2`, `DB8` | **Threat:** Disk fill / unbounded growth.<br>**Mitigation:** Configurable data retention daemon (`RETENTION_DAYS`) and log rotation.<br>**Test:** `DB6`, `DOS10` | **Threat:** Over-privileged DB user.<br>**Mitigation:** Non-superuser application connection; no `DROP` or `SUPERUSER` privileges.<br>**Test:** `DB1` |
| **Web Console & Mobile App** | **Threat:** Phishing, stolen credentials, deep link bypass.<br>**Mitigation:** Encrypted local token storage (`SecureStore`), client-side route guards.<br>**Test:** `C1`, `M1`, `MOB3` | **Threat:** Client-side cache / local storage tampering.<br>**Mitigation:** Tokens stored in hardware keychain; no sensitive biometrics cached.<br>**Test:** `M1`, `M4`, `MOB4` | **Threat:** Unlogged client actions.<br>**Mitigation:** All mutations require backend API calls which are centrally audited.<br>**Test:** `AU1` | **Threat:** XSS, HTML injection, CSV injection.<br>**Mitigation:** React auto-escaping, CSP headers, single-quote escaping of formula prefixes (`=`, `+`, `-`, `@`).<br>**Test:** `EXP1`, `EXP6`, `WEB1`, `WEB4` | **Threat:** Client resource exhaustion.<br>**Mitigation:** Lightweight virtualized lists, bounded history window in state store.<br>**Test:** `C4`, `M6` | **Threat:** Client-side role bypass.<br>**Mitigation:** Defense in depth: UI hides admin links, but backend strictly validates JWT claims.<br>**Test:** `C2`, `M2`, `V6` |

---

## 3. High-Priority Invariants (Non-Negotiable)

1. **Zero-Media Retention Invariant:**  
   Under no circumstances shall video frames, face crops, or biometric embeddings be stored in the database, cached on disk, or streamed to mobile clients (`PRIVACY_MODE=true` default).
2. **Non-Diagnostic Advisory Copy (D8):**  
   System outputs are classroom engagement indicators only. No medical, clinical, psychological, or disciplinary terminology is permitted in API responses, logs, or UI components.
3. **Explicit Role Isolation:**  
   Teachers are strictly confined to their assigned classrooms and sessions (`403 Forbidden` on foreign IDs). Re-identification maps (`track_roster_map`) and system diagnostic metrics are strictly restricted to administrators.
4. **Denial-of-Service Defense:**  
   Sliding-window rate limiting on auth endpoints, maximum page sizes on list endpoints, and connection quotas on WebSocket channels prevent resource exhaustion.

---

## 4. Threat Model Sign-Off

- **Lead Security Architect:** Approved
- **Lead Backend Engineer:** Approved
- **Compliance Status:** **100% of STRIDE cells mapped to automated test IDs or technical mitigations.**
