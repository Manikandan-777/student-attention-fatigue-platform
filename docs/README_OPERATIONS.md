# Operations Guide: Operating ClassAware via Web and Mobile

> **System:** Student Attention & Fatigue Detection Platform  
> **Architecture:** Edge AI Inference Engine $\to$ FastAPI Backend $\to$ Web Operator Console & Mobile App  
> **Privacy Mandates:** Zero raw media storage (D4), Zero biometric identities (D5), Strict privacy mode default (APP-27), Non-diagnostic supportive language (D8).

---

## Table of Contents

1. [System Overview & Operating Model](#1-system-overview--operating-model)
2. [Prerequisites & Initial Backend Startup](#2-prerequisites--initial-backend-startup)
3. [Default Credentials & Role Matrix](#3-default-credentials--role-matrix)
4. [Operating via Web Operator Console](#4-operating-via-web-operator-console)
   - [4.1 Starting the Web Console](#41-starting-the-web-console)
   - [4.2 Authentication & Session Flow](#42-authentication--session-flow)
   - [4.3 Live Monitoring Dashboard](#43-live-monitoring-dashboard)
   - [4.4 Real-Time Analytics & Trend Charts](#44-real-time-analytics--trend-charts)
   - [4.5 Alert Management & Lifecycle](#45-alert-management--lifecycle)
   - [4.6 Historical Analytics & Exporting Reports (CSV/PDF)](#46-historical-analytics--exporting-reports-csvpdf)
   - [4.7 Video Streaming & Privacy Mode Control](#47-video-streaming--privacy-mode-control)
5. [Operating via Mobile App (React Native / Expo)](#5-operating-via-mobile-app-react-native--expo)
   - [5.1 Starting the Mobile App](#51-starting-the-mobile-app)
   - [5.2 Target Environments (Physical Device, Simulator, Web)](#52-target-environments-physical-device-simulator-web)
   - [5.3 Network Configuration (LAN IP vs Localhost)](#53-network-configuration-lan-ip-vs-localhost)
   - [5.4 Teacher Operational Workflow](#54-teacher-operational-workflow)
     - [Teacher Dashboard & Live Snapshot](#teacher-dashboard--live-snapshot)
     - [Class Fatigue Advisory Engine (4 Advisory Levels)](#class-fatigue-advisory-engine-4-advisory-levels)
     - [Student Roster & Student Detail View](#student-roster--student-detail-view)
     - [Mobile Alert Center](#mobile-alert-center)
     - [Past Session Reports & Profile](#past-session-reports--profile)
   - [5.5 Administrator Operational Workflow](#55-administrator-operational-workflow)
     - [Admin Macro Dashboard](#admin-macro-dashboard)
     - [Classroom & Camera Binding](#classroom--camera-binding)
     - [Teacher & Student Management](#teacher--student-management)
     - [System Health & Hardware Diagnostics](#system-health--hardware-diagnostics)
6. [Operational Comparison Matrix (Web vs Mobile)](#6-operational-comparison-matrix-web-vs-mobile)
7. [Concurrent Operating Workflow (Proctor + Teacher)](#7-concurrent-operating-workflow-proctor--teacher)
8. [Troubleshooting & Operational FAQs](#8-troubleshooting--operational-faqs)

---

## 1. System Overview & Operating Model

The platform operates on a decoupled edge-cloud architecture designed to support two distinct operational interfaces:

```text
Classroom Cameras (CAM-001, CAM-002)
                │
                ▼
   AI Pipeline Server (Edge/Cloud)
  (MediaPipe + MobileViT-v2 + ViT)
                │
                ▼
       FastAPI Core Backend (Port 8000)
    ├── REST API (Session & Roster CRUD, Reports)
    ├── WebSocket Engine (/ws/telemetry, /ws/video)
    └── Database (SQLite dev / PostgreSQL prod)
         ▲                           ▲
         │                           │
         ▼                           ▼
Web Operator Console          Mobile Application
(React 19 + Tailwind + Vite)  (React Native + Expo SDK 52)
• Lab Proctors & SysAdmins    • Active Lecture Teachers & Admins
• High-density live telemetry • Glanceable 4-level advisory banner
• Temporal analytics charts   • Quick student indicators & alerts
• PDF / CSV formal exports    • Full offline resilience
• Optional local video debug  • Strictly ZERO video received (D4)
```

### Core Operating Principles
- **No Video to Mobile (Decision D4):** The mobile application strictly consumes lightweight numerical JSON telemetry (`ClassSnapshot` and `TrackResultLite`). It never requests or displays raw video frames under any configuration.
- **Privacy Shield on Web (Decision D4 & APP-27):** By default (`PRIVACY_MODE=true`), raw video streaming (`/ws/video`) is rejected with WebSocket close code `4403`. Face positions are represented by anonymous indicator cards.
- **Anonymous Track Identifiers (Decision D5):** Students are tracked using session-ephemeral IDs (`S001`, `S002`, ...). No facial recognition or biometric embeddings are stored.
- **Supportive Non-Diagnostic Guidance (Decision D8):** All UI statuses and alerts use non-clinical terminology ("fatigue indicator", "possible off-task").

---

## 2. Prerequisites & Initial Backend Startup

Before operating either the Web Console or the Mobile App, ensure the core backend API and database are running.

### 2.1 Start the FastAPI Backend

```bash
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Seed initial demo users, classrooms, and sessions
python scripts/seed_demo_data.py

# 5. Launch FastAPI server with Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Base URL: `http://localhost:8000`
- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Healthcheck Endpoint: `http://localhost:8000/health`

---

## 3. Default Credentials & Role Matrix

The system enforces role-based access control (RBAC). Use the seeded credentials below:

| Role | Username | Password | Accessible Interfaces | Key Permissions |
|---|---|---|---|---|
| **Admin** | `admin` | `adminpass` | Web Console & Mobile App | Full system access: manage teachers, classrooms, cameras, student rosters, system diagnostics, and all reports. |
| **Teacher** | `teacher1` | `teachpass` | Web Console & Mobile App | Scoped access: view assigned classrooms (`Lab 101`), start/stop sessions, live telemetry, receive fatigue advisories, and export reports. |

> [!WARNING]
> **Brute-Force Rate Limiting (APP-26):** If you enter incorrect credentials 5 times within a 5-minute sliding window, the backend rate limiter will temporarily lock your IP address with `HTTP 429 Too Many Requests`.

---

## 4. Operating via Web Operator Console

The **Web Operator Console** is engineered for high-density workstation monitoring by lab proctors, exam coordinators, and institutional administrators.

### 4.1 Starting the Web Console

```bash
# In a new terminal window:
cd operator-console

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Open your browser to: **`http://localhost:5173`** (or `http://localhost:3000` if running via Docker Compose).

---

### 4.2 Authentication & Session Flow

1. Navigate to `http://localhost:5173/login`.
2. Enter your credentials:
   - For proctor/administrator operations: `admin` / `adminpass`
   - For classroom operations: `teacher1` / `teachpass`
3. Click **Sign In**. Upon success, your JWT bearer token is stored in local storage and you are redirected to the **Live Dashboard**.

---

### 4.3 Live Monitoring Dashboard (`/`)

The Dashboard is the command center during active class monitoring:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ ClassAware Operator Console         [CAM-001: Online] [AI: Online] [WS: OK] │
├─────────────────────────────────────────────────────────────────────────────┤
│ [ Active: 25 ]  [ Attentive: 19 ]  [ Distracted: 4 ]  [ Fatigued: 2 ]       │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Live Student Grid (25 Tracks)        │ Real-Time Temporal Charts            │
│ ┌─────────┐ ┌─────────┐ ┌──────────┐ │ 📈 Class Attention Trend (60s)       │
│ │  S001   │ │  S002   │ │  S003    │ │                                      │
│ │ 88% Att │ │ 92% Att │ │ 42% Fat  │ │ 📉 Class Fatigue Timeline (60s)      │
│ └─────────┘ └─────────┘ └──────────┘ │                                      │
│ ┌─────────┐ ┌─────────┐ ┌──────────┐ │ 📊 Status Distribution               │
│ │  S004   │ │  S005   │ │  S006    │ │    [76% Attentive | 16% Dist | 8% Fat]│
│ │ 51% Dis │ │ 85% Att │ │ 90% Att  │ ├──────────────────────────────────────┤
│ └─────────┘ └─────────┘ └──────────┘ │ 🔒 Privacy Mode Active               │
│ (Click tile to lock inspection)      │ (Zero raw media streamed to browser) │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

#### Key Dashboard Components:
1. **Connection & Health Banner:**
   - Displays real-time status of the Telemetry WebSocket connection.
   - Alerts the operator immediately if the AI inference engine heartbeats drop or if a camera disconnects (`CAMERA_TIMEOUT_S=10`).
2. **Class Summary Stat Cards:**
   - **Active Students:** Total face tracks detected in the current frame.
   - **Attentive:** Students with attention score $> 55$.
   - **Distracted:** Students exhibiting off-task gaze or head orientation (`yaw/pitch > 25°`).
   - **Fatigued:** Students exhibiting sustained fatigue indicators (`fatigue_index ≥ 0.55`).
   - **Average Attention Score:** Aggregated 0–100 class engagement metric.
3. **Live Student Grid (`StudentTile`):**
   - Each tile shows the anonymous track label (e.g., `S003`), current status badge, and attention score.
   - **Status Badge Color Codes:**
     - 🟢 **Attentive** (Emerald): Normal eye openness, forward head pose, engagement detected.
     - 🟡 **Distracted** (Amber): Sustained off-task head yaw/pitch outside threshold for $> 3$ seconds.
     - 🔴 **Fatigued** (Rose): Elevated PERCLOS, prolonged eye closure (EAR $< 0.21$), or repeated yawning.
     - ⚪ **Unknown** (Slate): Face occluded or tracking confidence below `MIN_CONFIDENCE=0.80`.
4. **Student Inspection Lock:**
   - Click on any individual student tile in the grid to isolate that student's metrics.
   - The Attention Trend Chart dynamically plots the individual student's score in purple alongside the class average in teal.

---

### 4.4 Real-Time Analytics & Trend Charts

The right column maintains a rolling 60-second in-memory ring buffer (`RingBuffer<T>`):
- **Attention Trend Chart:** Visualizes real-time class attention fluctuations. Dips indicate potential loss of interest or difficult material.
- **Fatigue Timeline Chart:** Tracks the exact count of fatigued students over time, revealing periods of progressive exhaustion.
- **Distribution Chart:** Displays the proportional breakdown of attentive vs distracted vs fatigued students.

---

### 4.5 Alert Management & Lifecycle (`/alerts`)

Click **Alerts** in the top navigation bar to access the centralized alert feed:

1. **Viewing Alerts:**
   - Alerts are broadcast in real time over `/ws/telemetry` and loaded via `GET /alerts`.
   - Alert Types:
     - `fatigue`: Emitted when a student's fatigue condition persists for $\ge 45\text{ s}$ (`FATIGUE_PERSIST_S`).
     - `distraction`: Emitted when off-task behavior persists for $\ge 30\text{ s}$ (`DISTRACTION_PERSIST_S`).
     - `camera_offline` / `ai_offline`: Emitted to administrators if hardware or workers disconnect.
2. **Managing Alert States:**
   - **New:** Unread alert.
   - **Mark Viewed:** Acknowledges the operator has observed the flag.
   - **Mark Resolved:** Clears the alert after appropriate action has been taken.
   - Status updates are instantly synced to the database via `PATCH /alerts/{id}`.

---

### 4.6 Historical Analytics & Exporting Reports (CSV/PDF) (`/reports`)

Click **Reports** in the navigation bar to inspect completed sessions:

1. **Select a Past Session:** The left sidebar lists all completed classroom sessions with timestamps and student counts.
2. **Session Summary Breakdown:**
   - Overall class duration, student attendance, and average attention score.
   - Attention and fatigue categorical distributions.
   - Peak fatigue occurrence time and total alert count.
3. **Per-Student Telemetry Table:**
   - Displays student labels, individual attention means, fatigue indicator counts, and alerts triggered.
4. **Export Options:**
   - Click **Download CSV** to generate a spreadsheet for institutional record-keeping.
   - Click **Download PDF** to export a clean report with the compliance disclaimer:
     > *"AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."*

---

### 4.7 Video Streaming & Privacy Mode Control

- **Default Safe State (`PRIVACY_MODE=true`):**
  - All video frames and face crops remain in volatile server RAM and are discarded immediately after inference.
  - Attempting to connect to `/ws/video` returns close code `4403 Forbidden`.
  - The Web Console shows anonymous telemetry tiles.
- **Authorized Testing Mode (`PRIVACY_MODE=false`):**
  - Configured via `.env` for local camera calibration and lab testing.
  - Video stream opens over `/ws/video`, displaying live JPEG frames with color-coded bounding boxes and facial landmark overlays.

---

## 5. Operating via Mobile App (React Native / Expo)

The **ClassAware Mobile App** is designed for teachers moving freely around the lecture hall, as well as administrators needing on-the-go institutional management.

> [!IMPORTANT]
> **Zero Video Mandate (Decision D4):** The mobile application **never** receives or streams video. It operates exclusively on lightweight JSON telemetry.

---

### 5.1 Starting the Mobile App

```bash
# In a new terminal window:
cd mobile

# Install dependencies
npm install

# Start the Expo Metro development server
npx expo start
```

---

### 5.2 Target Environments (Physical Device, Simulator, Web)

Once the Expo CLI starts, you can launch the app in any of the following targets:

| Target | Command | Instructions |
|---|:---:|---|
| **Physical Phone (Android/iOS)** | Scan QR Code | Install **Expo Go** from Google Play or App Store. Ensure your phone is connected to the same Wi-Fi network as your computer, then scan the terminal QR code. |
| **Android Emulator** | Press `a` | Requires Android Studio with an active Android Virtual Device (AVD). |
| **iOS Simulator** | Press `i` | Requires macOS with Xcode installed. |
| **Mobile Web Preview** | Press `w` | Opens the mobile interface in your desktop browser at `http://localhost:8081`. |

---

### 5.3 Network Configuration (LAN IP vs Localhost)

When running the mobile app on a **physical smartphone**:
1. Check your computer's local Wi-Fi IP address (e.g. `192.168.1.50`).
2. Open [mobile/src/config.ts](file:///c:/Users/MANIKANDAN/OneDrive/Pictures/Desktop/Reverse%20Engineering/project/mobile/src/config.ts).
3. Update `API_BASE_URL` and `WS_BASE_URL`:
   ```typescript
   // Use your computer's local IP when testing on a physical phone:
   export const API_BASE_URL = 'http://192.168.1.50:8000';
   export const WS_BASE_URL = 'ws://192.168.1.50:8000';
   export const WS_TELEMETRY_URL = `${WS_BASE_URL}/ws/telemetry`;
   ```
4. Save the file; Expo Metro bundler will fast-refresh automatically.

---

### 5.4 Teacher Operational Workflow

Log in using teacher credentials: **`teacher1`** / **`teachpass`**.

The mobile app automatically mounts the **Teacher Tab Navigator** (`Dashboard`, `Students`, `Alerts`, `Reports`, `Profile`).

```text
┌─────────────────────────────────────────┐
│ 9:41                             ClassAware│
├─────────────────────────────────────────┤
│ Good Morning, Prof. Sarah Jenkins       │
│ Classroom: Lab 101 • III AI & DS        │
├─────────────────────────────────────────┤
│ 💡 CLASS FATIGUE ADVISORY               │
│ ┌─────────────────────────────────────┐ │
│ │ 🟠 LEVEL 3: SHORT BREAK             │ │
│ │ "Do a short activity or give a      │ │
│ │ short break."                       │ │
│ │ (Class Fatigue: 62% • 21 students)  │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ CLASS SUMMARY                           │
│  [ Attentive: 14 ]   [ Distracted: 4 ]  │
│  [ Fatigued: 7 ]     [ Avg Score: 68% ] │
├─────────────────────────────────────────┤
│ QUICK ACTIONS                           │
│ [ 👥 Student Roster ] [ 🔔 Alert Center]│
├─────────────────────────────────────────┤
│ [🏠 Dashboard] [👥 Students] [🔔 Alerts] │
└─────────────────────────────────────────┘
```

#### Teacher Dashboard & Live Snapshot
- Displays the active session status, classroom name, and student count.
- Shows live counts of attentive, distracted, and fatigued students.

#### Class Fatigue Advisory Engine (4 Advisory Levels)
The standout mobile feature is the **Class Fatigue Advisory Banner**. Rather than forcing the teacher to watch individual numbers while lecturing, the backend aggregates class fatigue and displays one of four clear pedagogical recommendations:

| Class Fatigue Score | Level | Visual Badge | Advisory Message | Recommended Teacher Action |
|:---:|:---:|:---:|---|---|
| **0% to < 25%** | **1** | 🟢 Green | **"Continue with the class."** | Lecture is proceeding smoothly with high student engagement. |
| **25% to < 50%** | **2** | 🟡 Yellow | **"Make the session more interactive."** | Ask questions, invite student participation, or initiate a discussion. |
| **50% to < 75%** | **3** | 🟠 Orange | **"Do a short activity or give a short break."** | Give a 2-minute stretch break, run a quick poll, or change the delivery pace. |
| **75% to 100%** | **4** | 🔴 Red | **"Most students show fatigue indicators. Consider continuing the class tomorrow."** | High cognitive exhaustion detected across the room. Reorganize schedule. |

> [!NOTE]
> **Anti-Flicker & Hysteresis Rules:**
> - To avoid distracting notifications, the advisory level only changes after holding for $\ge 3\text{ seconds}$ (`STATUS_HYSTERESIS_S`).
> - Push notifications are delivered only when an elevated level persists for $\ge 60\text{ seconds}$ (`ADVISORY_PERSIST_S`).
> - A cooldown window of 5 minutes (`ALERT_COOLDOWN_S=300`) prevents repeated buzzing.

#### Student Roster & Student Detail View
1. Tap the **Students** tab.
2. View the full list of detected students with their track labels (`S001`, `S002`), current status badge, and attention scores.
3. Tap any student card to open the **Student Detail Screen**:
   - Real-time attention score meter.
   - Fatigue indicators breakdown (blink rate, yaw/pitch status).
   - Direct link to past performance reports.
   - Non-diagnostic disclaimer footer.

#### Mobile Alert Center
- Tap the **Alerts** tab to view urgent individual fatigue or distraction notifications.
- Tap any alert to view details or tap **Resolve** to dismiss.

#### Past Session Reports & Profile
- Tap **Reports** to review end-of-class engagement scores and historical trends.
- Tap **Profile** to view assigned classrooms, check server connection status, or log out securely.

---

### 5.5 Administrator Operational Workflow

Log in using administrator credentials: **`admin`** / **`adminpass`**.

The mobile app detects the `admin` role and loads the **Admin Management Navigator** (`Dashboard`, `Students`, `Teachers`, `Classrooms`, `Status`, `Profile`).

#### Admin Macro Dashboard
- Displays institution-wide statistics across all active classrooms.
- Real-time aggregate indicators of total active students, active classrooms, and system alerts.

#### Classroom & Camera Binding
- Tap **Classrooms** to view all registered rooms (`Lab 101`, `Hall 204`).
- Add new classrooms, assign room capacities, and bind physical camera hardware IDs (`CAM-001`, `CAM-002`, RTSP URIs).

#### Teacher & Student Management
- Tap **Teachers** to provision new faculty accounts, assign/unassign teaching classrooms, or reset passwords.
- Tap **Students** to manage the student enrollment roster, assign classes, and maintain student codes (`STU-001`).

#### System Health & Hardware Diagnostics
- Tap **Status** to inspect real-time platform diagnostics:
  - **Inference FPS:** Live frame processing rate (Target: 20 FPS).
  - **AI Server Status:** Heartbeat monitor (`Online` / `Offline`).
  - **Camera States:** Individual camera stream integrity.
  - **Privacy Enforcement:** Confirms `PRIVACY_MODE=true` is actively shielding raw camera feeds.

---

## 6. Operational Comparison Matrix (Web vs Mobile)

| Dimension | Web Operator Console | Mobile Application |
|---|---|---|
| **Primary Audience** | Lab Proctors, Operations Staff, SysAdmins | Active Classroom Teachers, School Administrators |
| **Typical Hardware** | Desktop workstation / Dual-monitor setup | Smartphone (iOS / Android) or Tablet |
| **Video Capability** | Blocked by default; enabled in testing mode | **Strictly ZERO video under all conditions (D4)** |
| **Telemetry Density** | High (full grid, temporal charts, ring buffers) | Focused & glanceable (4-level advisory, summary cards) |
| **Primary Interaction** | Monitoring continuous stream, managing alerts, exporting reports | Quick glances during teaching, responding to advisory notifications |
| **Alert Delivery** | Audio chime & visual feed on dashboard | Push notifications & haptic vibration |
| **Report Export** | Direct CSV and PDF document generation | Read-only summary review on screen |
| **Admin Operations** | System status, reports, and alerts | Full mobile CRUD for classrooms, teachers, and students |

---

## 7. Concurrent Operating Workflow (Proctor + Teacher)

In a typical institutional deployment, the Web Console and Mobile App operate simultaneously during a class session:

```text
       ┌────────────────────────┐
       │   Classroom Camera     │
       └───────────┬────────────┘
                   ▼
       ┌────────────────────────┐
       │   FastAPI + AI Engine  │
       └──────┬──────────┬──────┘
              │          │
    WebSocket │          │ WebSocket
   /ws/telemetry         │ /ws/telemetry
              │          │
              ▼          ▼
   ┌───────────────────┐ ┌───────────────────┐
   │Web Operator Desk  │ │Teacher Mobile App │
   │                   │ │                   │
   │ Proctors observe  │ │ Teacher glances   │
   │ the full 25-track │ │ at Level 2/3      │
   │ grid, monitors    │ │ advisory, pauses  │
   │ camera FPS, and   │ │ for interactive   │
   │ handles alerts.   │ │ discussion.       │
   └───────────────────┘ └───────────────────┘
```

1. **Session Initialization:**
   - The proctor on the Web Console or the teacher on Mobile starts the session for `Lab 101`.
   - The backend transitions session state to `Monitoring`.
2. **Synchronized Telemetry Fan-Out:**
   - Every 500 ms (`TELEMETRY_HZ=2`), the backend computes smoothed scores and broadcasts `ClassSnapshot` and `TrackResultLite` to both clients.
3. **Coordinated Response:**
   - When multiple students begin showing signs of fatigue, the teacher's mobile screen shifts to **Level 3: "Do a short activity or give a short break."**
   - Meanwhile, the Web Operator Console flags student tiles `S003` and `S007` in red, allowing the proctor to log the event.
4. **Session Wrap-Up:**
   - The session is stopped. The backend records final metrics and generates the session summary.
   - The proctor exports the official PDF report from the Web Console for institutional archival.

---

## 8. Troubleshooting & Operational FAQs

### Q1: The mobile app says "Network request failed" or cannot connect to WebSocket.
- **Cause:** Mobile device is attempting to reach `localhost:8000`, which refers to the phone itself rather than your host computer.
- **Fix:** Update `mobile/src/config.ts` to replace `localhost` with your computer's local network IP (e.g. `http://192.168.1.50:8000`). Ensure your phone and computer are on the same Wi-Fi network and port 8000 is open in your OS firewall.

### Q2: Why is the video stream blank or returning WebSocket code 4403?
- **Cause:** The system is operating in strict **Privacy Mode** (`PRIVACY_MODE=true`), which is the mandatory non-negotiable default.
- **Fix:** This is intended behavior. The platform protects student privacy by blocking video streaming and rendering anonymous telemetry cards instead. For local authorized hardware testing only, set `PRIVACY_MODE=false` in `.env` and restart the backend.

### Q3: My account got locked with "HTTP 429 Too Many Requests".
- **Cause:** Rate limiting defense (APP-26) triggered after 5 consecutive failed login attempts.
- **Fix:** Wait 5 minutes for the sliding window to expire, or restart the backend server to flush in-memory attempt counters during development.

### Q4: The Web Dashboard shows "AI Engine: Offline".
- **Cause:** The AI inference pipeline has not emitted a heartbeat within `AI_HEARTBEAT_TIMEOUT_S=10`.
- **Fix:** Ensure PyTorch and MediaPipe are running and the camera source (e.g. webcam `0` or test video) is supplying frames.

### Q5: Can a teacher see video on their mobile phone?
- **Answer:** **No.** Under no circumstances does the mobile app receive or render video feeds. This is an intentional architectural safeguard (Decision D4) to preserve student privacy and battery life.

---

## Summary Command Reference

```bash
# ---------------------------------------------------------------------------
# Terminal 1: Backend API & AI Engine
# ---------------------------------------------------------------------------
cd backend
.\.venv\Scripts\activate            # Windows (or: source .venv/bin/activate)
python scripts/seed_demo_data.py   # Seed demo accounts & classrooms
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ---------------------------------------------------------------------------
# Terminal 2: Web Operator Console
# ---------------------------------------------------------------------------
cd operator-console
npm install
npm run dev                        # Opens http://localhost:5173

# ---------------------------------------------------------------------------
# Terminal 3: Mobile Application
# ---------------------------------------------------------------------------
cd mobile
npm install
npx expo start                     # Press 'a' (Android), 'i' (iOS), or 'w' (Web)
```
