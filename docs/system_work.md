# System Concept — AI-Based Student Attention and Fatigue Detection

> **Doc ID:** `SYS` · **Purpose:** explains *what* the system is and how the AI pipeline works conceptually.
> **Depends on:** `README.md` (decisions D1–D10) · **Names/schemas:** `contracts.md` · **Product behavior:** `application_behavior.md` · **Build steps:** `implementation.md`
> **Sections are referenced elsewhere as `SYS-n`.**

---

## SYS-0 Overview and Objective

A computer-vision + deep-learning system analyzes classroom camera video and estimates each student's **attention** and **fatigue** over time, without a teacher having to watch every student. AI runs on the **backend/AI server**. **Teachers/admins** see results through the **Mobile App** and the **Operator Console** (web); neither client runs AI (decision D3).

**Core pipeline:** MediaPipe Face Mesh (faces, landmarks, EAR/MAR/PERCLOS) + pretrained spatial models (MobileViT-v2 drowsiness, ViT expression) → temporal LSTM → self-attention → scoring/validation → backend API → database → dashboards.

The system should:
- Detect and track multiple faces in classroom video.
- Extract facial landmarks and derive EAR / MAR / PERCLOS / head pose.
- Extract spatial cues with pretrained models (D1).
- Model behavior across frames with LSTM; focus on important moments with attention.
- Output validated attention and fatigue statuses (contracts §1) plus scores.
- Generate alerts and reports; never replace teacher judgment (D8).

## SYS-1 Architecture

```text
 Classroom Camera / CCTV / file / mock generator
            │
            ▼
   Video Processing (OpenCV)                          ── Phase 12
            │
            ▼
   Face Detection + Tracking (MediaPipe + track IDs)   ── Phase 3
            │
            ▼
   Face Mesh landmarks ──► EAR / MAR / PERCLOS / head pose   ── Phases 3, 7
            │
            ▼
   ROI crop/normalize ──► MobileViT-v2 (drowsiness) + ViT (expression)   ── Phases 4–6
            │
            ▼
   Temporal window per track ──► LSTM ──► Self-attention     ── Phases 7–9
            │
            ▼
   Scoring + confidence filter + temporal validation         ── Phase 10
            │
   ┌────────┴────────┐
   ▼                 ▼
 Attention status   Fatigue status
   └────────┬────────┘
            ▼
   Backend API (FastAPI, WebSocket + REST) ──► Database      ── Phases 11, 13–16
            │
   ┌────────┴──────────────┐
   ▼                       ▼
 Operator Console (web)   Teacher/Admin Mobile App           ── Phases 17–20 / 21–23
```

## SYS-2 Camera Input and Face Detection

The camera produces a frame stream; the teacher does not operate it during monitoring. Each frame yields zero or more faces, each assigned an **anonymous `track_id`** (displayed `S001…`) so a temporal sequence can be kept per student (D5). The system does not identify who the person is.

## SYS-3 Facial Landmarks

MediaPipe Face Mesh (468+ landmarks per face) supports: eye movement and closure, mouth opening, head movement/position. Multiple faces per frame must be supported (`max_num_faces` ≥ expected class size, tuned per hardware).

## SYS-4 Landmark-Derived Features

| Feature | Meaning | Use |
|---------|---------|-----|
| **EAR** | Eye Aspect Ratio — eye open vs closed | blink/closure detection |
| **MAR** | Mouth Aspect Ratio | yawning |
| **PERCLOS** | Fraction of time eyes are mostly closed in a window | classic fatigue indicator |
| **Head pose (yaw/pitch)** | Orientation estimated from landmarks | looking away, head drop |

Computed in `ai/features.py` (Phases 3/7), stored in `TrackResult.features` (contracts §2.1).

## SYS-5 Spatial Feature Extraction (pretrained models — decision D1)

```text
Face ROI (224×224 tensor)
   ├─► MobileViT-v2  → p(Drowsy) / p(Non Drowsy)
   └─► ViT expression → 7 emotion probabilities
```

These per-frame outputs become the spatial part of the feature vector fed to the temporal model. See `model_download_integration_plan.md`. (Earlier drafts proposed training a custom CNN and using TensorFlow/Keras; that is superseded.)

## SYS-6 Temporal Analysis (LSTM)

Fatigue/attention cannot be judged from one frame. Per track, the last `WINDOW_FRAMES` feature vectors form a sequence:

```text
Normal eyes → partially closed → closed → repeated closure → possible fatigue
```

The LSTM (`ai/lstm_attention.py`, Phase 8) outputs a temporal representation. **Training status:** no labeled data is bundled (D10, OQ-2); until trained weights exist the system runs in `heuristic` mode (contracts §6).

## SYS-7 Attention Mechanism

An additive/self-attention layer (Phase 9) weights time steps so anomalous moments (sudden head drop, clustered long blinks) matter more than uneventful frames. Attention weights sum to 1.0 and are an internal signal, not displayed to teachers (APP-9).

## SYS-8 Classification and Scoring

Combined outputs produce (contracts §2.1, §6): `attention_score` (0–100), `fatigue_index` (0–1), `attention_status`, `fatigue_status`, `confidence`.

```text
Student S001  Attention: Attentive   Fatigue: Normal    Confidence: 94.2%
Student S015  Attention: Distracted  Fatigue: Fatigued  Confidence: 91.7%
```

Exact thresholds are configurable and must be tuned on real classroom data.

## SYS-9 Alert Generation and Validation

No alert from a single prediction (D7). Flow:

```text
Prediction → confidence ≥ MIN_CONFIDENCE → persists ≥ persist window
           → temporal validation (hysteresis) → Alert (with cooldown)
```

Reduces false alerts from blinking, brief head turns, or one misclassified frame. Exact state machine and defaults: `contracts.md` §5.

## SYS-10 Backend Responsibilities

Receive camera data; run inference; manage sessions; store **aggregated observations** (not frames); generate alerts; provide REST + WebSocket APIs; enforce authentication and role-based authorization. Endpoint list: `contracts.md` §3–4.

## SYS-11 Clients

- **Mobile App** (teachers/admins, React Native + Expo): consumes processed results only; no CNN/LSTM on device. Screens: `application_behavior.md`.
- **Operator Console** (web, React + Tailwind + shadcn/ui): live grid with annotated video (only when `PRIVACY_MODE=false`), telemetry charts, alert feed. Styling: `ui.md`.

Example teacher dashboard summary:

```text
Students: 45 | Attentive: 35 | Distracted: 7 | Fatigued: 3 | ⚠ 3 students need review
```

## SYS-12 Database

Stores users, students, classes, cameras, sessions, aggregated observations, alerts, reports (schema: `contracts.md` §7). **Raw video and face images are not stored** (D4).

## SYS-13 Reporting

Per-session summary: total students, average attention, repeated fatigue/distraction indicators, duration, alerts (schema: `contracts.md` §8; behavior: APP-13/14). Purpose: class-level patterns without continuous watching.

## SYS-14 Privacy and Security

- Restrict access to authorized users; backend-enforced roles.
- Secure API transport (TLS in production).
- No unnecessary raw-video/face-image storage; retention policy (`RETENTION_DAYS`).
- Do not expose facial imagery publicly; mobile receives no video.
- Obtain appropriate institutional consent/notification before real-world use (OQ-5).

## SYS-15 Technology Stack (updated)

| Layer | Choice |
|-------|--------|
| AI / ML | Python, **PyTorch**, torchvision, transformers/huggingface_hub, OpenCV, MediaPipe, NumPy (Pandas/Scikit-learn for reports/analysis) |
| Deep learning | Pretrained MobileViT-v2 + ViT; custom LSTM + attention (PyTorch) |
| Backend | **FastAPI** + Uvicorn, WebSockets, SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Operator Console | React + Tailwind CSS + shadcn/ui + Recharts |
| Mobile | React Native + Expo |
| Deployment | Docker Compose |

## SYS-16 Model Pipeline (single-line form)

`Input Video → Frames → Face Detection → Tracking → Face Mesh → Features (EAR/MAR/PERCLOS/pose) → ROI → MobileViT + ViT → Temporal window → LSTM → Attention → Scoring → Confidence filter → Temporal smoothing/validation → Attention + Fatigue result → Backend API → Database → Dashboards`

## SYS-17 Constraints and Limitations

Poor lighting; occlusion (masks, sunglasses, hands); extreme head angles; low resolution; small/distant faces; overlapping faces; hardware capacity; network latency. Maximum simultaneous students depends on hardware, inference latency, camera setup, and deployment — measure in Phases 12 and 24. Under these conditions output must degrade to `Unknown`, not guess.

## SYS-18 Expected Outcome and Future Work

Automated pipeline: **Capture → Detect → Track → Extract → Analyze → Predict → Validate → Report**. The goal is AI-assisted information that supports, not replaces, the teacher (D8).

Future: transformer-based temporal models, better tracking, edge inference, distributed GPU processing, adaptive thresholds, per-student baselines, long-term trends, offline inference, quantization, federated/privacy-preserving learning.

## SYS-19 Traceability (concept → where it is built)

| Concept | Phase(s) in `implementation.md` |
|---------|---------------------------------|
| SYS-2/3/4 detection, landmarks, features | 3, 7 |
| SYS-5 spatial models | 2, 4, 5, 6 |
| SYS-6/7 LSTM + attention | 8, 9 |
| SYS-8/9 scoring + validation | 10 |
| SYS-10 backend | 11–16 |
| SYS-11 clients | 17–23 |
| SYS-14 privacy/security | 14, 25 (and enforced throughout) |
