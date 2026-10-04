# Model Acquisition Plan — Pretrained Hugging Face Models

> **Doc ID:** `MDL` · **Implements:** `implementation.md` Phase 2 (download/verify) and feeds Phases 5–6 (wrappers)
> **Depends on:** `README.md` decisions D1, D2, D10 · **Names/enums:** `contracts.md` §1
> **Paths are canonical (D2):** `backend/models/drowsiness/` and `backend/models/expression/`. The earlier `./pretrained_models/` path is retired.

---

## MDL-1 Selected Models

| Role | Repo | Local dir | Output | Consumed by |
|------|------|-----------|--------|-------------|
| Eye-state / drowsiness | [`mosesb/drowsiness-detection-mobileViT-v2`](https://huggingface.co/mosesb/drowsiness-detection-mobileViT-v2) | `backend/models/drowsiness/` | `Drowsy` vs `Non Drowsy` probabilities | `ai/drowsiness.py` (Phase 5) |
| Facial expression | [`trpakov/vit-face-expression`](https://huggingface.co/trpakov/vit-face-expression) | `backend/models/expression/` | 7 emotion probabilities | `ai/expression.py` (Phase 6) |

These two models play the "spatial feature extraction" role that `system_work.md` (SYS-5) originally assigned to a custom CNN (decision D1). They are **per-frame image classifiers**. They do not output "attention" or "fatigue" directly; those are derived later by temporal modeling and scoring (Phases 7–10, `contracts.md` §6).

## MDL-2 Agent Task (copy into a coding agent)

```text
Task: Phase 2 of docs/implementation.md.
1. Ensure `huggingface_hub`, `torch`, `transformers` are installed (Phase 1 env).
2. Create backend/scripts/download_models.py exactly as in MDL-3.
3. Create backend/scripts/verify_models.py exactly as in MDL-4.
4. Run both. Write the output to docs/PROGRESS.md using the template in README.md §6.
5. Do not start Phase 3 until verify_models.py exits with code 0.
```

## MDL-3 `backend/scripts/download_models.py`

```python
"""Download pretrained models into backend/models/ (decision D2)."""
import json, os, sys
from pathlib import Path
from huggingface_hub import snapshot_download, HfApi

BASE = Path(__file__).resolve().parents[1] / "models"
MODELS = {
    "drowsiness": "mosesb/drowsiness-detection-mobileViT-v2",
    "expression": "trpakov/vit-face-expression",
}

def main() -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    manifest, failed = {}, []
    for name, repo_id in MODELS.items():
        target = BASE / name
        target.mkdir(parents=True, exist_ok=True)
        print(f"[download] {name}: {repo_id} -> {target}")
        try:
            snapshot_download(repo_id=repo_id, local_dir=str(target))  # symlink flag is deprecated; not needed
            info = HfApi().model_info(repo_id)
            manifest[name] = {
                "repo_id": repo_id,
                "revision": info.sha,                        # pin for reproducibility
                "license": (info.card_data.license if info.card_data else None),  # record for OQ-4
            }
        except Exception as e:                               # report, continue, fail at end
            print(f"[download] ERROR {name}: {e}")
            failed.append(name)
    (BASE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print(f"[download] manifest written: {BASE/'MANIFEST.json'}")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
```

## MDL-4 `backend/scripts/verify_models.py` (Phase 2 test)

Must check, for **each** model directory:

1. `config.json` exists and parses; print `id2label`.
2. A weights file exists: `model.safetensors` **or** `pytorch_model.bin`.
3. Preprocessing config exists (`preprocessor_config.json`); print expected image size and mean/std (Phase 4 must use these values, not assumptions).
4. The model loads in memory (`AutoModelForImageClassification.from_pretrained(dir)`), and a dummy tensor `(1, 3, H, W)` passes through without error.
5. Print a table: file, size in MB, path.
6. Expression model: `len(id2label) == 7` and the label set equals `contracts.md` §1 `emotion` (case-insensitive). Drowsiness model: two labels; build a mapping from the model's labels to `Drowsy` / `Non Drowsy` in a single constant (`ai/drowsiness.py::LABEL_MAP`) — do not scatter string literals.
7. Exit code `0` on success, non-zero on any failure.

**Pass condition:** both models load via PyTorch with no missing-file exceptions and the label checks pass.

## MDL-5 Notes for Wrappers (Phases 5–6)

- Use the image processor shipped with each model (`AutoImageProcessor`) or replicate its mean/std/size exactly; the project's own 224×224 ROI output (Phase 4) must be compatible.
- Run inference in `torch.inference_mode()`, batch all faces of a frame, use `.eval()`.
- Latency budget: `MAX_INFER_MS_PER_FACE` (contracts §5) on the declared hardware (OQ-3). Record actual numbers in `PROGRESS.md`.
- Models were trained on generic datasets; accuracy in real classrooms (angle, lighting, distance, masks) is unknown. Surface `Unknown` when confidence is low (D7).
- Expression output is a weak proxy for engagement (contracts §6) and must never be the sole cause of an alert.
- Confirm each model's license (stored in `MANIFEST.json`) before production use (OQ-4).

## MDL-6 What Comes Next

| Step | Phase | Doc |
|------|-------|-----|
| MediaPipe Face Mesh faces + tracking IDs | 3 | `implementation.md` |
| ROI crop / normalize to model input | 4 | `implementation.md` |
| Wrappers → temporal buffer → LSTM + attention → scoring | 5–10 | `implementation.md`, `contracts.md` §6 |
