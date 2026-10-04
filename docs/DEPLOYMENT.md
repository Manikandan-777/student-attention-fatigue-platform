# Production Deployment & Operations Runbook

> **Specification References:** SYS-10, SYS-14, SYS-17, APP-26, APP-27, APP-28, README_EXECUTION Phase 24 & 25.

---

## 1. Architecture Overview

```
                      ┌─────────────────────────────────────┐
                      │    Nginx Reverse Proxy / Ingress    │
                      │       (TLS / HTTPS Port 443)        │
                      └───────────────┬─────────────────────┘
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           │                                                     │
           ▼ (Port 80)                                           ▼ (Port 8000)
┌────────────────────────┐                             ┌────────────────────────┐
│    Operator Console    │                             │      FastAPI App       │
│     (Static React)     │                             │  + WebSocket Telemetry │
└────────────────────────┘                             └───────────┬────────────┘
                                                                   │
                                                                   ▼ (Port 5432)
                                                       ┌────────────────────────┐
                                                       │   PostgreSQL Database  │
                                                       │ (Tables + Data Retention│
                                                       └────────────────────────┘
```

---

## 2. Production Quickstart (Docker Compose)

### 2.1 Configuration
1. Clone the repository into production host.
2. Initialize environment:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` to supply strong secrets:
   ```bash
   # Generate strong 256-bit random key
   openssl rand -hex 32
   ```
   Set `SECRET_KEY` and ensure `PRIVACY_MODE=true`.

### 2.2 Booting the Stack
```bash
docker compose up -d --build
```

### 2.3 Applying Alembic Migrations
```bash
docker compose exec backend alembic upgrade head
```

---

## 3. Production Security Checklist

- [x] **Strict Privacy Default:** `PRIVACY_MODE=true` is enforced. Live video endpoints return HTTP 4403.
- [x] **Rate Limiting (APP-26):** Max 5 failed login attempts per IP within 5 minutes triggers HTTP 429 Too Many Requests.
- [x] **JWT Security:** Configurable expiration (default 8 hours) with HS256 / RS256 token verification on all protected endpoints.
- [x] **CORS Allow-List:** Origin restrictions configured in `.env`.
- [x] **Data Retention:** Automated daily cron or background task purging observations older than `RETENTION_DAYS`.
- [x] **Zero Raw Media:** Database schema and application code contain zero BLOB or image columns.
- [x] **TLS Termination:** Production ingress handles SSL certificates (Let's Encrypt / Certbot) and proxies to internal containers.

---

## 4. Monitoring & Health Probes

- **Liveness Probe:** `GET /health` returns `{"status": "ok", "privacy_mode": true}`.
- **System Metrics:** `GET /system/status` provides live camera status, AI inference throughput (FPS), and service availability.
- **WebSocket Heartbeat:** Send `{"type": "ping"}` to `/ws/telemetry` to receive `{"type": "pong"}`.
