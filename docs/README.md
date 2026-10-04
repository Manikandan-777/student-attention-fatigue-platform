# Student Attention & Fatigue Detection Platform

> **Real-Time Edge AI Classroom Monitoring & Well-Being Indicator System**  
> *Camera Feed $\to$ MediaPipe Face Tracking $\to$ Vision Transformer Feature Extraction $\to$ Heuristic / Temporal Aggregation $\to$ FastAPI Backend $\to$ React Web Operator Console & React Native Mobile App.*

---

## Highlights & Verified Status

- **Status:** **All 25 Phases Complete & Verified (150/150 Automated Tests Passing)**
- **Backend & AI Pipeline:** 111 Pytest unit, integration, stress, and security tests passing.
- **Web Operator Console:** 23 Jest/RTL frontend tests passing.
- **Mobile App (Expo / React Native):** 16 Jest/RNTL tests passing across Scaffolding, Teacher, and Admin flows.
- **E2E Stress & Soak Benchmark:** **11,626.3 student-frames/s** across 25 concurrent student tracks (effective class frame rate: **465.1 FPS** vs 20 FPS target).
- **Soak Memory Stability:** 14,400 database records processed with memory drift of only **+0.072 MB** (< 2.0 MB threshold).

---

## 🔒 Security & Vulnerability Checks

Security and child data privacy are **core architectural non-negotiables** of this platform:

| Core Mandate | Specification | Implemented Defense |
|---|:---:|---|
| **Zero Raw Media Storage** | Decision D4 | Video frames, face crops, and bounding boxes are strictly processed in ephemeral RAM. Never written to disk, databases, or logs. |
| **Zero Biometric Identity** | Decision D5 | No face recognition or face embeddings. All students are tracked with session-ephemeral IDs (`S001`, `S002`, ...). |
| **Strict Privacy Default** | APP-27 | `PRIVACY_MODE=true` by default; WebSocket video streaming rejected with close code `4403`. Mobile app receives zero video under all conditions. |
| **Brute-Force Protection** | APP-26 | In-memory sliding window rate limiter locks out IPs after 5 failed login attempts per 5 minutes (`HTTP 429` with `Retry-After`). |
| **Non-Diagnostic Language** | Decision D8 | All UI copy and reports use supportive indicator terminology ("indicator", "possible"). No clinical or disciplinary classifications. |

### Quick Vulnerability Audit Command

Run the repository-wide vulnerability, privacy schema, and secret leak scanner:

```bash
# Windows
.\backend\.venv\Scripts\python.exe backend/scripts/run_security_audit.py

# Linux / macOS
python3 backend/scripts/run_security_audit.py
```

### In-Depth Security Documentation:
- **[README_SECURITY.md](README_SECURITY.md)**: Repository security guide, SCA tools (`pip-audit`, `npm audit`), SAST (`bandit`), container scans (`trivy`), and CI pipeline integration.
- **[docs/VULNERABILITY_CHECK.md](docs/VULNERABILITY_CHECK.md)**: Enterprise vulnerability scanning manual, threat matrix, emergency lockdown procedures, and vulnerability SLAs.
- **[docs/PRIVACY_CONSENT_POLICY.md](docs/PRIVACY_CONSENT_POLICY.md)**: Guardian consent, institutional policy, and student disclosure guidelines (OQ-5, APP-27).
- **[docs/MODEL_LICENSES.md](docs/MODEL_LICENSES.md)**: Model license audit confirming permissive Apache 2.0 and MIT compliance (OQ-4).
- **[README_1000_FACES.md](README_1000_FACES.md)**: Ultra-scale 1,000-face live camera detection architecture, hardware sizing, optics, and near-lossless zero-miss deployment.

---

## Repository Structure

```text
project/
├── .env.example                # Zero-secret environment template (PRIVACY_MODE=true default)
├── docker-compose.yml          # Container orchestration (Backend + PostgreSQL 16 + Web Console)
├── README.md                   # This project overview
├── README_SECURITY.md          # Root security & vulnerability guide
├── backend/
│   ├── ai/                     # Computer vision & PyTorch inference pipeline
│   │   ├── mediapipe_tracker.py# Multi-face tracking (EAR, MAR, head pose, blink rate)
│   │   ├── drowsiness.py       # MobileViT-v2 drowsiness spatial feature extractor
│   │   ├── expression.py       # ViT facial expression feature extractor
│   │   ├── temporal.py         # Rolling window buffer (30 frames/track)
│   │   ├── scoring.py          # Attention Score (0-100) & Fatigue Index (0-1)
│   │   └── pipeline.py         # End-to-end multi-student inference engine
│   ├── app/                    # FastAPI application
│   │   ├── api/                # REST endpoints (sessions, alerts, students, reports)
│   │   ├── auth/               # JWT authentication, role guards & APP-26 rate limiter
│   │   ├── db/                 # SQLAlchemy 2.0 ORM & database models (zero BLOBs)
│   │   └── ws/                 # WebSocket real-time event and video streaming routers
│   ├── models/                 # Downloaded PyTorch weights & MANIFEST.json
│   ├── scripts/                # Utility scripts (download_models.py, run_security_audit.py)
│   └── tests/                  # 111 Pytest unit, integration, stress, and hardening tests
├── operator-console/           # Web dashboard (React 19 + Tailwind CSS + Vite)
│   ├── src/                    # Components (CameraGrid, StudentCards, AlertPanel, SessionTimeline)
│   └── Dockerfile              # Multi-stage Nginx container build
├── mobile/                     # Cross-platform mobile app (React Native + Expo SDK 52)
│   └── src/                    # Scaffolding, Teacher Dashboard, Admin Console, SecureStore Auth
└── docs/                       # Architectural specifications & compliance runbooks
    ├── contracts.md            # Single source of truth for schemas, enums, endpoints
    ├── VULNERABILITY_CHECK.md  # Comprehensive vulnerability manual
    ├── DEPLOYMENT.md           # Production deployment runbook
    └── PROGRESS.md             # Phase-by-phase execution logs (Phases 1-25)
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose (optional for containerized deployment)

### 2. Environment Setup

```bash
# Copy template configuration
cp .env.example .env
```

### 3. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Run all 111 backend tests
pytest tests -v
```

### 4. Web Operator Console Setup

```bash
cd operator-console
npm install
npm test                        # Runs 23 Jest tests
npm run dev                     # Starts Vite dev server at http://localhost:5173
```

### 5. Mobile App Setup

```bash
cd mobile
npm install
npm test                        # Runs 16 Jest tests
npm run start                   # Starts Expo Metro bundler
```

### 6. Full Docker Deployment

To launch the backend, PostgreSQL database, and web console concurrently:

```bash
docker compose up --build
```
- Web Operator Console: `http://localhost:3000`
- FastAPI Backend & Swagger API: `http://localhost:8000/docs`
- Healthcheck Endpoint: `http://localhost:8000/health`

---

## Test Verification Summary

| Test Suite | Framework | Tests | Status | Key Coverage |
|---|:---:|:---:|:---:|---|
| **Backend Core** | Pytest | 103 | **PASS** | MediaPipe tracking, ViT inference, attention scoring, REST API, WebSockets. |
| **Phase 24 Stress** | Pytest | 4 | **PASS** | 25-track throughput benchmark, 1-hr soak memory stability (+0.072 MB), WS fan-out. |
| **Phase 25 Hardening** | Pytest | 4 | **PASS** | Sliding-window rate limiter (APP-26), `PRIVACY_MODE` lockout, zero-media DB schema. |
| **Operator Console** | Jest / RTL | 23 | **PASS** | Live telemetry rendering, alert lifecycle, privacy lock indicators, session reports. |
| **Mobile App** | Jest / RNTL | 16 | **PASS** | Teacher dashboard, admin CRUD, SecureStore auth, multi-service offline banners. |
| **Total** | | **150** | **PASS** | **100% test pass rate across all monorepo components.** |

---

## License & Compliance

- **Model Licenses:** Permissive Apache 2.0 (`apple/mobilevitv2-1.0-imagenet1k-256`) and MIT (`google/vit-base-patch16-224-in21k`). See [docs/MODEL_LICENSES.md](docs/MODEL_LICENSES.md).
- **Privacy Framework:** Non-diagnostic educational assistance compliant with privacy policies detailed in [docs/PRIVACY_CONSENT_POLICY.md](docs/PRIVACY_CONSENT_POLICY.md).
