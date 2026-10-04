"""Phase 5 Test Suite — MobileViT Drowsiness Inference Wrapper.

Spec refs: MDL-5, CON §2.1, CON §5, implementation.md Phase 5.
Pass condition:
- Closed eye fixture classified as 'Drowsy'.
- Open eye fixture classified as 'Non Drowsy'.
- Per-face latency measured over >= 100 runs after warm-up and recorded.
"""

from pathlib import Path
import time
import cv2
import numpy as np
import pytest
import torch

from ai.drowsiness import DrowsinessClassifier, LABEL_MAP
from ai.roi import DEFAULT_DROWSINESS_NORM, normalize_crop_to_tensor

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def classifier():
    return DrowsinessClassifier()


def test_drowsiness_open_vs_closed(classifier):
    """Assert closed eye crop classified as Drowsy and open eye crop as Non Drowsy."""
    open_img_path = FIXTURES_DIR / "face_open_eyes.png"
    closed_img_path = FIXTURES_DIR / "face_closed_eyes.png"

    assert open_img_path.exists(), f"Missing fixture: {open_img_path}"
    assert closed_img_path.exists(), f"Missing fixture: {closed_img_path}"

    img_open = cv2.imread(str(open_img_path))
    img_closed = cv2.imread(str(closed_img_path))

    crop_open_rgb = cv2.resize(cv2.cvtColor(img_open, cv2.COLOR_BGR2RGB), (224, 224))
    crop_closed_rgb = cv2.resize(cv2.cvtColor(img_closed, cv2.COLOR_BGR2RGB), (224, 224))

    t_open = normalize_crop_to_tensor(crop_open_rgb, DEFAULT_DROWSINESS_NORM["mean"], DEFAULT_DROWSINESS_NORM["std"])
    t_closed = normalize_crop_to_tensor(crop_closed_rgb, DEFAULT_DROWSINESS_NORM["mean"], DEFAULT_DROWSINESS_NORM["std"])

    res_open = classifier.predict_single(t_open)
    res_closed = classifier.predict_single(t_closed)

    print(f"\n[Drowsiness Test Result]")
    print(f"  Open Eye Crop  : label='{res_open['label']}', p_drowsy={res_open['p_drowsy']}")
    print(f"  Closed Eye Crop: label='{res_closed['label']}', p_drowsy={res_closed['p_drowsy']}")

    assert res_open["label"] == "Non Drowsy", f"Expected 'Non Drowsy' for open eyes, got {res_open['label']}"
    assert res_closed["label"] == "Drowsy", f"Expected 'Drowsy' for closed eyes, got {res_closed['label']}"
    assert res_closed["p_drowsy"] > res_open["p_drowsy"], "Closed eyes must have higher p_drowsy than open eyes"


def test_batch_drowsiness_inference(classifier):
    """Assert batch inference handles multiple inputs and empty input."""
    dummy_batch = torch.randn(4, 3, 224, 224)
    results = classifier.predict_batch(dummy_batch)
    assert len(results) == 4
    for r in results:
        assert r["label"] in ["Drowsy", "Non Drowsy"]
        assert 0.0 <= r["p_drowsy"] <= 1.0

    # Test empty batch
    empty_tensor = torch.empty((0, 3, 224, 224))
    assert classifier.predict_batch(empty_tensor) == []


def test_drowsiness_latency_benchmark(classifier):
    """Measure per-face inference latency over >= 100 runs after warm-up on declared hardware."""
    dummy_input = torch.randn(1, 3, 224, 224)

    # 1. Warm-up (10 runs)
    print("\n[Benchmark] Warming up MobileViT-v2 (10 runs)...")
    for _ in range(10):
        _ = classifier.predict_batch(dummy_input)

    # 2. Benchmark runs (100 runs)
    num_runs = 100
    print(f"[Benchmark] Executing {num_runs} timed benchmark runs on declared hardware ({classifier.device})...")
    latencies_ms = []

    for _ in range(num_runs):
        t0 = time.perf_counter()
        _ = classifier.predict_batch(dummy_input)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    avg_ms = float(np.mean(latencies_ms))
    p50_ms = float(np.median(latencies_ms))
    p95_ms = float(np.percentile(latencies_ms, 95))
    min_ms = float(np.min(latencies_ms))
    max_ms = float(np.max(latencies_ms))

    print(f"\n" + "=" * 60)
    print(f"MobileViT-v2 Drowsiness Model Latency Report ({classifier.device})")
    print(f"=" * 60)
    print(f"  Runs Tested : {num_runs}")
    print(f"  Mean Latency: {avg_ms:.2f} ms")
    print(f"  P50 Latency : {p50_ms:.2f} ms")
    print(f"  P95 Latency : {p95_ms:.2f} ms")
    print(f"  Min / Max   : {min_ms:.2f} ms / {max_ms:.2f} ms")
    print(f"=" * 60)

    # Save benchmark numbers to artifact / test output for PROGRESS.md
    assert len(latencies_ms) == num_runs
    assert avg_ms > 0
