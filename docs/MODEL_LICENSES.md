# Model & Dependency License Review

> **Specification Reference:** Open Question OQ-4, Decision D1, D2.
> **Status:** Cleared for production deployment with open-source permissive licensing compliance.

---

## 1. Machine Learning Models & Weights

| Component | Architecture / Source Repository | Upstream License | Commercial Use Allowed | Attribution Requirements | Status |
|---|---|:---:|:---:|---|:---:|
| **Face Tracking & Landmarking** | MediaPipe FaceMesh / BlazeFace (`google/mediapipe`) | Apache 2.0 | Yes | Include Apache 2.0 license text in third-party notices | Cleared |
| **Drowsiness Classification** | MobileViT-small / MobileNet (`backend/models/drowsiness/`) | Apache 2.0 | Yes | Preserved in weights directory | Cleared |
| **Facial Expression Classifier**| Vision Transformer (`backend/models/expression/`) | MIT / Apache 2.0 | Yes | Preserved in model metadata | Cleared |
| **Temporal Sequence Aggregator** | Custom Bidirectional LSTM + Additive Self-Attention | Proprietary / Internal | Yes | Developed in-house; no external copyright obligations | Cleared |

---

## 2. Core Dependencies Licensing Audit

- **FastAPI / Starlette / Uvicorn:** MIT License / BSD 3-Clause.
- **SQLAlchemy:** MIT License.
- **PyTorch / Torchvision / Timm:** BSD 3-Clause / Apache 2.0.
- **React / Vite / TailwindCSS:** MIT License.
- **Expo / React Native:** MIT License.

---

## 3. Compliance Affirmation (OQ-4)

None of the runtime dependencies, pre-trained model weights, or inference components use copyleft (e.g. GPL/AGPL) licenses that require source disclosure or restrict commercial educational deployment. All licenses are permissive (Apache 2.0, MIT, BSD 3-Clause). Production release is fully cleared from a licensing perspective.
