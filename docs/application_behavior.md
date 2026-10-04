# Application Behavior & Functional Specification

> **Doc ID:** `APP` · **Purpose:** defines how the product must *behave* for teachers and admins (roles, screens, alerts, errors, security, privacy).
> **Depends on:** `README.md` (decisions D3–D8) · **Names, enums, endpoints, schemas:** `contracts.md` · **Concept:** `system_work.md` · **Built in phases:** 13–16 (backend) and 21–23 (mobile) of `implementation.md` · **Styling:** `ui.md`
> **Sections are referenced elsewhere as `APP-n`.** Status words in mock-ups must use the frozen enums in `contracts.md` §1 (`Attentive`/`Distracted`/`Unknown`, `Normal`/`Fatigued`/`Unknown`).

## APP-1 Application Overview

The application is a classroom monitoring platform where the **AI system performs video analysis automatically**, while the **Teacher and Admin mobile application displays the processed results**.

The teacher does **not** continuously monitor the camera through the mobile application. (A separate web **Operator Console**, `implementation.md` phases 17–20, may show annotated live video to authorized users on the local network; the mobile app never receives video — decision D4.) The camera and AI processing operate independently, and the mobile application receives the analyzed results through the backend API.

### Main Flow

```text
Classroom Camera
       ↓
AI Processing Server
       ↓
Face Detection & Tracking
       ↓
Attention + Fatigue Analysis
       ↓
Backend API
       ↓
Database
       ↓
Teacher / Admin Mobile App
```

---

## APP-2 User Roles

The application contains two primary roles:

### Teacher

The teacher can:

* Log in securely.
* View assigned classrooms.
* Start/view monitoring sessions.
* View the current classroom status.
* View student-level attention/fatigue results.
* Receive important alerts.
* View session reports.
* View historical performance.

### Admin

The administrator can:

* Log in securely.
* Manage teachers.
* Manage students.
* Manage classrooms.
* Assign students to classrooms.
* View monitoring sessions.
* View system-wide reports.
* Manage application settings.
* Monitor system status.

---

## APP-3 Application Screens

## Authentication

The first screen should provide:

```text
┌─────────────────────────────┐
│       AI MONITOR            │
│                             │
│  Email / Username           │
│  ┌───────────────────────┐  │
│  │                       │  │
│  └───────────────────────┘  │
│                             │
│  Password                   │
│  ┌───────────────────────┐  │
│  │ •••••••••             │  │
│  └───────────────────────┘  │
│                             │
│       [ LOGIN ]             │
│                             │
└─────────────────────────────┘
```

After successful authentication, the application identifies the user's role and redirects them to the appropriate dashboard.

---

## APP-4 Teacher Application Flow

```text
Login
  ↓
Teacher Dashboard
  ↓
Select Classroom
  ↓
View Monitoring Status
  ↓
View Student Results
  ↓
Receive Alerts
  ↓
View Session Report
```

---

## APP-5 Teacher Dashboard

The dashboard should immediately show the current classroom situation.

### Dashboard Information

```text
┌─────────────────────────────────┐
│ Good Morning, Teacher           │
├─────────────────────────────────┤
│                                 │
│ Current Session                 │
│ Class: III AI & DS              │
│ Status: ● Monitoring            │
│                                 │
│ Students: 45                    │
│                                 │
│ Attentive       35              │
│ Distracted       7              │
│ Fatigue          3              │
│                                 │
│ [ View Students ]               │
│ [ View Alerts ]                 │
│ [ View Report ]                 │
└─────────────────────────────────┘
```

The dashboard should use simple visual indicators rather than overwhelming the teacher with raw AI data.

---

## APP-6 Monitoring Behavior

The actual classroom camera runs separately from the mobile application.

When a monitoring session is active:

```text
Camera
   ↓
Video Frames
   ↓
Face Detection
   ↓
Student Tracking
   ↓
AI Model
   ↓
Predictions
   ↓
Backend
   ↓
Mobile Dashboard
```

The teacher's phone receives **processed results**, not necessarily the raw camera stream.

---

## APP-7 Student Monitoring

Each detected student should have a unique identifier. Per decision D5 this is an anonymous per-session `track_id` shown as `S001`, `S002`, … (no face recognition); linking it to a real student is a roster action (open question OQ-1).

Example:

```text
Student S001
Attention: Attentive
Fatigue: Normal
Confidence: 94%

Student S002
Attention: Distracted
Fatigue: Normal
Confidence: 89%

Student S003
Attention: Attentive
Fatigue: Fatigued
Confidence: 92%
```

The application should avoid changing a student's status based on one isolated frame. If a face is occluded or confidence is low, show `Unknown` instead of guessing.

---

## APP-8 Prediction Validation

The application should use temporal validation before displaying important alerts.

```text
AI Prediction
      ↓
Confidence Check
      ↓
Repeated Observation
      ↓
Temporal Validation
      ↓
Status Update
```

For example:

```text
One closed-eye frame
        ↓
No fatigue alert

Repeated eye closure
        ↓
Temporal analysis
        ↓
Fatigue indicator
```

This reduces unnecessary false alerts. Thresholds, persistence windows, hysteresis and cooldowns are defined in `contracts.md` §5.

---

## APP-9 Student Details Screen

When the teacher selects a student, the application should show:

```text
Student S003

Current Status
────────────────────
Attention: Attentive
Fatigue: Fatigued

Confidence
────────────────────
92%

Session Statistics
────────────────────
Attention Duration
Fatigue Indicators
Distraction Indicators
Number of Alerts

[ View Detailed Report ]
```

The screen should focus on **interpretable results**, not expose complex CNN/LSTM internals.

---

## APP-10 Alert System

The application should generate an alert only when a configured condition is satisfied.

Example:

```text
Repeated Fatigue Detection
          ↓
Confidence Threshold
          ↓
Temporal Validation
          ↓
Generate Alert
```

Example notification:

```text
⚠ Fatigue Indicator

Student S003 has shown repeated
fatigue-related indicators during
the current session.

[ View Student ]
```

The notification should be informational rather than automatically making disciplinary decisions. Wording must say "indicator" / "possible" (see APP-28).

---

## APP-11 Alert Center

Teachers should have a dedicated alert screen.

```text
┌──────────────────────────────┐
│ Alerts                       │
├──────────────────────────────┤
│ ⚠ S003                      │
│ Repeated fatigue indicators  │
│ 10:42 AM                     │
├──────────────────────────────┤
│ ⚠ S017                      │
│ Repeated distraction         │
│ 10:51 AM                     │
└──────────────────────────────┘
```

Alerts have exactly these statuses (`alert_status`, contracts §1): `New` → `Viewed` → `Resolved`. Changing status uses `PATCH /alerts/{id}`. Alert types: `fatigue`, `distraction` (teachers) and `camera_offline`, `ai_offline` (admins, see APP-20/21).

---

## APP-12 Session Management

Each classroom monitoring period should be treated as a session.

Example:

```text
Session
────────────────────
Class: III AI & DS
Date: 30/09/2026
Start: 09:00 AM
End: 10:00 AM
Students: 45
Status: Completed
```

The system should automatically record session start and end times. A session is started/stopped with `POST /sessions` and `POST /sessions/{id}/stop`; stopping triggers report generation (APP-13). The AI server only processes a camera while a session for its classroom is `Monitoring`.

---

## APP-13 Session Report

After a session ends, the application generates a summary.

```text
CLASSROOM SESSION REPORT

Class: III AI & DS
Duration: 60 minutes
Students: 45

Attention
────────────────
Attentive:     35
Distracted:     7

Fatigue
────────────────
Normal:        42
Fatigue:        3

Alerts
────────────────
Total Alerts:   5
```

The teacher can open the detailed report to examine individual student records.

---

## APP-14 Historical Reports

Teachers should be able to access previous sessions.

```text
Reports

30 Sep 2026
III AI & DS
60 minutes

29 Sep 2026
III AI & DS
55 minutes

28 Sep 2026
III AI & DS
60 minutes
```

Selecting a report opens the corresponding session statistics.

---

## APP-15 Admin Application Flow

```text
Admin Login
     ↓
Admin Dashboard
     ↓
Manage Users
     ↓
Manage Students
     ↓
Manage Teachers
     ↓
Manage Classrooms
     ↓
Assign Students
     ↓
Monitor Sessions
     ↓
View Reports
```

---

## APP-16 Admin Dashboard

The admin dashboard should provide system-level information.

```text
┌────────────────────────────────┐
│ Admin Dashboard                │
├────────────────────────────────┤
│ Teachers              12       │
│ Students             450       │
│ Classrooms             8       │
│ Active Sessions        3       │
│                                │
│ AI Server: ● Online            │
│ Database: ● Online              │
│ Camera Services: ● Online      │
└────────────────────────────────┘
```

---

## APP-17 Student Management

Admin can:

* Add students.
* Edit student information.
* Remove/deactivate students.
* Assign students to classrooms.
* View student records.

Example:

```text
Student ID
Name
Department
Year
Class
Status
```

---

## APP-18 Teacher Management

Admin can:

* Create teacher accounts.
* Edit teacher information.
* Assign classrooms.
* Disable accounts.
* View teacher activity.

---

## APP-19 Classroom Management

Admin can create and configure classrooms.

Example:

```text
Classroom
────────────────
Room: AI Lab 01
Class: III AI & DS
Camera: CAM-001
Status: Online
Students: 45
```

The system should associate each camera/monitoring source with the appropriate classroom.

---

## APP-20 Camera Status

The application should show whether the monitoring infrastructure is available.

```text
Camera Status

CAM-001    ● Online
CAM-002    ● Online
CAM-003    ● Offline
```

If a camera disconnects, the backend should update its status and the admin should be notified.

---

## APP-21 AI Server Status

The application should also display basic infrastructure health.

```text
AI Server
● Online

Database
● Connected

API
● Available

Camera
● Connected
```

This prevents the teacher from assuming that no alerts means everything is normal when the AI service is actually offline.

---

## APP-22 Mobile Navigation

### Teacher

```text
Dashboard
   │
   ├── Classroom
   ├── Students
   ├── Alerts
   ├── Reports
   └── Profile
```

### Admin

```text
Dashboard
   │
   ├── Teachers
   ├── Students
   ├── Classrooms
   ├── Sessions
   ├── Reports
   ├── System Status
   └── Profile
```

---

## APP-23 Backend API Behavior

The mobile application communicates with the backend through secure APIs.

Example API structure:

```text
POST /auth/login

GET /teacher/dashboard

GET /classrooms

GET /classrooms/{id}/students

GET /sessions

GET /sessions/{id}

GET /students/{id}/status

GET /alerts

GET /reports

GET /system/status
```

**The authoritative endpoint list, request/response shapes and role rules are in `contracts.md` §3** (it adds CRUD endpoints for students/teachers/classrooms, session start/stop, alert status updates and report export that are implied by APP-17 to APP-19 and APP-13/14).

The AI inference service can communicate with the backend using internal APIs or message queues (this project: in-process pipeline → FastAPI, `implementation.md` Phase 12).

---

## APP-24 Real-Time Updates

The dashboard should update when new validated AI results become available.

```text
AI Prediction
      ↓
Backend
      ↓
Database / Event
      ↓
Mobile Application
      ↓
Dashboard Update
```

For real-time behavior this project uses **WebSockets** (`/ws/telemetry`, contracts §4). Messages contain validated results only (`TrackResult-lite`), throttled to `TELEMETRY_HZ`. The mobile app falls back to REST polling at a low rate if the socket drops and shows "Showing the latest available data" (APP-25).

The application should avoid repeatedly requesting the server unnecessarily.

---

## APP-25 Error Handling

The application must clearly handle failures.

### Camera Offline

```text
⚠ Camera Offline

The classroom camera is currently
unavailable.

AI monitoring has been paused.
```

### AI Server Offline

```text
⚠ AI Service Unavailable

New predictions are currently
unavailable.
```

### Network Error

```text
No Internet Connection

Showing the latest available data.
```

### Authentication Failure

```text
Invalid username or password.
```

---

## APP-26 Security Behavior

The application must enforce role-based access.

```text
Teacher
   ↓
Teacher Resources Only

Admin
   ↓
Administrative Resources
```

A teacher should not be able to access administrative endpoints simply by changing the mobile application's UI.

Authorization must be enforced by the backend.

---

## APP-27 Privacy Behavior

The application should follow a privacy-first design.

The mobile application should receive only the information required for monitoring and reporting.

Avoid exposing unnecessary:

* Raw video
* Facial images
* Biometric information
* Internal model data
* Sensitive student information

Raw classroom video should not be permanently stored unless there is a specific, justified requirement and appropriate authorization. **Project rule (D4):** the mobile app never receives video or face images; the backend never persists them; the Operator Console video channel `/ws/video` is admin/teacher-authenticated and disabled when `PRIVACY_MODE=true`.

---

## APP-28 Important Application Rule

The application should **not automatically make academic, disciplinary, or health decisions based solely on AI predictions**.

The AI output should be treated as an **indicator that can support teacher observation**, not as a definitive diagnosis of fatigue, attention, or student behavior.

```text
AI Prediction
      ↓
Teacher Information
      ↓
Human Review
      ↓
Appropriate Action
```

---

## APP-29 Complete Application Workflow

```text
                    LOGIN
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
       TEACHER                  ADMIN
          │                       │
          ▼                       ▼
      DASHBOARD              DASHBOARD
          │                       │
          ▼                       ├── Manage Students
     CLASSROOM                    ├── Manage Teachers
          │                       ├── Manage Classes
          ▼                       ├── Sessions
   MONITORING STATUS              └── Reports
          │
          ▼
    AI RESULTS
          │
     ┌────┴─────┐
     ▼          ▼
 ATTENTION    FATIGUE
     │          │
     └────┬─────┘
          ▼
       ALERTS
          │
          ▼
       REPORTS
```

---

## APP-30 Final Application Principle

The application should behave as a **three-layer system**:

```text
┌──────────────────────────────┐
│ 1. AI LAYER                 │
│ Camera → Detection → Model  │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ 2. BACKEND LAYER            │
│ API → Validation → Database │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ 3. MOBILE APPLICATION       │
│ Dashboard → Alerts → Reports│
└──────────────────────────────┘
```

The **AI layer analyzes**, the **backend validates and manages the data**, and the **mobile application presents the results to authorized users**.

This separation keeps the application scalable, maintainable, and suitable for real-time classroom monitoring.

---

## APP-31 Traceability — Behavior → Contracts → Build Phase

| Behavior | Section | Contract refs | Built in phase |
|----------|---------|---------------|----------------|
| Login, role redirect | APP-3, APP-26 | `/auth/login`, `role` | 14 (backend), 21 (mobile) |
| Teacher dashboard | APP-5 | `ClassSnapshot`, `/teacher/dashboard` | 14, 22 |
| Student list & details | APP-7, APP-9 | `TrackResult-lite`, `/sessions/{id}/tracks`, `/students/{id}/status` | 14, 22 |
| Prediction validation | APP-8 | contracts §5 | 10 |
| Alerts & Alert Center | APP-10, APP-11 | `Alert`, `/alerts`, `PATCH /alerts/{id}` | 15 (backend), 20 (web feed), 22 (mobile) |
| Sessions | APP-12 | `/sessions`, `sessions` table | 13, 14, 22 |
| Reports & history | APP-13, APP-14 | report schema, `/reports*` | 16, 22 |
| Admin CRUD (students, teachers, classrooms) | APP-15, APP-17–19 | CRUD endpoints | 14, 23 |
| Camera / AI / system status | APP-16, APP-20, APP-21 | `SystemStatus`, `/system/status` | 11, 14, 23 |
| Navigation | APP-22 | — | 21 |
| Real-time updates | APP-24 | `/ws/telemetry` | 11, 12, 21 |
| Error states | APP-25 | — | 21–23 |
| Role-based security | APP-26 | role checks on every endpoint | 14, 25 |
| Privacy | APP-27 | D4, `PRIVACY_MODE` | 11, 13, 25 |

## APP-32 Mobile Implementation Notes

- **Stack:** React Native + Expo (decision D3), TypeScript, secure token storage (`expo-secure-store`), WebSocket client with reconnect/backoff.
- **Design:** reuse the color/typography/spacing tokens from `ui.md` via a single `theme.ts` (mobile section of `ui.md`). Status must never rely on color alone (icon + text label).
- **Every screen must implement** loading, empty, error and offline states (APP-25).
- **Copy rules:** sentence case, "indicator"/"possible" wording, no disciplinary or medical language (APP-28).
