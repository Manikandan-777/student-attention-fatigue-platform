# Contracts — Shared Names, Schemas, APIs, Thresholds

> **Doc ID:** `CON` · **Authority:** second only to `README.md` §3. Every backend, AI, web and mobile component must use these names exactly.
> **Related:** concept → `system_work.md` · behavior → `application_behavior.md` · build order → `implementation.md`

---

## 1. Enums (frozen — decision D6)

| Enum | Values |
|------|--------|
| `attention_status` | `Attentive`, `Distracted`, `Unknown` |
| `fatigue_status` | `Normal`, `Fatigued`, `Unknown` |
| `emotion` | `Angry`, `Disgust`, `Fear`, `Happy`, `Sad`, `Surprise`, `Neutral` |
| `drowsiness_label` | `Drowsy`, `Non Drowsy` (verify against model `config.json` `id2label`, do not hard-code — see MDL-4) |
| `alert_type` | `fatigue`, `distraction`, `camera_offline`, `ai_offline` |
| `alert_status` | `New`, `Viewed`, `Resolved` |
| `session_status` | `Scheduled`, `Monitoring`, `Completed`, `Aborted` |
| `role` | `teacher`, `admin` |
| `service_state` | `Online`, `Offline`, `Degraded` |
| `model_mode` | `heuristic`, `lstm` (D10) |

`Unknown` is used when no usable face, occlusion, or confidence below `MIN_CONFIDENCE`.

## 2. Core Data Objects

### 2.1 `TrackResult` — per tracked face, per processed frame (internal + operator console)

```json
{
  "track_id": 4,
  "label": "S004",
  "bbox": [x, y, w, h],
  "bbox_normalized": true,
  "landmark_confidence": 0.97,
  "features": { "ear": 0.27, "mar": 0.31, "perclos": 0.08, "head_yaw": -4.2, "head_pitch": 6.1 },
  "drowsiness": { "label": "Non Drowsy", "p_drowsy": 0.12 },
  "emotion": { "top": "Neutral", "probs": { "Angry": 0.01, "Disgust": 0.0, "Fear": 0.01, "Happy": 0.1, "Sad": 0.03, "Surprise": 0.02, "Neutral": 0.83 } },
  "attention_score": 86.0,
  "fatigue_index": 0.14,
  "attention_status": "Attentive",
  "fatigue_status": "Normal",
  "confidence": 0.94,
  "model_mode": "heuristic"
}
```

Rules: `emotion.probs` has exactly 7 keys summing to 1.0 (±1e-4). `attention_score` ∈ [0,100]. `fatigue_index` ∈ [0,1]. No image data in this object.

### 2.2 `Observation` — stored aggregate (one row per track per `OBSERVATION_INTERVAL_S`)

```json
{
  "session_id": 12, "track_id": 4, "ts": "2026-09-30T10:42:05Z",
  "attention_status": "Attentive", "fatigue_status": "Normal",
  "attention_score_mean": 86.0, "fatigue_index_mean": 0.14,
  "confidence_mean": 0.94, "drowsy_frames": 0, "total_frames": 60
}
```

### 2.3 `Alert`

```json
{
  "id": 77, "session_id": 12, "track_id": 3, "label": "S003",
  "type": "fatigue", "status": "New",
  "message": "Repeated fatigue-related indicators during the current session.",
  "confidence": 0.92, "created_at": "2026-09-30T10:42:11Z",
  "viewed_at": null, "resolved_at": null
}
```

Message copy is informational only (D8). Never "is sleeping" / "is sick".

### 2.4 `ClassSnapshot` — dashboard summary

```json
{
  "session_id": 12, "class_name": "III AI & DS", "status": "Monitoring",
  "students_detected": 45,
  "counts": { "attentive": 35, "distracted": 7, "unknown": 0, "fatigued": 3 },
  "avg_attention_score": 82.0,
  "open_alerts": 3,
  "fatigue_advisory": {
    "class_fatigue_pct": 62.4,
    "level": 3,
    "code": "SHORT_BREAK",
    "message": "Do a short activity or give a short break.",
    "usable_tracks": 41,
    "since": "2026-09-30T10:42:11Z"
  }
}
```
Note: `fatigue_advisory` is an optional additive field; returns `null` when fewer than `ADVISORY_MIN_TRACKS` usable tracks are present.


### 2.5 `SystemStatus`

```json
{
  "ai_server": "Online", "database": "Online", "api": "Online",
  "cameras": [ { "id": "CAM-001", "state": "Online" }, { "id": "CAM-003", "state": "Offline" } ],
  "fps": 22.4, "model_mode": "heuristic", "privacy_mode": true
}
```

## 3. REST API (JSON, `Authorization: Bearer <JWT>`)

Role column: **T** teacher, **A** admin, **A/T** both (teachers limited to their assigned classrooms; enforced server-side, APP-26).

| Method | Path | Role | Purpose | Phase |
|--------|------|------|---------|-------|
| GET | `/health` | none | Liveness | 11 |
| POST | `/auth/login` | none | Returns JWT + `role` | 14 |
| GET | `/auth/me` | A/T | Current user | 14 |
| GET | `/teacher/dashboard` | T | `ClassSnapshot` for active session(s) | 14 |
| GET | `/classrooms` | A/T | List classrooms (+camera id, status) | 14 |
| POST/PUT/DELETE | `/classrooms[/{id}]` | A | Classroom CRUD | 14 |
| GET | `/classrooms/{id}/students` | A/T | Roster | 14 |
| GET/POST/PUT/DELETE | `/students[/{id}]` | A | Student CRUD (deactivate rather than delete) | 14 |
| POST | `/students/{id}/assign` | A | Assign to classroom | 14 |
| GET/POST/PUT | `/teachers[/{id}]` | A | Teacher accounts, enable/disable, assign classrooms | 14 |
| POST | `/sessions` | A/T | Start session `{classroom_id}` | 13/14 |
| POST | `/sessions/{id}/stop` | A/T | End session, triggers report | 13/14 |
| GET | `/sessions` , `/sessions/{id}` | A/T | List / detail | 14 |
| GET | `/sessions/{id}/tracks` | A/T | Current per-track status list | 14 |
| GET | `/students/{id}/status` | A/T | Latest status for a student/track (path accepts track label during anonymous mode) | 14 |
| GET | `/alerts?status=&session_id=` | A/T | Alert list | 15 |
| PATCH | `/alerts/{id}` | A/T | Body `{ "status": "Viewed" \| "Resolved" }` | 15 |
| GET | `/reports` | A/T | Historical session summaries | 16 |
| GET | `/reports/{session_id}` | A/T | Session report JSON | 16 |
| GET | `/reports/{session_id}/export?format=csv\|pdf` | A/T | File download | 16 |
| GET | `/system/status` | A | `SystemStatus` (teachers get a reduced view: AI/camera availability only) | 14 |

Errors: `{ "error": { "code": "string", "message": "string" } }` with standard HTTP codes (401 unauthenticated, 403 wrong role/classroom, 404, 422 validation).

## 4. WebSocket API

| Endpoint | Audience | Messages server→client | Notes |
|----------|----------|------------------------|-------|
| `/ws/telemetry?token=` | Operator Console **and** Mobile | `telemetry`, `alert`, `system_status`, `pong` | Validated results only, no pixels. Throttled to `TELEMETRY_HZ` (default 2). |
| `/ws/video?token=` | Operator Console only (role `admin`/`teacher`, and `PRIVACY_MODE=false`) | `frame` | Annotated JPEG, rejected with close code 4403 when privacy mode is on. Never forwarded to mobile. |

Client→server: `{"type":"ping"}` → server `{"type":"pong"}`; `{"type":"subscribe","session_id":12}`.

```json
{ "type": "telemetry", "session_id": 12, "ts": "...", "snapshot": ClassSnapshot, "tracks": [ TrackResult-lite ] }
{ "type": "alert", "alert": Alert }
{ "type": "system_status", "status": SystemStatus }
{ "type": "frame", "session_id": 12, "ts": "...", "jpeg_b64": "...", "tracks": [ {"track_id":4,"bbox":[...],"attention_status":"...","fatigue_status":"..."} ] }
```

`TrackResult-lite` = `track_id, label, attention_status, fatigue_status, attention_score, confidence` (no landmarks, no probabilities) — this is what mobile receives (APP-27 privacy).

## 5. Validation & Alert Rules (defaults — all configurable via env/config)

| Key | Default | Meaning |
|-----|---------|---------|
| `MIN_CONFIDENCE` | 0.80 | Below this a status is shown as `Unknown` and cannot alert. |
| `WINDOW_FRAMES` | 30 | Rolling window per track. |
| `SMOOTHING` | EMA α=0.3 on scores | Prevents single-frame flips. |
| `STATUS_HYSTERESIS_S` | 3 | A status must hold this long before the displayed status changes. |
| `FATIGUE_PERSIST_S` | 45 | Fatigued-state persistence before a `fatigue` alert (example from the alert-feed spec, IMP Phase 20). |
| `DISTRACTION_PERSIST_S` | 30 | Distracted-state persistence before a `distraction` alert. |
| `ALERT_COOLDOWN_S` | 300 | Minimum gap for same `(track, type)` alert. |
| `OBSERVATION_INTERVAL_S` | 5 | Aggregation for DB rows. |
| `TELEMETRY_HZ` | 2 | Client broadcast rate. |
| `CAMERA_TIMEOUT_S` | 10 | No frames for this long → camera `Offline` + `camera_offline` alert to admin. |
| `AI_HEARTBEAT_TIMEOUT_S` | 10 | AI worker silent → `ai_offline`. |
| `TARGET_FPS` | 20 | Phase 12 pass threshold. |
| `MAX_INFER_MS_PER_FACE` | 15 | Phase 5 pass threshold (on declared hardware, OQ-3). |
| `PRIVACY_MODE` | `true` | Disables `/ws/video`. |

State machine per `(track, condition)`: `Normal → Candidate (condition true, confidence ≥ MIN_CONFIDENCE) → Confirmed (held ≥ persist window) → Alerted (emit once, start cooldown) → Cleared (condition false for STATUS_HYSTERESIS_S)`.

## 6. Default Scoring Formula (heuristic mode, D10)

Inputs (each ∈ [0,1] after smoothing): `p_drowsy` (MobileViT), `perclos`, `yawn` (MAR above threshold fraction of window), `off_task` (head yaw/pitch outside ±`HEAD_LIMIT_DEG`, default 25°, fraction of window), `neg_affect` (Sad+Fear+Angry+Disgust probability — weak signal).

```text
fatigue_index   = 0.45*p_drowsy + 0.35*perclos + 0.20*yawn
distraction     = 0.65*off_task + 0.20*fatigue_index + 0.15*neg_affect
attention_score = 100 * (1 - clamp(distraction, 0, 1))

fatigue_status  = Fatigued   if fatigue_index   ≥ 0.55
attention_status= Distracted if attention_score ≤ 55
                  (else Attentive; Unknown if confidence < MIN_CONFIDENCE)
```

These weights/thresholds are **starting values for tuning**, not validated science. Phase 10 must expose them in config and record the simulation results. When trained LSTM-attention weights are loaded (`model_mode = "lstm"`), its output is blended: `final = 0.5*heuristic + 0.5*lstm` until validated on real data.
Expression is a weak, culturally variable proxy — it must not be the sole trigger of any alert.

## 7. Database Tables (SQLAlchemy; SQLite dev / PostgreSQL prod)

| Table | Key columns |
|-------|-------------|
| `users` | id, username (unique), password_hash, role, active, created_at |
| `teachers` | id, user_id → users, display_name |
| `students` | id, student_code (unique), name, department, year, class_name, active |
| `classrooms` | id, room_name, class_name, camera_id → cameras, active |
| `cameras` | id (e.g. `CAM-001`), source_uri, state, last_seen |
| `teacher_classrooms` | teacher_id, classroom_id |
| `classroom_students` | classroom_id, student_id |
| `sessions` | id, classroom_id, started_at, ended_at, status, students_detected_max |
| `track_roster_map` | session_id, track_id, student_id (nullable; OQ-1) |
| `observations` | id, session_id, track_id, ts, statuses, score means, confidence_mean, frame counts |
| `alerts` | id, session_id, track_id, type, status, message, confidence, created_at, viewed_at, resolved_at |

Constraints: foreign keys enforced, cascade rules documented, **no BLOB/image columns**. Retention: observations and alerts kept `RETENTION_DAYS` (default 180, configurable).

## 8. Report Schema (CSV/PDF source, phase 16)

```json
{
  "session_id": 12, "class_name": "III AI & DS", "date": "2026-09-30",
  "start": "09:00", "end": "10:00", "duration_min": 60, "students": 45,
  "attention": { "attentive": 35, "distracted": 7, "unknown": 3 },
  "fatigue":   { "normal": 42, "fatigued": 3 },
  "alerts_total": 5, "avg_attention_score": 82.0,
  "per_student": [ { "label": "S003", "attention_mean": 71.2, "fatigue_index_mean": 0.61, "fatigue_indicators": 4, "distraction_indicators": 1, "alerts": 2 } ]
}
```

Counts in the CSV/PDF must equal this JSON exactly (Phase 16 pass condition). Every report carries the footer: *"AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."*
