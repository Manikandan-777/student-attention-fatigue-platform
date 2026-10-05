# Web Operator Console — Student Attention & Fatigue Platform

> **Real-Time Operator Monitoring Dashboard for Live Classroom Telemetry**  
> Built with **React 19**, **TypeScript**, **Vite**, **Tailwind CSS**, and **Recharts**.

---

## 1. System Role & Execution Flow

The **Web Operator Console** is the centralized monitoring interface designed for administrative operators and educational supervisors. It connects directly to the FastAPI backend over high-frequency WebSocket channels to provide real-time visualization of classroom attention and fatigue indicators.

### Key Operational Features:
- **Live Student Grid (`LiveGrid`):** Anonymous student tiles (`S001`, `S002`, ...) displaying real-time Attention Scores (0–100), Fatigue Badges (`Normal`, `Fatigued`, `Unknown`), and tracking confidence meters.
- **Dynamic Telemetry Charts (`Recharts`):**
  - **Attention Trend Chart:** 60-second scrolling window of class-average attention trajectory.
  - **Fatigue Distribution Chart:** Real-time breakdown of attentive vs. distracted vs. fatigued students.
  - **Fatigue Timeline:** Longitudinal fatigue accumulation tracker across the ongoing session.
- **Alert Triage & Feed (`AlertFeed`):** Instant notifications for persistent fatigue (>10s) or distraction (>15s). Allows operators to view or resolve alerts with one-click actions.
- **Session Lifecycle Controls:** Start, monitor, and finalize classroom sessions with automatic UTC synchronization.
- **Strict Privacy Compliance:** Video streaming is strictly disabled by default (`PRIVACY_MODE=true`). Annotated camera video is only streamed if explicitly enabled by administrative policy.

---

## 2. Component Hierarchy

```text
src/
├── App.tsx                     # React Router (LoginPage, DashboardPage, AlertsPage, ReportsPage)
├── config.ts                   # API & WebSocket connection endpoints
├── tokens.ts                   # Design system color and spacing tokens (ui.md)
├── pages/
│   ├── LoginPage.tsx           # JWT authentication & role checking
│   ├── DashboardPage.tsx       # Live multi-student grid, charts & stats
│   ├── AlertsPage.tsx          # Real-time alert feed & resolution workflow
│   └── ReportsPage.tsx         # Historical session analytics & metric export
└── components/
    ├── LiveGrid.tsx            # Grid container for student cards
    ├── StudentTile.tsx         # Individual student card (S001, S002...)
    ├── AttentionTrendChart.tsx # 60s scrolling area chart for class attention
    ├── DistributionChart.tsx   # Donut chart showing attention/fatigue distribution
    ├── FatigueTimelineChart.tsx# Historical fatigue index progression
    ├── AlertFeed.tsx           # Real-time alert list with action triggers
    └── ConnectionBanner.tsx    # Live WebSocket connection status & reconnect alerts
```

---

## 3. Quick Start & Execution

### Prerequisites
- Node.js 20+
- npm 10+

### Development Server
```bash
# Install dependencies
npm install

# Run Vite development server (HMR enabled)
npm run dev
```
The console will start at **`http://localhost:5173`**.

### Production Build
```bash
# Typecheck and build production bundle
npm run build

# Preview production build locally
npm run preview
```

### Running Test Suite
```bash
# Run all 23 Vitest & React Testing Library tests
npm test
```

---

## 4. Environment Configuration

Configurable via `.env` or root environment variables:

| Variable | Default | Description |
|---|:---:|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | FastAPI REST backend endpoint |
| `VITE_WS_BASE_URL` | `ws://localhost:8000` | FastAPI WebSocket gateway |

---

## 5. End-to-End System Flow Reference

For the comprehensive end-to-end system flow execution guide across Backend, AI pipeline, Web Console, and Mobile app, see:
- **[../README_SYSTEM_FLOW_EXECUTION.md](../README_SYSTEM_FLOW_EXECUTION.md)**
- **[../docs/contracts.md](../docs/contracts.md)**
