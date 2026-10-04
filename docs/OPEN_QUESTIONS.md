# Open Questions (OQ) Log

This document tracks unresolved product, architecture, or policy questions as defined in `README.md` §8 and `README_EXECUTION.md`. When a conflict or question is uncovered, record it here and operate using the most conservative default.

| ID | Question | Conservative Default Adopted | Status |
|:---|:---|:---|:---:|
| **OQ-1** | How are `S001…` tracks mapped to real students (seat map, manual tagging, none)? | Stay anonymous per session. Display only anonymous track labels (`S001`, `S002`, ...). | ACTIVE (Default In Use) |
| **OQ-2** | Is labeled data available to train the LSTM/attention head? | No labeled dataset provided; run scoring in heuristic mode (`model_mode = "heuristic"`) per Decision D10. | ACTIVE (Default In Use) |
| **OQ-3** | Target hardware (CPU only vs GPU) for latency/FPS targets? | Hardware declared as **CPU only (Intel Core i5-12450H)**. Latency/FPS will be measured and recorded on CPU. | RESOLVED / DECLARED |
| **OQ-4** | Are the two Hugging Face model licenses acceptable for deployment? | Extract license metadata from model cards and log in `backend/models/MANIFEST.json`. Block production release until confirmed. | ACTIVE (Default In Use) |
| **OQ-5** | Consent/notification policy for students and parents/guardians? | Strict privacy-first defaults (`PRIVACY_MODE=true`, no image persistence). Do not deploy in real classrooms without signed policy. Document in Phase 25. | ACTIVE (Default In Use) |
