"""Phase 6 Test Suite — ViT Facial Expression Wrapper.

Spec refs: MDL-5, CON §1, CON §2.1, CON §6, implementation.md Phase 6.
Pass condition:
- Exact 7 emotion keys present in probs dictionary:
  ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral'].
- Probabilities sum to 1.0 (+-1e-4).
- Correct top label identified.
- Empty and batched tensors handled gracefully.
"""

from pathlib import Path
import time
import cv2
import numpy as np
import pytest
import torch

from ai.expression import CANONICAL_EMOTIONS, ExpressionClassifier
from ai.roi import DEFAULT_EXPRESSION_NORM, normalize_crop_to_tensor

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def classifier():
    return ExpressionClassifier()


def test_expression_prediction_and_keys(classifier):
    """Assert output dictionary has exactly the 7 canonical emotion keys and sum == 1.0 (+-1e-4)."""
    fixture_path = FIXTURES_DIR / "face_open_eyes.png"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    img_bgr = cv2.imread(str(fixture_path))
    crop_rgb = cv2.resize(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), (224, 224))
    tensor_3d = normalize_crop_to_tensor(crop_rgb, DEFAULT_EXPRESSION_NORM["mean"], DEFAULT_EXPRESSION_NORM["std"])

    result = classifier.predict_single(tensor_3d)

    print("\n[Expression Prediction Result]")
    print(f"  Top Emotion: {result['top']}")
    print(f"  Probs: {result['probs']}")

    # 1. Assert top emotion is valid
    assert result["top"] in CANONICAL_EMOTIONS

    # 2. Assert exactly the 7 keys are present
    probs = result["probs"]
    assert len(probs) == 7
    assert set(probs.keys()) == set(CANONICAL_EMOTIONS)

    # 3. Assert probabilities sum to 1.0 (+-1e-4)
    prob_sum = sum(probs.values())
    assert abs(prob_sum - 1.0) <= 1e-4, f"Probabilities must sum to 1.0 (+-1e-4), got {prob_sum}"

    # 4. Assert top emotion corresponds to the maximum probability
    max_label = max(probs.items(), key=lambda kv: kv[1])[0]
    assert result["top"] == max_label


def test_batch_expression_inference(classifier):
    """Assert batched inference works correctly and empty tensor is handled."""
    dummy_batch = torch.randn(3, 3, 224, 224)
    results = classifier.predict_batch(dummy_batch)
    assert len(results) == 3

    for r in results:
        assert r["top"] in CANONICAL_EMOTIONS
        assert len(r["probs"]) == 7
        assert abs(sum(r["probs"].values()) - 1.0) <= 1e-4

    # Test empty batch
    empty_tensor = torch.empty((0, 3, 224, 224))
    assert classifier.predict_batch(empty_tensor) == []


def test_expression_latency_benchmark(classifier):
    """Measure inference latency on declared hardware (CPU) over timed runs."""
    dummy_input = torch.randn(1, 3, 224, 224)

    # Warm-up (5 runs)
    print("\n[Benchmark] Warming up ViT expression classifier...")
    for _ in range(5):
        _ = classifier.predict_batch(dummy_input)

    # 20 timed runs for CPU report
    num_runs = 20
    print(f"[Benchmark] Executing {num_runs} timed runs on declared hardware ({classifier.device})...")
    latencies_ms = []

    for _ in range(num_runs):
        t0 = time.perf_counter()
        _ = classifier.predict_batch(dummy_input)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    avg_ms = float(np.mean(latencies_ms))
    p50_ms = float(np.median(latencies_ms))
    p95_ms = float(np.percentile(latencies_ms, 95))

    print("\n" + "=" * 60)
    print(f"ViT Facial Expression Model Latency Report ({classifier.device})")
    print("=" * 60)
    print(f"  Runs Tested : {num_runs}")
    print(f"  Mean Latency: {avg_ms:.2f} ms")
    print(f"  P50 Latency : {p50_ms:.2f} ms")
    print(f"  P95 Latency : {p95_ms:.2f} ms")
    print("=" * 60)

    assert avg_ms > 0
