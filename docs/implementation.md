# Implementation Roadmap — 25 Phases with Agent Verification

> **Doc ID:** `IMP` · **Purpose:** the build order for the whole system and how each step is verified.
> **Read first:** `README.md` (decisions D1–D10, working protocol §6) and `contracts.md` (all names/schemas/thresholds).
> **Each phase lists its Spec refs:** `SYS-n` → `system_work.md`, `APP-n` → `application_behavior.md`, `MDL-n` → `model_download_integration_plan.md`, `UI` → `ui.md`, `CON §n` → `contracts.md`.
> Targets such as latency/FPS are **config values** measured on declared hardware (OQ-3); record measured numbers in `docs/PROGRESS.md`.

---

## 1. Phase Overview

| Track | Phases | Result |
|-------|--------|--------|
| A. Foundations | 1–2 | Environment + pretrained models on disk |
| B. AI pipeline | 3–10 | Faces → features → scores → validated status |
| C. Backend | 11–16 | API, streaming loop, DB, auth, alerts, reports |
| D. Operator Console (web) | 17–20 | Live grid, charts, alert feed |
| E. Mobile App | 21–23 | Teacher/admin app |
| F. Release | 24–25 | Integration/stress test, hardening |

```text
1 → 2 → 3 → 4 → 5 ┐
              └→ 6 ┴→ 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 ┬→ 17 → 18 → 19 → 20 ┐
                                                                     └→ 21 → 22 → 23 ─────┴→ 24 → 25
```

## 2. Mapping from the Earlier 20-Phase Plan (decision D9)

| Old | New | Change |
|-----|-----|--------|
| 1, 2 | 1, 2 | Model path changed to `backend/models/…` (D2) |
| 3 | 3 | Added track IDs and landmark-derived EAR/MAR |
| 4–6 | 4–6 | Unchanged in intent |
| 7 | 7 | Added PERCLOS/head-pose feature computation |
| 8, 9 | 8, 9 | Added "untrained weights" rule (D10) |
| 10 | 10 | Added validation state machine + heuristic formula |
| 11, 12 | 11, 12 | Privacy mode, contracts-based messages |
| 17 | **13** | DB moved earlier (sessions/alerts need it) |
| — | **14** | NEW: auth, roles, REST API |
| — | **15** | NEW: alert engine + alert API |
| 18 | **16** | Reports |
| 13–16 | **17–20** | Operator Console |
| — | **21–23** | NEW: mobile app (was only in `application_behavior.md`) |
| 19 | **24** | Integration & stress |
| 20 | **25** | Hardening |

---

# Track A — Foundations

### Phase 1 — Environment & Dependency Provisioning
- **Depends on:** none
- **Task:** Create repo layout (`README.md` §5), Python virtual environment, install `torch`, `torchvision`, `transformers`, `mediapipe`, `fastapi`, `uvicorn`, `opencv-python`, `huggingface_hub`, `sqlalchemy`, `pytest`, `pytest-asyncio`, `httpx`. Pin versions in `requirements.txt`.
- **Deliverables:** `backend/requirements.txt`, `backend/scripts/check_env.py`, `.gitignore` (excludes `backend/models/**`, `.env`, `*.db`).
- **Spec refs:** SYS-15.
- **Test:** run `check_env.py` — imports every package, asserts versions against pins, prints Python version and whether CUDA is available.
- **Pass:** zero import errors; all version assertions succeed.

### Phase 2 — Hugging Face Model Download & Verification
- **Depends on:** 1
- **Task:** Implement `download_models.py` and `verify_models.py` exactly as specified in MDL-3/MDL-4; models go to `backend/models/drowsiness/` and `backend/models/expression/` (D2).
- **Deliverables:** both scripts, `backend/models/MANIFEST.json` (repo, pinned revision, license).
- **Spec refs:** MDL-1…MDL-5, OQ-4.
- **Test:** run `verify_models.py` (config exists, weights file exists, `id2label` printed, preprocessor config read, dummy forward pass works).
- **Pass:** both models load via PyTorch without missing-file exceptions; emotion labels match CON §1.

---

# Track B — AI Pipeline

### Phase 3 — MediaPipe Multi-Face Pipeline with Tracking
- **Depends on:** 1
- **Task:** Implement `ai/mediapipe_tracker.py`: process frames, return per-face bounding boxes and normalized landmark arrays for multiple faces; assign stable anonymous `track_id`s across frames (IoU/centroid matching with a max-age for lost tracks); expose landmark-confidence; compute EAR, MAR, head yaw/pitch from landmarks in `ai/features.py`.
- **Deliverables:** `ai/mediapipe_tracker.py`, `ai/features.py`, test fixtures (synthetic or sample multi-face images).
- **Spec refs:** SYS-2, SYS-3, SYS-4, CON §2.1.
- **Test:** pass a multi-face mock clip/image batch through the tracker; assert track-ID stability across consecutive frames and correct EAR direction (closed-eye image → lower EAR than open-eye).
- **Pass:** all faces in the fixtures detected with ≥ 95% landmark tracking confidence; IDs persist across frames; no ID swap in the fixture clip.

### Phase 4 — Dynamic ROI Cropping & Alignment
- **Depends on:** 3, 2 (for model preprocessing values from MDL-4)
- **Task:** `ai/roi.py`: crop each face (with margin), resize to 224×224 (or the size read from each model's `preprocessor_config.json`), normalize with the model's mean/std, return batched tensors. Handle edge cases: box partially outside frame, tiny faces (reject below `MIN_FACE_PX`).
- **Spec refs:** MDL-5, SYS-5.
- **Test:** unit tests for tensor shape, dtype, value bounds, and out-of-frame boxes.
- **Pass:** output shape is `(Batch, 3, 224, 224)`; values match the model's normalization; invalid crops are skipped, not crashed on.

### Phase 5 — MobileViT Drowsiness Inference Wrapper
- **Depends on:** 2, 4
- **Task:** `ai/drowsiness.py`: batch inference in `torch.inference_mode()`; output `{label, p_drowsy}` using the single `LABEL_MAP` constant (MDL-4).
- **Spec refs:** MDL-5, CON §2.1, CON §5 (`MAX_INFER_MS_PER_FACE`).
- **Test:** run on open-eye vs closed-eye test crops; measure per-face latency over ≥ 100 runs after warm-up.
- **Pass:** closed-eye fixtures classified `Drowsy`, open-eye `Non Drowsy`; latency ≤ `MAX_INFER_MS_PER_FACE` (default 15 ms) on declared hardware, number recorded.

### Phase 6 — Vision Transformer Expression Wrapper
- **Depends on:** 2, 4
- **Task:** `ai/expression.py`: output a probability dict over exactly the 7 `emotion` values (CON §1) plus `top`.
- **Spec refs:** MDL-5, CON §2.1, CON §6 (expression is a weak signal).
- **Test:** evaluate on reference emotion images; assert key set, sum, and top label for clear examples.
- **Pass:** dict has all 7 keys, probabilities sum to 1.0 (±1e-4).

### Phase 7 — Temporal History Queue & Feature Window
- **Depends on:** 3, 5, 6
- **Task:** `ai/temporal.py`: per-`track_id` rolling buffer of the last `WINDOW_FRAMES` feature vectors (EAR, MAR, head pose, `p_drowsy`, emotion probs); compute windowed PERCLOS, yawn fraction, off-task fraction; purge tracks not seen for `TRACK_TTL_S`.
- **Spec refs:** SYS-4, SYS-6, CON §5.
- **Test:** push sequential mock frames for several tracks; check FIFO bounds and memory over a long run (e.g., 100k pushes with track churn).
- **Pass:** window size constant; old frames and dead tracks purged; no memory growth trend.

### Phase 8 — LSTM Sequence Aggregator
- **Depends on:** 7
- **Task:** `ai/lstm_attention.py` (LSTM part): PyTorch module taking `(Batch, Seq_Len, Embedding_Dim)`; configurable hidden size/layers; supports loading weights if present; flags `model_mode="heuristic"` when no trained weights are found (D10).
- **Spec refs:** SYS-6, D10, OQ-2.
- **Test:** dummy tensor forward pass; check output shapes and that absent weights yield heuristic mode, not an error.
- **Pass:** valid hidden-state outputs with the expected temporal dimensions.

### Phase 9 — Self-Attention Layer
- **Depends on:** 8
- **Task:** add additive/self-attention over LSTM hidden states; return both pooled vector and attention weights.
- **Spec refs:** SYS-7.
- **Test:** inspect attention weights on synthetic sequences with one injected anomalous frame (e.g., eyes closed for 3 frames).
- **Pass:** weights sum to 1.0 per sequence; the anomalous frames receive above-average weight *in a synthetic test where the model is fit to do so* — with untrained weights only the sum-to-1 and shape checks are asserted, and this limitation is logged.

### Phase 10 — Composite Scoring & Validation State Machine
- **Depends on:** 5, 6, 7, 9
- **Task:** `ai/scoring.py`: implement the heuristic formula and thresholds in CON §6 (all weights configurable), optional LSTM blend when `model_mode="lstm"`; implement smoothing, confidence gating and the state machine in CON §5; produce `TrackResult` (CON §2.1) and alert-candidate events.
- **Spec refs:** SYS-8, SYS-9, APP-8, CON §5–6.
- **Test:** simulate scripted inputs — baseline, sustained eye closure, sustained look-away, single closed-eye frame, low-confidence frames, occlusion; record resulting scores/statuses.
- **Pass:** score falls predictably in fatigue/distraction scenarios; a single closed frame never changes the displayed status or creates a candidate; low confidence → `Unknown`; results saved in `PROGRESS.md`.

---

# Track C — Backend

### Phase 11 — FastAPI Core Server & WebSocket Infrastructure
- **Depends on:** 10
- **Task:** `backend/app/main.py`: FastAPI app, `/health`, `/ws/telemetry` and `/ws/video` (closed with code 4403 when `PRIVACY_MODE=true`), connection manager with broadcast, ping/pong, config via environment.
- **Spec refs:** SYS-10, APP-24, APP-27, CON §4.
- **Test:** `TestClient` + pytest-asyncio WebSocket tests: multiple concurrent connections, ping→pong, privacy-mode rejection.
- **Pass:** server boots; concurrent sockets handled; ping/pong works; `/ws/video` refused in privacy mode.

### Phase 12 — Video Stream Processing Loop
- **Depends on:** 11
- **Task:** `ai/pipeline.py`: OpenCV capture (RTSP/USB/file) or mock frame generator → tracker → ROI → models → temporal → scoring → broadcast `telemetry` (and annotated `frame` only if allowed). Non-blocking design (separate capture/inference threads or tasks, bounded queue that drops old frames); camera-loss detection per `CAMERA_TIMEOUT_S`; AI heartbeat.
- **Spec refs:** SYS-1, SYS-17, APP-6, APP-20, CON §4–5.
- **Test:** 60-second end-to-end benchmark with a multi-face feed; log FPS, p95 latency, dropped frames; unplug-camera simulation.
- **Pass:** sustained ≥ `TARGET_FPS` (default 20) on declared hardware; camera loss sets state `Offline` within the timeout without crashing.

### Phase 13 — Database & Session Logging
- **Depends on:** 11 (can run in parallel with 12)
- **Task:** SQLAlchemy models + migrations (Alembic) for all tables in CON §7; session lifecycle (start/stop, automatic timestamps); observation aggregation every `OBSERVATION_INTERVAL_S`; retention job.
- **Spec refs:** SYS-12, APP-12, CON §7.
- **Test:** migration up/down; CRUD tests; FK/integrity violations; assert no image/BLOB columns exist.
- **Pass:** inserts/queries succeed, constraints enforced, sessions record start/end automatically.

### Phase 14 — Auth, Roles & REST API
- **Depends on:** 13
- **Task:** JWT login (`/auth/login`), password hashing, `teacher`/`admin` roles, dependency-based authorization on **every** route, teacher-classroom scoping, all endpoints in CON §3 except alerts and reports; `/system/status`; WebSocket token auth.
- **Spec refs:** APP-2, APP-3, APP-5, APP-7, APP-9, APP-12, APP-15–19, APP-26, CON §3.
- **Test:** endpoint tests per role: teacher → admin route returns 403; teacher → other teacher's classroom returns 403; invalid token 401; CRUD flows; start/stop session.
- **Pass:** all role matrix tests pass; no route is reachable without the intended role.

### Phase 15 — Alert Engine & Alert API
- **Depends on:** 10, 13, 14
- **Task:** convert confirmed candidates (Phase 10) into stored `Alert`s with cooldown; system alerts `camera_offline`/`ai_offline` for admins; `GET /alerts`, `PATCH /alerts/{id}`; push `alert` messages via `/ws/telemetry`.
- **Spec refs:** SYS-9, APP-10, APP-11, APP-20, APP-21, CON §2.3, CON §5.
- **Test:** scripted sessions produce expected alerts; cooldown suppresses duplicates; status transitions `New→Viewed→Resolved`; invalid transitions rejected; wording contains no diagnostic/disciplinary language.
- **Pass:** alerts appear once per condition, in correct role scopes, within 2 s of confirmation.

### Phase 16 — Export & Reporting Engine
- **Depends on:** 13, 14
- **Task:** session report builder (CON §8), `/reports`, `/reports/{id}`, `/reports/{id}/export?format=csv|pdf` (PDF via ReportLab or similar), required disclaimer footer.
- **Spec refs:** SYS-13, APP-13, APP-14, CON §8.
- **Test:** generate reports for a seeded session; parse CSV and PDF text; compare every count with the report JSON.
- **Pass:** valid, non-corrupt files whose aggregates equal the JSON exactly.

---

# Track D — Operator Console (web)

> All UI work follows `ui.md` (tokens only, all states, accessibility). Video shown only when the server permits it (D4).

### Phase 17 — Frontend Scaffolding (React + Tailwind + shadcn/ui)
- **Depends on:** 11
- **Task:** Vite/React + TypeScript project `operator-console/`; Tailwind configured with the tokens from `ui.md` (UI-2); shadcn/ui primitives; layout shell (sidebar, header, content); API/WS client modules typed from CON; login screen using `/auth/login`.
- **Spec refs:** UI, CON §3–4.
- **Test:** production build; lint; check no hardcoded hex/px outside the token file (simple grep rule in CI).
- **Pass:** build completes with zero warnings and missing-module errors; token lint passes.

### Phase 18 — Multi-Face Live Grid Component
- **Depends on:** 12, 17
- **Task:** canvas/grid component rendering annotated frames from `/ws/video` and drawing tracks' bounding boxes and `StatusBadge`s using the status-color mapping in UI-3; graceful "Video disabled (privacy mode)" state showing a tile-only view fed by `/ws/telemetry`.
- **Spec refs:** UI, SYS-11, CON §4.
- **Test:** mock WebSocket frames at target rate; measure dropped frames/long tasks; layout-shift check; privacy-mode rendering.
- **Pass:** smooth rendering with no freezing or layout shifts; correct fallback in privacy mode.

### Phase 19 — Real-Time Telemetry Charts & Analytics Panels
- **Depends on:** 17
- **Task:** Recharts panels: class attention trend, fatigue-frequency timeline, status distribution, per-student selection. Bounded client-side history (ring buffer) to prevent memory growth.
- **Spec refs:** UI, SYS-13, CON §2.4.
- **Test:** feed high-frequency telemetry mocks into the store; watch heap over a 10-minute simulated run.
- **Pass:** charts update in real time; no memory bloat; a11y text alternatives present.

### Phase 20 — Alert Log & Event Feed Widget
- **Depends on:** 15, 17
- **Task:** live feed showing timestamped alerts (e.g., "S004 — repeated fatigue indicators for > 45 s"), newest first, mark Viewed/Resolved, filter by status, `aria-live="polite"`.
- **Spec refs:** APP-11, UI, CON §2.3.
- **Test:** trigger mock and real alerts; verify ordering, auto-scroll rules, status PATCH calls, keyboard operation.
- **Pass:** alerts appear immediately in reverse-chronological order and obey states/accessibility checks.

---

# Track E — Mobile App (Teacher / Admin)

> Follows `application_behavior.md` screen-by-screen and the mobile token mapping in `ui.md` (UI-7). No video (D4).

### Phase 21 — Mobile Scaffolding, Auth & Navigation
- **Depends on:** 14
- **Task:** Expo + TypeScript app; secure token storage; login screen (APP-3) with role-based redirect; teacher and admin navigation (APP-22); API client + WebSocket client with reconnect; global error/offline banners (APP-25); `theme.ts` from `ui.md`.
- **Test:** run on emulator/device; Jest/React Native Testing Library tests for auth flow, role routing, offline banner; failed login message matches APP-25.
- **Pass:** teacher and admin land on correct navigation; token never stored in plain storage; offline state shown.

### Phase 22 — Teacher Screens
- **Depends on:** 15, 16, 21
- **Task:** dashboard (APP-5), classroom/monitoring status (APP-6), student list + detail (APP-7, APP-9), Alert Center with status actions (APP-10/11), session report and history (APP-13/14), profile.
- **Test:** component tests with mocked API/WS; scenario tests for empty, loading, error, offline; verify `Unknown` and alert wording.
- **Pass:** every screen implements all states; live dashboard updates from `/ws/telemetry`; teacher cannot reach admin screens.

### Phase 23 — Admin Screens & System Status
- **Depends on:** 14, 21
- **Task:** admin dashboard (APP-16), student/teacher/classroom management (APP-17–19), sessions, reports, camera/AI/system status (APP-20/21) with offline notifications.
- **Test:** CRUD flows against the test backend; status indicator simulations (camera offline, AI offline).
- **Pass:** CRUD works with validation errors surfaced; offline services clearly shown so "no alerts" is never misread.

---

# Track F — Release

### Phase 24 — End-to-End Integration & Stress Testing
- **Depends on:** 12, 16, 20, 23
- **Task:** `docker-compose.yml` (backend, database, operator-console, optional reverse proxy); simulated classroom with 20+ concurrent tracked faces / mock camera inputs; multi-client WebSocket load; long-run soak test (≥ 1 hour simulated).
- **Spec refs:** SYS-17, APP-29, APP-30.
- **Test:** automated integration suite + load script; track packet/telemetry loss, memory, FPS, error logs.
- **Pass:** no unhandled exceptions, no memory-growth trend, no telemetry loss beyond the documented tolerance, reports match stored data; measured capacity (max students at `TARGET_FPS`) recorded.

### Phase 25 — Production Hardening & Documentation Finalization
- **Depends on:** 24
- **Task:** `.env.example` (no secrets), secure defaults (`PRIVACY_MODE=true`, strong JWT secret required, CORS allow-list, TLS guidance, rate limiting on login), fallback/error handling, dependency vulnerability scan, log review for PII/images, final docs incl. privacy notice and consent checklist (OQ-5), license review (OQ-4), production build flags.
- **Spec refs:** SYS-14, APP-26, APP-27, APP-28.
- **Test:** security audit of env/config; `pip-audit`/`npm audit`; verify no image data in DB/logs; production startup sequence; role-matrix regression.
- **Pass:** clean security report, verified production boot, open questions either answered or explicitly documented as accepted risks.
