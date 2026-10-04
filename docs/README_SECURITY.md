# Security & Vulnerability Check Guide

> **Classroom Attention & Fatigue Detection Platform**
> **Scope:** Python Backend & AI Inference Engine, Web Operator Console, Mobile App (Expo/RN), Docker Containers, Database & REST/WebSocket APIs.
> **Compliance & Non-Negotiables:** Decision D4 (No Raw Frame/Crop Storage), Decision D5 (No Facial Recognition), Decision D8 (Non-Diagnostic Terminology), APP-26 (Login Rate Limiting), APP-27 (Strict Privacy Mode).  
> **Reference Manual:** For comprehensive scanning procedures, threat triage SLAs, and lockdown runbooks, see [docs/VULNERABILITY_CHECK.md](docs/VULNERABILITY_CHECK.md).

---

## 1. Quick Automated Audit (One Command)

To run the built-in vulnerability, secrets, privacy schema, and configuration audit across the entire repository:

```bash
# Windows
.\backend\.venv\Scripts\python.exe backend/scripts/run_security_audit.py

# Linux / macOS
python backend/scripts/run_security_audit.py
```

### What this checks automatically:
1. **Privacy Mode Default (`PRIVACY_MODE=true`):** Confirms live video is blocked by default with WebSocket code `4403`.
2. **Zero-Media Schema Integrity:** Scans all SQLAlchemy models ensuring zero `BLOB`, `image`, `photo`, or biometric `embedding` columns.
3. **Secret & Key Leak Detection:** Scans source code for hardcoded private keys, JWT secrets, and cleartext credentials.
4. **Node.js Dependency Audits:** Runs `npm audit` for both `operator-console` and `mobile`.
5. **Rate Limiting (APP-26):** Verifies max 5 failed attempts per IP per 5 minutes before `HTTP 429` lockout.

---

## 2. Layer-by-Layer Vulnerability Scanning

### 2.1 Backend Python Dependencies (`pip-audit`)
Detects known vulnerabilities (CVEs) in Python packages:

```bash
cd backend
# Install pip-audit in the virtual environment
.\.venv\Scripts\python.exe -m pip install pip-audit

# Run audit against installed packages
.\.venv\Scripts\python.exe -m pip_audit

# Or audit directly against requirements.txt
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

### 2.2 Static Application Security Testing (SAST with `bandit`)
Scans Python code for security flaws (SQL injection, unsafe deserialization, weak ciphers, cleartext credentials):

```bash
cd backend
.\.venv\Scripts\python.exe -m pip install bandit

# Run Bandit scan on app and AI modules
.\.venv\Scripts\python.exe -m bandit -r app/ ai/ -ll -s B101,B311
```
- `-ll`: Report only medium and high severity issues.
- `-s B101`: Suppress `assert` statement warnings used in internal typing.

### 2.3 Web Operator Console (`npm audit`)
Scans frontend npm packages for supply-chain vulnerabilities:

```bash
cd operator-console
npm audit --audit-level=high

# To fix compatible non-breaking advisory updates:
npm audit fix
```

### 2.4 Mobile App (`npm audit`)
Scans React Native and Expo libraries for vulnerabilities:

```bash
cd mobile
npm audit --audit-level=high
```

### 2.5 Secret & Credential Scanning (`gitleaks`)
Ensures no API keys, tokens, or credentials are accidentally committed to Git:

```bash
# Using GitLeaks (standalone binary or Docker)
docker run --rm -v ${PWD}:/path zricethezav/gitleaks:latest detect --source="/path" --verbose
```

### 2.6 Docker Container Vulnerability Scan (`trivy` & `docker scout`)
Scans container base images (`python:3.11-slim`, `node:20-alpine`, `nginx:alpine`, `postgres:16-alpine`):

```bash
# Using Docker Scout
docker scout cves local://classroom_monitor_backend:latest
docker scout cves local://classroom_monitor_console:latest

# Or using Trivy
trivy image classroom_monitor_backend:latest
trivy image classroom_monitor_console:latest
```

---

## 3. Privacy & Non-Negotiables Verification Suite

Run the automated privacy and security test suites:

```bash
# 1. Run Phase 25 Hardening & Security Audit Test
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_phase25_hardening.py -v -s

# 2. Run Phase 24 End-to-End Stress & Soak Test
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_phase24_e2e_stress.py -v -s

# 3. Run Full System Regression (111 tests)
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

---

## 4. Threat Matrix & Implemented Safeguards

| Threat Vector | Severity | Implemented Mitigation | Verification Check |
|---|:---:|---|---|
| **Brute-Force Login** | High | `LoginRateLimiter` enforces max 5 failed attempts per IP per 5 min $\to$ `HTTP 429` with `Retry-After`. | `test_login_rate_limiting_enforcement` |
| **Biometric / Privacy Breach** | Critical | Ephemeral video in RAM; zero frame storage; no face recognition (D5); zero BLOB columns in DB. | `test_database_schema_zero_media_audit` |
| **Unauthorized Video Stream** | High | Video endpoint `/ws/video` rejected with close code `4403` when `PRIVACY_MODE=true` (default). | `test_privacy_mode_health_and_video_lock` |
| **Broken Object Level Auth (BOLA)** | High | Teacher classroom scoping strictly prevents accessing sessions or students of other teachers. | `test_teacher_scoping` in Phase 14 suite |
| **SQL Injection** | High | SQLAlchemy 2.0 parameterized queries exclusively; no raw string interpolation. | Static audit + SQLAlchemy type bindings |
| **JWT Tampering** | High | HS256/RS256 cryptographically verified with server `SECRET_KEY` on all private endpoints. | `test_jwt_validation` in Phase 14 suite |
| **Cross-Site Scripting (XSS)** | Medium | React JSX output escaping; strict Content-Security-Policy headers in Nginx. | `operator-console/nginx.conf` |

---

## 5. Continuous Integration (CI) Security Pipeline

To enforce these vulnerability checks on every Pull Request, configure GitHub Actions (`.github/workflows/security.yml`):

```yaml
name: Security & Vulnerability Scans

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install pip-audit bandit

      - name: Python Dependency Audit (pip-audit)
        run: |
          python -m pip_audit -r backend/requirements.txt

      - name: Static Security Analysis (Bandit)
        run: |
          python -m bandit -r backend/app backend/ai -ll -s B101,B311

      - name: Repository Security & Privacy Audit Script
        run: |
          python backend/scripts/run_security_audit.py

      - name: Operator Console npm audit
        run: |
          cd operator-console && npm audit --audit-level=high

      - name: Mobile App npm audit
        run: |
          cd mobile && npm audit --audit-level=high

      - name: Pytest Security Audit Suite
        run: |
          python -m pytest backend/tests/test_phase25_hardening.py -v
```

---

## 6. Incident Response & Vulnerability Disclosure

If a security vulnerability or privacy violation is discovered:
1. **Report:** Immediately notify the security lead or create a confidential advisory.
2. **Containment:** If a video leakage or privacy exposure is identified, immediately set `PRIVACY_MODE=true` in `.env` and restart containers (`docker compose restart backend`).
3. **Remediation:** Fix and verify with `python backend/scripts/run_security_audit.py` and submit a patch with corresponding automated test cases.
