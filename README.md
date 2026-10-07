# Student Attention & Fatigue Detection Platform

> **Real-Time Edge AI Classroom Monitoring & Well-Being Indicator System**  
> *Camera Feed $\to$ MediaPipe Face Tracking $\to$ Vision Transformer Feature Extraction $\to$ Heuristic / Temporal Aggregation $\to$ FastAPI Backend $\to$ React Web Operator Console & React Native Mobile App.*

---

## 🧭 Key Documentation & Architecture Guides

| Guide | Description |
|---|---|
| **[docs/README_OPERATIONS.md](docs/README_OPERATIONS.md)** | **Operations Manual: Web & Mobile** — Comprehensive guide for operating the Web Operator Console and Mobile App independently and concurrently. |
| **[README_SYSTEM_FLOW_EXECUTION.md](README_SYSTEM_FLOW_EXECUTION.md)** | **Complete End-to-End System Flow Execution Manual** — Deep dive into 12 pipeline stages, thread architecture, WebSocket contracts, and operational runbook. |
| **[docs/README_EXECUTION.md](docs/README_EXECUTION.md)** | **Phase-by-Phase Build Guide** — Step-by-step checklist executing and verifying all 25 implementation phases. |
| **[docs/README_SECURITY.md](docs/README_SECURITY.md)** | **Security & Privacy Defense Manual** — Threat matrix, rate limiting (APP-26), and zero-raw-media compliance (D4/D5). |
| **[docs/README_1000_FACES.md](docs/README_1000_FACES.md)** | **Ultra-Scale 1,000-Face Live Benchmark** — High-density tracking architecture, optics, and 100% precision benchmark. |
| **[docs/README_MOBILE_FATIGUE_ALERTS.md](docs/README_MOBILE_FATIGUE_ALERTS.md)** | **Class Fatigue Advisory Alerts** — 4-tier pedagogical guidance engine and push notification specs for mobile devices. |
| **[docs/contracts.md](docs/contracts.md)** | **Data Contracts & APIs** — Frozen enums, REST endpoints, WebSocket schemas, and threshold definitions. |

---

## Highlights & Verified Status

- **Status:** **All 25 Phases Complete & Verified (150/150 Automated Tests Passing)**
- **Backend & AI Pipeline:** 111 Pytest unit, integration, stress, and security tests passing.
- **Web Operator Console:** 23 Vitest/RTL frontend tests passing.
- **Mobile App (Expo / React Native):** 16 Jest/RNTL tests passing across Scaffolding, Teacher, and Admin flows.
- **E2E Stress & Soak Benchmark:** **11,626.3 student-frames/s** across 25 concurrent student tracks (effective class frame rate: **465.1 FPS** vs 20 FPS target).
- **Soak Memory Stability:** 14,400 database records processed with memory drift of only **+0.072 MB** (< 2.0 MB threshold).

---

## 🔒 Security & Privacy Guarantees

Security and child data privacy are **core architectural non-negotiables** of this platform:

| Core Mandate | Specification | Implemented Defense |
|---|:---:|---|
| **Zero Raw Media Storage** | Decision D4 | Video frames, face crops, and bounding boxes are strictly processed in ephemeral RAM. Never written to disk, databases, or logs. |
| **Zero Biometric Identity** | Decision D5 | No face recognition or face embeddings. All students are tracked with session-ephemeral IDs (`S001`, `S002`, ...). |
| **Strict Privacy Default** | APP-27 | `PRIVACY_MODE=true` by default; WebSocket video streaming rejected with close code `4403`. Mobile app receives zero video under all conditions. |
| **Brute-Force Protection** | APP-26 | In-memory sliding window rate limiter locks out IPs after 5 failed login attempts per 5 minutes (`HTTP 429` with `Retry-After`). |
| **Non-Diagnostic Language** | Decision D8 | All UI copy and reports use supportive indicator terminology ("indicator", "possible"). No clinical or disciplinary classifications. |

---

## Repository Structure

```text
project/
├── .env.example                     # Zero-secret environment template (PRIVACY_MODE=true default)
├── docker-compose.yml               # Container orchestration (Backend + PostgreSQL 16 + Web Console)
├── README.md                        # Master repository guide
├── README_SYSTEM_FLOW_EXECUTION.md  # Complete End-to-End System Flow & Runtime Architecture
├── backend/
│   ├── ai/                          # Computer vision & PyTorch inference pipeline
│   │   ├── mediapipe_tracker.py     # Multi-face tracking (EAR, MAR, head pose, blink rate)
│   │   ├── drowsiness.py            # MobileViT-v2 drowsiness spatial feature extractor
│   │   ├── expression.py            # ViT facial expression feature extractor
│   │   ├── temporal.py              # Rolling window buffer (30 frames/track)
│   │   ├── scoring.py               # Attention Score (0-100) & Fatigue Index (0-1)
│   │   └── pipeline.py              # End-to-end multi-student inference engine
│   ├── app/                         # FastAPI application
│   │   ├── api/                     # REST endpoints (sessions, alerts, students, reports)
│   │   ├── auth/                    # JWT authentication, role guards & APP-26 rate limiter
│   │   ├── db/                      # SQLAlchemy 2.0 ORM & database models (zero BLOBs)
│   │   └── ws/                      # WebSocket real-time event and video streaming routers
│   ├── models/                      # Downloaded PyTorch weights & MANIFEST.json
│   ├── scripts/                     # Utility scripts (download_models.py, run_security_audit.py)
│   └── tests/                       # 111 Pytest unit, integration, stress, and hardening tests
├── operator-console/                # Web dashboard (React 19 + Tailwind CSS + Vite)
│   ├── src/                         # Components (LiveGrid, StudentTile, AlertFeed, Charts)
│   └── Dockerfile                   # Multi-stage Nginx container build
├── mobile/                          # Cross-platform mobile app (React Native + Expo SDK 52)
│   └── src/                         # Scaffolding, Teacher Dashboard, Admin Console, SecureStore Auth
└── docs/                            # Architectural specifications & compliance runbooks
    ├── contracts.md                 # Single source of truth for schemas, enums, endpoints
    ├── VULNERABILITY_CHECK.md       # Comprehensive vulnerability manual
    ├── DEPLOYMENT.md                # Production deployment runbook
    └── PROGRESS.md                  # Phase-by-phase execution logs (Phases 1-25)
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose (optional for containerized deployment)

### 2. Environment Setup
```bash
cp .env.example .env
```

### 3. Full Docker Deployment (All Services)
```bash
docker compose up --build
```
- **Web Operator Console:** `http://localhost:3000` (or port 80)
- **FastAPI Backend & Swagger API:** `http://localhost:8000/docs`
- **Healthcheck Endpoint:** `http://localhost:8000/health`

### 4. Running Tests
```bash
# Backend tests (111 passing)
cd backend && pytest tests -v

# Operator Console tests (23 passing)
cd ../operator-console && npm test

# Mobile App tests (16 passing)
cd ../mobile && npm test
```

---

## 🔑 Default Credentials & Role Matrix

| Role | Username | Password | Target User | Key Capabilities |
|---|---|---|---|---|
| **Admin** | `admin` | `adminpass` | Proctors, Lab In-Charges, IT Admins | Full institutional access: manage classrooms, bind cameras, register teachers & students, inspect system health, and review all reports. |
| **Teacher** | `teacher1` | `teachpass` | Classroom Faculty | Scoped access: view assigned classrooms (`Lab 101`), receive 4-level class fatigue advisories, view student indicators, and export session reports. |

To seed initial demo accounts, classrooms, and sample historical sessions:
```bash
cd backend
python scripts/seed_demo_data.py
```

---

## 🖥️ Operating via Web Operator Console

The **Web Operator Console** (`operator-console/`) is a React 19 + Tailwind CSS desktop interface for lab proctors, system operators, and institutional administrators.

### Local Setup & Launch:
```bash
cd operator-console
npm install
npm run dev      # Launches Vite dev server at http://localhost:5173
```

### Operational Workflow:
1. **Login (`/login`):** Sign in with `admin` / `adminpass` or `teacher1` / `teachpass`.
2. **Live Classroom Monitoring (`/`):**
   - **Health & Connection Banner:** Confirms WebSocket telemetry connection (`/ws/telemetry`). Alerts immediately if AI pipeline heartbeats drop or camera disconnects.
   - **Class Stat Cards:** High-level metrics showing Total Students, Attentive, Distracted, Fatigued, and Class Average Attention Score (0–100 scale).
   - **Live Student Grid:** 25+ student tiles with anonymous track IDs (`S001`...`S025`). Status chips: 🟢 **Attentive**, 🟡 **Distracted**, 🔴 **Fatigued**, ⚪ **Unknown**.
   - **Student Isolation:** Click any student tile to isolate their telemetry and plot their individual attention against the class average.
   - **Rolling 60-Second Charts:** Dynamic ring-buffer graphs for Attention Trends, Fatigue Timelines, and Categorical Distributions.
3. **Alert Management (`/alerts`):**
   - View real-time incoming alerts triggered by sustained fatigue ($\ge 45\text{ s}$) or distraction ($\ge 30\text{ s}$).
   - Operators can click **Mark Viewed** to acknowledge and **Mark Resolved** to clear the flag.
4. **Session Reports & Analytics (`/reports`):**
   - Review past completed sessions with attendance, peak fatigue timestamps, and per-student statistics.
   - One-click export to **CSV** or **PDF** with the required non-diagnostic disclaimer:
     > *"AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."*
5. **Privacy Mode Enforcement:**
   - By default (`PRIVACY_MODE=true`), raw video streaming is rejected (`/ws/video` returns code `4403`) to safeguard child privacy. Only anonymous telemetry cards are rendered.

---

## 📱 Operating via Mobile App (React Native / Expo)

The **Mobile App** (`mobile/`) is a React Native + Expo SDK 52 application designed for teachers moving freely in the lecture hall and on-the-go administrators.

> [!IMPORTANT]
> **Strict Zero-Video Mandate (Decision D4):** The mobile application **never** receives or streams raw video frames. It consumes only lightweight JSON telemetry, preserving student privacy and device battery.

### Local Setup & Launch:
```bash
cd mobile
npm install
npx expo start
```
- **Physical Phone:** Ensure phone and computer are on the same Wi-Fi. In [mobile/src/config.ts](file:///c:/Users/MANIKANDAN/OneDrive/Pictures/Desktop/Reverse%20Engineering/project/mobile/src/config.ts), change `localhost` to your computer's LAN IP (e.g. `http://192.168.1.50:8000`). Scan the terminal QR code with **Expo Go**.
- **Simulator / Web Preview:** Press `a` (Android Emulator), `i` (iOS Simulator), or `w` (Web browser preview at `http://localhost:8081`).

### Teacher Operational Flow (Login as `teacher1` / `teachpass`):
1. **Teacher Dashboard & 4-Level Fatigue Advisory:**
   - Rather than watching complex numbers while teaching, the backend aggregates class fatigue into four glanceable advisory recommendations:
     - 🟢 **Level 1 (0% to <25%):** *"Continue with the class."* — Normal engagement.
     - 🟡 **Level 2 (25% to <50%):** *"Make the session more interactive."* — Ask questions or initiate discussion.
     - 🟠 **Level 3 (50% to <75%):** *"Do a short activity or give a short break."* — Short stretch break or pace change.
     - 🔴 **Level 4 (75% to 100%):** *"Most students show fatigue indicators. Consider continuing the class tomorrow."* — High exhaustion across room.
   - Push / local notification fires only after holding $\ge 60\text{ s}$ (`ADVISORY_PERSIST_S`), with a 5-minute cooldown.
2. **Students Tab:** Scrollable roster with instant status badges (`Attentive`, `Distracted`, `Fatigued`) and attention scores. Tap any student to inspect individual indicators.
3. **Alerts Tab:** Mobile notification inbox for acute student-level fatigue flags with one-tap acknowledgment.
4. **Reports Tab:** Review past session summaries directly on the phone.
5. **Profile Tab:** View assigned classrooms and log out securely.

### Administrator Operational Flow (Login as `admin` / `adminpass`):
1. **Admin Dashboard:** Campus-wide overview across multiple active classrooms.
2. **Classrooms Tab:** Register rooms, set capacity, and bind camera IDs (`CAM-001`).
3. **Teachers Tab:** Provision faculty accounts, assign classrooms, or reset passwords.
4. **Students Tab:** Manage student rosters and student codes (`STU-001`).
5. **Status Tab:** Real-time platform health: live FPS (Target: 20 FPS), AI heartbeat, camera status, and privacy compliance.

---

## 🔄 Operating Web and Mobile Concurrently
## Real-Time Interface Deployment

During a typical classroom session, the system deploys two distinct interfaces operating simultaneously in real time to ensure comprehensive monitoring and immediate instructional support:

* **Web Operator Console:** Stationed at the lab proctor desk, this dashboard is optimized for continuous technical oversight. It monitors high-density 25-track video grids, tracks hardware frame rates, and manages the complete lifecycle of system alerts.
* **Teacher Mobile App:** Utilized actively by the instructor at the front of the room. This mobile-optimized application delivers glanceable Level 1–4 advisory banners and critical alert notifications, maintaining real-time situational awareness without introducing video-based distractions during the lecture.

For full technical specifications, network diagrams, and operational procedures, see **[docs/README_OPERATIONS.md](docs/README_OPERATIONS.md)**.

