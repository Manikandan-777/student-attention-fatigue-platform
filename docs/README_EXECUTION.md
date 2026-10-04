# Execution Guide — Build the Student Attention & Fatigue Detection System Step by Step

> How to use this file: follow it top to bottom. It turns the project docs (`README.md`, `contracts.md`, `implementation.md`, etc.) into a single runnable checklist. Do **one phase at a time**, run its test, and only continue when it passes.

---

## 0. Before You Start

### 0.1 Put the docs in place

```text
project/
└─ docs/
   ├─ README.md                          (index + decisions D1–D10)
   ├─ system_work.md                     (concept, SYS-n)
   ├─ application_behavior.md            (product behavior, APP-n)
   ├─ contracts.md                       (names, schemas, APIs, thresholds)
   ├─ model_download_integration_plan.md (models, MDL-n)
   ├─ implementation.md                  (25 phases)
   └─ ui.md                              (design tokens, UI-n)
```

### 0.2 Reading order (once, before Phase 1)

| Order | File | Why |
|-------|------|-----|
| 1 | `README.md` | Decisions D1–D10, conflict rules, working protocol |
| 2 | `contracts.md` | Exact enums, JSON, endpoints, thresholds: use these names verbatim |
| 3 | `implementation.md` | The phase list you will execute |
| 4 | Others | Read only the **Spec refs** listed in the phase you are on |

### 0.3 Rules you must follow throughout

1. **One phase at a time**, in order, respecting *Depends on*.
2. **Never mark a phase done on "looks right."** Run its Test and compare to its Pass condition.
3. **Use only names from `contracts.md`** and **only design tokens from `ui.md`**.
4. **Thresholds go in config/env**, never hard-coded.
5. **If a test fails**, fix and re-run; do not start the next phase. If blocked by hardware or data, record `BLOCKED` with the reason.
6. **If docs conflict**, precedence is: README §3 decisions > `contracts.md` > `application_behavior.md` > `system_work.md` > everything else. For uncovered conflicts, write to `docs/OPEN_QUESTIONS.md` and pick the most conservative option (privacy-preserving, human-in-the-loop).

### 0.4 Key decisions to keep in mind

| ID | Rule |
|----|------|
| D1 | PyTorch stack; two pretrained HF models (no custom CNN); own LSTM + attention head |
| D2 | Model paths: `backend/models/drowsiness/` and `backend/models/expression/` |
| D4 | No video to mobile; video to web console only if `PRIVACY_MODE=false`; never persist frames or face crops |
| D5 | No face recognition; anonymous `S001…` track IDs |
| D6 | Frozen labels: `Attentive/Distracted/Unknown`, `Normal/Fatigued/Unknown` |
| D7 | Only validated (smoothed, confident, persistent) results are shown or alerted |
| D8 | Indicators, not diagnoses; never write "sleeping" or "sick" in UI copy |
| D10 | LSTM starts untrained, so scoring runs in `heuristic` mode until trained weights exist |

### 0.5 Prerequisites

- Python 3.10+ and `pip`
- Node.js 18+ (phases 17+)
- Git, and Docker + Docker Compose (phase 24)
- A webcam or sample video / mock frame generator for testing
- Internet access for Hugging Face downloads (phase 2)
- **Declare your hardware** (CPU only or GPU). The 15 ms/face and 20 FPS targets depend on it (OQ-3). Record it in `docs/PROGRESS.md`.

### 0.6 Progress log (create now)

Create `docs/PROGRESS.md` and append this block after **every** phase:

```markdown
## Phase N — <title>
- Status: PASS | FAIL | BLOCKED
- Files changed: ...
- Test command + result: ...
- Measured values (latency/FPS/etc.): ...
- Deviations from spec / new open questions: ...
```

Also create an empty `docs/OPEN_QUESTIONS.md`.

---

## Track A — Foundations

### Phase 1 — Environment & dependencies
**Depends on:** none

1. Create the repo layout:
   ```bash
   mkdir -p project/{docs,backend/{app/{api,ws,auth,db,reports},ai,models,scripts,tests},operator-console,mobile}
   cd project/backend
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```
2. Install packages:
   ```bash
   pip install torch torchvision transformers mediapipe fastapi uvicorn opencv-python \
               huggingface_hub sqlalchemy pytest pytest-asyncio httpx
   pip freeze > requirements.txt     # pin versions
   ```
3. Create `.gitignore` excluding `backend/models/**`, `.env`, `*.db`.
4. Write `scripts/check_env.py`: import every package, assert versions against `requirements.txt`, print Python version and CUDA availability.

**Test:** `python scripts/check_env.py`
**Pass:** zero import errors, all version assertions succeed.

---

### Phase 2 — Download & verify pretrained models
**Depends on:** 1 · **Spec refs:** MDL-1…MDL-5, OQ-4

1. Create `scripts/download_models.py` exactly as in `model_download_integration_plan.md` **MDL-3**.
2. Create `scripts/verify_models.py` per **MDL-4**. It must, for each model:
   - parse `config.json` and print `id2label`
   - confirm a weights file exists (`model.safetensors` or `pytorch_model.bin`)
   - read `preprocessor_config.json` (image size, mean, std)
   - load via `AutoModelForImageClassification` and run a dummy `(1,3,H,W)` tensor
   - check expression labels == the 7 `emotion` values in `contracts.md` §1
   - define a single `LABEL_MAP` constant (`ai/drowsiness.py::LABEL_MAP`) mapping to `Drowsy` / `Non Drowsy`
   - exit `0` on success, non-zero otherwise
3. Run:
   ```bash
   python scripts/download_models.py
   python scripts/verify_models.py
   ```
4. Check `backend/models/MANIFEST.json` contains repo, pinned revision and **license** for each model (needed for OQ-4).

**Pass:** both models load in PyTorch; label checks pass; exit code `0`. **Do not start Phase 3 until this passes.**

---

## Track B — AI Pipeline

### Phase 3 — MediaPipe multi-face pipeline with tracking
**Depends on:** 1 · **Spec refs:** SYS-2/3/4, CON §2.1

- Build `ai/mediapipe_tracker.py`: per-face bounding boxes, normalized landmarks, landmark confidence, stable anonymous `track_id`s (IoU/centroid matching with max-age for lost tracks).
- Build `ai/features.py`: EAR, MAR, head yaw/pitch from landmarks.
- Add test fixtures (synthetic or sample multi-face images/clips).

**Test:** run a multi-face clip through the tracker; assert ID stability across frames and that closed-eye EAR < open-eye EAR.
**Pass:** all fixture faces detected at ≥ 95% landmark confidence; IDs persist; no ID swaps.

### Phase 4 — Dynamic ROI cropping & alignment
**Depends on:** 3, 2 · **Spec refs:** MDL-5, SYS-5

- `ai/roi.py`: crop with margin, resize to the size in each model's `preprocessor_config.json` (224×224), normalize with the model's mean/std, return batched tensors.
- Handle boxes partly outside the frame; reject faces below `MIN_FACE_PX`.

**Test:** unit tests for shape, dtype, value bounds, out-of-frame boxes.
**Pass:** output `(Batch, 3, 224, 224)`; normalization matches the model; invalid crops are skipped, not crashed on.

### Phase 5 — MobileViT drowsiness wrapper
**Depends on:** 2, 4 · **Spec refs:** MDL-5, CON §2.1, CON §5

- `ai/drowsiness.py`: batch inference under `torch.inference_mode()` and `.eval()`; output `{label, p_drowsy}` via `LABEL_MAP`.

**Test:** open-eye vs closed-eye crops; measure per-face latency over ≥ 100 runs after warm-up.
**Pass:** closed → `Drowsy`, open → `Non Drowsy`; latency ≤ `MAX_INFER_MS_PER_FACE` (15 ms) on declared hardware. **Record the number.**

### Phase 6 — ViT expression wrapper
**Depends on:** 2, 4 · **Spec refs:** MDL-5, CON §6

- `ai/expression.py`: probability dict over exactly the 7 emotions, plus `top`.

**Test:** reference emotion images; assert key set, sum, and top label for clear examples.
**Pass:** 7 keys; probabilities sum to 1.0 (±1e-4).

### Phase 7 — Temporal history queue & feature window
**Depends on:** 3, 5, 6 · **Spec refs:** SYS-4, SYS-6, CON §5

- `ai/temporal.py`: per-`track_id` rolling buffer of the last `WINDOW_FRAMES` (30) feature vectors. Compute windowed PERCLOS, yawn fraction, off-task fraction. Purge tracks unseen for `TRACK_TTL_S`.

**Test:** push sequential mock frames for several tracks; run 100k pushes with track churn and watch memory.
**Pass:** window size constant; old frames and dead tracks purged; no memory growth trend.

### Phase 8 — LSTM sequence aggregator
**Depends on:** 7 · **Spec refs:** SYS-6, D10, OQ-2

- `ai/lstm_attention.py` (LSTM part): input `(Batch, Seq_Len, Embedding_Dim)`, configurable hidden size/layers, loads weights if present, otherwise flags `model_mode="heuristic"`.

**Test:** dummy forward pass; confirm missing weights gives heuristic mode, not an error.
**Pass:** valid hidden-state outputs with expected temporal dimensions.

### Phase 9 — Self-attention layer
**Depends on:** 8 · **Spec refs:** SYS-7

- Add additive/self-attention over LSTM states; return the pooled vector and attention weights.

**Test:** synthetic sequences with an injected anomaly (eyes closed for 3 frames).
**Pass:** weights sum to 1.0 per sequence. With untrained weights, assert only sum-to-1 and shape, and log that limitation.

### Phase 10 — Composite scoring & validation state machine
**Depends on:** 5, 6, 7, 9 · **Spec refs:** SYS-8/9, APP-8, CON §5–6

- `ai/scoring.py`: implement the heuristic formula from `contracts.md` §6 (all weights configurable), optional 50/50 LSTM blend when `model_mode="lstm"`.
- Implement EMA smoothing, `MIN_CONFIDENCE` gating and the state machine `Normal → Candidate → Confirmed → Alerted → Cleared`.
- Produce `TrackResult` (CON §2.1) and alert-candidate events.

**Test:** scripted scenarios: baseline, sustained eye closure, sustained look-away, **single closed-eye frame**, low-confidence frames, occlusion.
**Pass:** scores fall predictably in fatigue/distraction scenarios; a single closed frame never changes status or creates a candidate; low confidence → `Unknown`. Save the results in `PROGRESS.md`.

---

## Track C — Backend

### Phase 11 — FastAPI core & WebSocket infrastructure
**Depends on:** 10 · **Spec refs:** SYS-10, APP-24, APP-27, CON §4

- `backend/app/main.py`: `/health`, `/ws/telemetry`, `/ws/video` (close code **4403** when `PRIVACY_MODE=true`), connection manager with broadcast, ping/pong, env-based config.

**Test:** `TestClient` + pytest-asyncio: concurrent sockets, ping → pong, privacy-mode rejection.
**Pass:** server boots; concurrent sockets work; `/ws/video` refused in privacy mode.

```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
```

### Phase 12 — Video stream processing loop
**Depends on:** 11 · **Spec refs:** SYS-1, SYS-17, APP-6, APP-20

- `ai/pipeline.py`: OpenCV capture (RTSP/USB/file) or mock generator → tracker → ROI → models → temporal → scoring → broadcast `telemetry` (and annotated `frame` only if allowed).
- Non-blocking: separate capture/inference threads/tasks, bounded queue that drops old frames.
- Camera-loss detection (`CAMERA_TIMEOUT_S`) and AI heartbeat (`AI_HEARTBEAT_TIMEOUT_S`).

**Test:** 60-second end-to-end benchmark on a multi-face feed; log FPS, p95 latency, dropped frames; simulate camera unplug.
**Pass:** sustained ≥ `TARGET_FPS` (20); camera loss sets `Offline` within the timeout without crashing.

### Phase 13 — Database & session logging
**Depends on:** 11 (can run in parallel with 12) · **Spec refs:** SYS-12, APP-12, CON §7

- SQLAlchemy models + Alembic migrations for every table in `contracts.md` §7. **No BLOB/image columns.**
- Session start/stop with automatic timestamps; observation aggregation every `OBSERVATION_INTERVAL_S` (5 s); retention job (`RETENTION_DAYS`).

**Test:** migration up/down; CRUD; FK/integrity violations; assert no image/BLOB columns.
**Pass:** inserts and queries succeed; constraints enforced; sessions record start/end automatically.

### Phase 14 — Auth, roles & REST API
**Depends on:** 13 · **Spec refs:** APP-2/3/5/7/9/12/15–19/26, CON §3

- JWT login (`/auth/login`), password hashing, `teacher`/`admin` roles, authorization dependency on **every** route, teacher-classroom scoping.
- All CON §3 endpoints except alerts and reports; `/system/status`; WebSocket token auth.

**Test:** per-role endpoint tests: teacher → admin route = 403; teacher → another teacher's classroom = 403; bad token = 401; CRUD; start/stop session.
**Pass:** full role matrix passes; no route reachable without the intended role.

### Phase 15 — Alert engine & alert API
**Depends on:** 10, 13, 14 · **Spec refs:** SYS-9, APP-10/11/20/21, CON §2.3

- Convert confirmed candidates to stored `Alert`s with `ALERT_COOLDOWN_S`; emit admin-only `camera_offline` / `ai_offline`.
- `GET /alerts`, `PATCH /alerts/{id}`; push `alert` messages over `/ws/telemetry`.

**Test:** scripted sessions produce expected alerts; cooldown suppresses duplicates; `New → Viewed → Resolved` works; invalid transitions rejected; wording has no diagnostic/disciplinary language.
**Pass:** one alert per condition, in correct role scopes, within 2 s of confirmation.

### Phase 16 — Export & reporting engine
**Depends on:** 13, 14 · **Spec refs:** SYS-13, APP-13/14, CON §8

- Session report builder, `/reports`, `/reports/{id}`, `/reports/{id}/export?format=csv|pdf` (ReportLab for PDF).
- Every report carries the footer: *"AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."*

**Test:** generate reports for a seeded session; parse CSV and PDF text; compare every count to the report JSON.
**Pass:** valid files whose aggregates equal the JSON exactly.

---

## Track D — Operator Console (web)

> All UI work follows `ui.md`: tokens only, all component states, accessibility. Status is never color alone (color + icon + text).

```bash
cd project
npm create vite@latest operator-console -- --template react-ts
```

### Phase 17 — Frontend scaffolding
**Depends on:** 11 · **Spec refs:** UI, CON §3–4

- Tailwind configured from `ui.md` UI-2 tokens (`tokens.ts`); shadcn/ui primitives; layout shell (sidebar, header, content); typed API/WS clients; login screen.
- Add a CI lint that fails on hex/`px` literals outside the token file.

**Test:** production build, lint, token grep rule.
**Pass:** build has zero warnings or missing-module errors; token lint passes.

### Phase 18 — Multi-face live grid
**Depends on:** 12, 17 · **Spec refs:** UI, SYS-11, CON §4

- Canvas/grid rendering annotated frames from `/ws/video` with bounding boxes and `StatusBadge`s (UI-3 mapping).
- Privacy-mode fallback: "Video disabled (privacy mode)" tile view fed by `/ws/telemetry`.

**Test:** mock WebSocket frames at target rate; measure dropped frames, long tasks, layout shift; privacy-mode rendering.
**Pass:** smooth rendering, no freezes or layout shifts; correct fallback.

### Phase 19 — Real-time charts & analytics
**Depends on:** 17 · **Spec refs:** UI, SYS-13, CON §2.4

- Recharts panels: attention trend, fatigue timeline, status distribution, per-student selection. Client-side ring buffer for bounded history.

**Test:** feed high-frequency telemetry mocks; watch heap over a 10-minute simulated run.
**Pass:** real-time updates; no memory bloat; text alternatives for charts.

### Phase 20 — Alert log & event feed
**Depends on:** 15, 17 · **Spec refs:** APP-11, UI, CON §2.3

- Live feed, newest first, mark Viewed/Resolved, filter by status, `aria-live="polite"`.

**Test:** trigger mock and real alerts; verify ordering, scroll rules, PATCH calls, keyboard operation.
**Pass:** immediate reverse-chronological alerts; states and accessibility checks pass.

---

## Track E — Mobile App (teacher / admin)

> Follows `application_behavior.md` screen by screen and the mobile token mapping in `ui.md` UI-7. **No video on mobile (D4).** Mobile receives only `TrackResult-lite`.

```bash
cd project
npx create-expo-app mobile --template expo-template-blank-typescript
```

### Phase 21 — Mobile scaffolding, auth & navigation
**Depends on:** 14 · **Spec refs:** APP-3, APP-22, APP-25

- Secure token storage (e.g. `expo-secure-store`), login with role-based redirect, teacher/admin navigation, API + WebSocket clients with reconnect, global error/offline banners, `theme.ts` from `ui.md`.

**Test:** emulator/device run; Jest + React Native Testing Library for auth flow, role routing, offline banner; failed-login message matches APP-25.
**Pass:** correct navigation per role; token never in plain storage; offline state visible.

### Phase 22 — Teacher screens
**Depends on:** 15, 16, 21 · **Spec refs:** APP-5/6/7/9/10/11/13/14

- Dashboard, classroom/monitoring status, student list + detail, Alert Center with status actions, session report and history, profile.

**Test:** component tests with mocked API/WS; empty, loading, error and offline scenarios; verify `Unknown` and alert wording.
**Pass:** every screen implements all states; dashboard updates live from `/ws/telemetry`; teacher cannot reach admin screens.

### Phase 23 — Admin screens & system status
**Depends on:** 14, 21 · **Spec refs:** APP-16…21

- Admin dashboard, student/teacher/classroom management, sessions, reports, camera/AI/system status with offline notifications.

**Test:** CRUD flows against the test backend; simulate camera offline and AI offline.
**Pass:** CRUD works with validation errors surfaced; offline services clearly shown so "no alerts" is never misread.

---

## Track F — Release

### Phase 24 — End-to-end integration & stress testing
**Depends on:** 12, 16, 20, 23 · **Spec refs:** SYS-17, APP-29, APP-30

- Write `docker-compose.yml` (backend, database, operator-console, optional reverse proxy).
- Simulate 20+ concurrent tracked faces / mock cameras, multi-client WebSocket load, and a ≥ 1 hour simulated soak test.

```bash
docker compose up --build
```

**Test:** automated integration suite + load script; track telemetry loss, memory, FPS, error logs.
**Pass:** no unhandled exceptions, no memory-growth trend, telemetry loss within tolerance, reports match stored data. **Record measured capacity** (max students at `TARGET_FPS`).

### Phase 25 — Production hardening & documentation
**Depends on:** 24 · **Spec refs:** SYS-14, APP-26/27/28

- `.env.example` with no secrets; secure defaults (`PRIVACY_MODE=true`, strong JWT secret required, CORS allow-list, TLS guidance, login rate limiting).
- Dependency scan (`pip-audit`, `npm audit`); log review for PII/images; privacy notice and consent checklist (OQ-5); license review (OQ-4); production build flags.

**Test:** security audit of env/config; verify no image data in DB/logs; production boot; role-matrix regression.
**Pass:** clean security report; verified production boot; open questions answered or recorded as accepted risks.

---

## Dependency Map (quick reference)

```text
1 → 2 → 3 → 4 → 5 ┐
              └→ 6 ┴→ 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 ┬→ 17 → 18 → 19 → 20 ┐
                                                                     └→ 21 → 22 → 23 ─────┴→ 24 → 25
```

## Phase Checklist

| Done | Phase | Title |
|:----:|:-----:|-------|
| ☑ | 1 | Environment & dependencies |
| ☑ | 2 | Model download & verification |
| ☑ | 3 | MediaPipe multi-face + tracking |
| ☑ | 4 | ROI cropping & alignment |
| ☑ | 5 | MobileViT drowsiness wrapper |
| ☑ | 6 | ViT expression wrapper |
| ☑ | 7 | Temporal window |
| ☑ | 8 | LSTM aggregator |
| ☑ | 9 | Self-attention |
| ☑ | 10 | Scoring & validation state machine |
| ☑ | 11 | FastAPI core + WebSockets |
| ☑ | 12 | Video processing loop |
| ☑ | 13 | Database & sessions |
| ☑ | 14 | Auth, roles, REST API |
| ☑ | 15 | Alert engine & API |
| ☑ | 16 | Reports & export |
| ☑ | 17 | Console scaffolding |
| ☑ | 18 | Live grid |
| ☑ | 19 | Charts |
| ☑ | 20 | Alert feed |
| ☑ | 21 | Mobile scaffolding & auth |
| ☑ | 22 | Teacher screens |
| ☑ | 23 | Admin screens & status |
| ☑ | 24 | Integration & stress |
| ☑ | 25 | Hardening & docs |

## Open Questions Status

| ID | Question | Resolution / Status |
|----|----------|---------------------|
| OQ-1 | How are `S001…` tracks mapped to real students? | Stay anonymous per session (Settled; anonymous S001... tracks) |
| OQ-2 | Is labeled data available to train the LSTM/attention head? | Heuristic mode fallback with dynamic weight loading (Settled via D10) |
| OQ-3 | Target hardware (CPU vs GPU)? | Intel Core i5-12450H CPU (Measured: 11,626 student-frames/s; 465 effective FPS for 25 tracks) |
| OQ-4 | Are the two Hugging Face model licenses acceptable? | Cleared (Apache 2.0 / MIT permissive licenses verified in `docs/MODEL_LICENSES.md`) |
| OQ-5 | Consent/notification policy for students and guardians? | Complete (Institutional policy & checklist in `docs/PRIVACY_CONSENT_POLICY.md`) |

## Final Non-Negotiables (check before every release)

- No raw video, frames or face crops stored; none in logs; none sent to mobile.
- Role checks enforced server-side on every endpoint.
- Show `Unknown` rather than a low-quality guess.
- Every service exposes health, so "no alerts" is never confused with "AI is offline."
- Copy says "indicator" / "possible"; never a diagnosis or disciplinary statement.
