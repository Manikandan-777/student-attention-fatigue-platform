#!/usr/bin/env python3
"""Pretrained Model Verification Script for Phase 2.

Implements MDL-4 specifications:
1. Validates config.json, id2label, weights file existence.
2. Reads and reports preprocessor_config.json parameters (size, mean, std).
3. Performs dummy forward pass (1, 3, H, W) for each model.
4. Asserts emotion labels match contracts.md §1 enums exactly (7 classes).
5. Asserts drowsiness labels map cleanly via ai.drowsiness.LABEL_MAP.
6. Prints formatted table with file paths, sizes, and model metadata.
7. Exits 0 on success, non-zero on error.
"""

import json
from pathlib import Path
import sys

# Ensure backend root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import torch
from ai.drowsiness import LABEL_MAP, normalize_drowsiness_label

MODELS_DIR = BACKEND_DIR / "models"
EXPECTED_EMOTIONS = {"angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"}


def format_size(bytes_len: int) -> str:
    mb = bytes_len / (1024 * 1024)
    return f"{mb:.2f} MB"


def verify_drowsiness_model(model_dir: Path) -> dict:
    print("\n" + "=" * 60)
    print("Verifying Drowsiness Model (MobileViT-v2)")
    print("=" * 60)

    # 1. Config check
    cfg_file = model_dir / "config.json"
    if not cfg_file.exists():
        raise FileNotFoundError(f"Missing config.json in {model_dir}")
    with cfg_file.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    id2label = cfg.get("id2label", {})
    print(f"[Config] id2label: {id2label}")

    # 2. Weights file check
    weights_files = [f for f in ["model.safetensors", "best_model.pt", "pytorch_model.bin"] if (model_dir / f).exists()]
    if not weights_files:
        raise FileNotFoundError(f"No weights file (model.safetensors, best_model.pt, pytorch_model.bin) in {model_dir}")
    print(f"[Weights] Found weights files: {weights_files}")

    # If best_model.pt exists, also ensure model.safetensors is saved
    if "best_model.pt" in weights_files and not (model_dir / "model.safetensors").exists():
        import safetensors.torch as st
        sd = torch.load(model_dir / "best_model.pt", map_location="cpu")
        st.save_file(sd, model_dir / "model.safetensors")
        weights_files.append("model.safetensors")
        print("[Weights] Converted best_model.pt to model.safetensors")

    # 3. Preprocessor config
    prep_file = model_dir / "preprocessor_config.json"
    if not prep_file.exists():
        raise FileNotFoundError(f"Missing preprocessor_config.json in {model_dir}")
    with prep_file.open("r", encoding="utf-8") as f:
        prep_cfg = json.load(f)
    print(f"[Preprocessor] Config: {json.dumps(prep_cfg, indent=2)}")

    # 4. Model instantiation and dummy forward pass
    import timm
    print("[Inference] Loading MobileViT-v2 architecture via timm...")
    model = timm.create_model("mobilevitv2_200", pretrained=False, num_classes=2)
    state_dict = torch.load(model_dir / "best_model.pt", map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    dummy_input = torch.randn(1, 3, 224, 224)
    with torch.inference_mode():
        output = model(dummy_input)
    print(f"[Inference] Dummy forward pass output shape: {output.shape}")
    assert output.shape == (1, 2), f"Expected shape (1, 2), got {output.shape}"

    # 5. Label mapping assertion
    print("[Labels] Validating drowsiness labels with ai/drowsiness.py::LABEL_MAP...")
    for idx_str, raw_label in id2label.items():
        mapped = normalize_drowsiness_label(raw_label)
        assert mapped in ["Drowsy", "Non Drowsy"], f"Invalid mapped label: {mapped}"
        print(f"  {raw_label} -> {mapped}")

    return {
        "name": "drowsiness",
        "dir": str(model_dir),
        "weights": weights_files[0],
        "size": format_size((model_dir / weights_files[0]).stat().st_size),
        "output_shape": list(output.shape),
    }


def verify_expression_model(model_dir: Path) -> dict:
    print("\n" + "=" * 60)
    print("Verifying Facial Expression Model (ViT)")
    print("=" * 60)

    # 1. Config check
    cfg_file = model_dir / "config.json"
    if not cfg_file.exists():
        raise FileNotFoundError(f"Missing config.json in {model_dir}")
    with cfg_file.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    id2label = cfg.get("id2label", {})
    print(f"[Config] id2label ({len(id2label)} classes): {id2label}")

    # 2. Weights file check
    weights_files = [f for f in ["model.safetensors", "pytorch_model.bin"] if (model_dir / f).exists()]
    if not weights_files:
        raise FileNotFoundError(f"No weights file found in {model_dir}")
    print(f"[Weights] Found weights files: {weights_files}")

    # 3. Preprocessor config
    prep_file = model_dir / "preprocessor_config.json"
    if not prep_file.exists():
        raise FileNotFoundError(f"Missing preprocessor_config.json in {model_dir}")
    with prep_file.open("r", encoding="utf-8") as f:
        prep_cfg = json.load(f)
    print(f"[Preprocessor] Config: {json.dumps(prep_cfg, indent=2)}")

    # 4. Model instantiation and forward pass
    from transformers import AutoModelForImageClassification
    print("[Inference] Loading ViT expression classifier via transformers...")
    model = AutoModelForImageClassification.from_pretrained(str(model_dir))
    model.eval()

    dummy_input = torch.randn(1, 3, 224, 224)
    with torch.inference_mode():
        output = model(dummy_input).logits
    print(f"[Inference] Dummy forward pass logits shape: {output.shape}")
    assert output.shape == (1, 7), f"Expected shape (1, 7), got {output.shape}"

    # 5. Label assertion against contracts.md §1
    print("[Labels] Validating 7 emotions against contracts.md §1...")
    labels = {v.lower().strip() for v in id2label.values()}
    if labels != EXPECTED_EMOTIONS:
        raise ValueError(f"Emotion labels {labels} do not match contracts.md §1: {EXPECTED_EMOTIONS}")
    print(f"[Labels] Match confirmed! All 7 emotions verified: {sorted(list(labels))}")

    return {
        "name": "expression",
        "dir": str(model_dir),
        "weights": weights_files[0],
        "size": format_size((model_dir / weights_files[0]).stat().st_size),
        "output_shape": list(output.shape),
    }


def main() -> int:
    print("=" * 60)
    print("Phase 2 — Pretrained Model Verification")
    print("=" * 60)

    # Check MANIFEST.json
    manifest_file = MODELS_DIR / "MANIFEST.json"
    if not manifest_file.exists():
        print(f"[ERROR] Missing {manifest_file}")
        return 1
    with manifest_file.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    print(f"[Manifest] Loaded {manifest_file}:")
    print(json.dumps(manifest, indent=2))

    summary = []
    try:
        res_drow = verify_drowsiness_model(MODELS_DIR / "drowsiness")
        summary.append(res_drow)

        res_expr = verify_expression_model(MODELS_DIR / "expression")
        summary.append(res_expr)
    except Exception as e:
        print(f"\n[FAIL] Verification encountered an error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary table
    print("\n" + "=" * 80)
    print(f"{'Model':<15} {'Primary Weights':<20} {'Size':<12} {'Output Shape':<15} {'License':<10}")
    print("-" * 80)
    for s in summary:
        name = s["name"]
        lic = manifest.get(name, {}).get("license", "Unknown")
        print(f"{name:<15} {s['weights']:<20} {s['size']:<12} {str(s['output_shape']):<15} {lic:<10}")
    print("=" * 80)
    print("Verification PASSED: Both models verified and functional.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
