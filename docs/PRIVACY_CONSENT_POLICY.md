# Privacy Notice & Student/Guardian Consent Policy

> **Specification References:** Decision D4, D5, D7, D8, SYS-14, APP-27, APP-28, Open Question OQ-5.
> **Deployment Rule:** Do not deploy this system in an active classroom without satisfying the consent and notification checklists below.

---

## 1. Core Ethical & Privacy Guarantees

The Classroom Attention & Fatigue Detection System was engineered with **privacy-by-design** principles to support educators while safeguarding student dignity:

1. **Zero Biometric Identity / No Facial Recognition (D5, APP-27):**
   - The system tracks anonymous bounding boxes labeled `S001`, `S002`, etc.
   - It **never** executes facial recognition, face identification, or facial embedding comparison against student photos.
2. **Ephemeral Video & Zero Frame Storage (D4, APP-27):**
   - Live video feeds are processed in volatile memory and immediately discarded.
   - Raw frames, video recordings, and face crops are **never written to disk, database, or persistent storage**.
3. **No Video to Mobile (D4):**
   - Mobile applications used by teachers and administrators receive strictly structured telemetry data (`TrackResult-lite`); video streaming is architecturally prohibited on mobile devices.
4. **Strict Default Privacy Mode (`PRIVACY_MODE=true`):**
   - Live operator video streaming is disabled by default. If enabled in dev environments, the video channel is secured and rejected with close code `4403` whenever privacy mode is engaged.
5. **Supportive, Non-Diagnostic Language (D8):**
   - The platform never issues medical diagnoses (e.g. "ADHD", "narcolepsy") or disciplinary assertions ("lazy", "sleeping", "delinquent").
   - All reports carry the required legal disclaimer:
     > *"AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."*

---

## 2. Institutional Consent Checklist (OQ-5)

Prior to turning on camera inputs in any educational environment, the institution must complete and document the following items:

- [ ] **Institutional Review & Approval:** School board, administration, and legal counsel approval obtained for real-time classroom telemetry assistance.
- [ ] **Guardian Notification & Consent:**
  - Clear information disclosure distributed to all parents/guardians explaining:
    - What data is processed: head pose, blink rate (EAR), mouth opening (MAR), and coarse facial expression probabilities.
    - What data is NOT collected: no names matched to faces, no identity recognition, no video storage.
    - Opt-out policy: alternate classroom seating or unmonitored classroom option provided without academic penalty.
- [ ] **Student Transparency:** Age-appropriate explanation provided to students regarding the camera's role in measuring collective classroom pacing and fatigue.
- [ ] **Physical Signage:** Physical notices posted at classroom entrances indicating: *"Notice: Automated classroom pacing & attention telemetry in operation. No video recordings are persisted."*
- [ ] **Data Retention Compliance:** Automatic purge job active ensuring all session observations and alerts are irreversibly expunged after `RETENTION_DAYS` (default: 180 days).

---

## 3. Data Flow & Access Controls

| Role | Access Scope | Visual Data Access |
|---|---|:---:|
| **Student** | Anonymous `S001...` track within session | None |
| **Teacher** | Assigned classroom sessions, aggregated telemetry, alert resolutions | None (telemetry only) |
| **Admin** | System health, user management, infrastructure logs | None (telemetry only) |
| **Operator** | Live grid (only if explicit privacy override `PRIVACY_MODE=false`) | Bounding boxes on volatile canvas |
