"""Phase 9 Test Suite — Temporal Self-Attention Layer.

Spec refs: SYS-7, implementation.md Phase 9, README_EXECUTION.md Phase 9.
Pass conditions:
- Attention weights sum to 1.0 per sequence across batches (within 1e-5).
- Returns pooled context vector matching hidden dimension and attention weights of shape (B, T).
- Synthetic sequence with an injected 3-frame eye closure anomaly validates sum-to-1 and shape.
- When fitted/trained, attention dynamically concentrates above-average weight on anomalous frames.
- Masked positions receive zero attention weight.
- Limitation of untrained weights logged per spec.
"""

import logging
import pytest
import torch
import torch.nn as nn

from ai.lstm_attention import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_HIDDEN_DIM,
    LSTMAggregator,
    LSTMAttentionNetwork,
    TemporalAdditiveAttention,
)

logger = logging.getLogger("tests.phase9")


def test_temporal_attention_weights_sum_to_one():
    """Verify that attention weights sum strictly to 1.0 for each sequence in a batch."""
    batch_size = 4
    seq_len = 30
    hidden_dim = 64

    attn = TemporalAdditiveAttention(hidden_dim=hidden_dim, attention_dim=32)
    hidden_states = torch.randn(batch_size, seq_len, hidden_dim)

    context_vec, weights = attn(hidden_states)

    assert context_vec.shape == (batch_size, hidden_dim)
    assert weights.shape == (batch_size, seq_len)

    # Sum of weights across time dimension must equal 1.0 per sequence
    weight_sums = torch.sum(weights, dim=-1)
    expected_sums = torch.ones(batch_size)
    assert torch.allclose(weight_sums, expected_sums, atol=1e-5), (
        f"Expected sum 1.0, got {weight_sums.tolist()}"
    )


def test_synthetic_sequence_with_injected_anomaly():
    """Test on a synthetic sequence with an injected anomaly (eyes closed for 3 frames).

    Verifies shape, sum-to-1, and logs the limitation of untrained weights per spec.
    """
    agg = LSTMAggregator(weights_path=None, hidden_dim=64)

    # 30-frame sequence:
    # Frames 0..19: Normal baseline (EAR=0.30, MAR=0.15, p_drowsy=0.05)
    # Frames 20..22: Injected anomaly (EAR=0.05, MAR=0.15, p_drowsy=0.95) -> sustained eye closure
    # Frames 23..29: Normal baseline
    seq = torch.zeros(1, 30, DEFAULT_EMBEDDING_DIM)

    # Baseline features
    seq[:, :, 0] = 0.30   # EAR
    seq[:, :, 1] = 0.15   # MAR
    seq[:, :, 4] = 0.05   # p_drowsy
    seq[:, :, 11] = 0.90  # Neutral emotion

    # Anomaly injection: 3 consecutive closed-eye frames
    anomaly_indices = [20, 21, 22]
    for idx in anomaly_indices:
        seq[0, idx, 0] = 0.05  # Severe eye closure
        seq[0, idx, 4] = 0.95  # High drowsiness probability
        seq[0, idx, 11] = 0.10

    out = agg(seq)

    # 1. Output shapes
    assert out.sequence_features.shape == (1, 30, 64)
    assert out.context_vector.shape == (1, 64)
    assert out.attention_weights.shape == (1, 30)

    # 2. Sum to 1.0
    w_sum = out.attention_weights.sum().item()
    assert pytest.approx(1.0, abs=1e-5) == w_sum

    # 3. Specification requirement: log untrained weights limitation
    logger.info(
        "[Phase 9 Spec Note] Untrained attention weights produce near-uniform attention "
        "across all time steps (mean weight = %.4f). Actual focus on anomalous frames requires "
        "supervised/fine-tuned training data (Decision D10 / OQ-2).",
        out.attention_weights.mean().item(),
    )


def test_fitted_attention_anomaly_focus():
    """Verify that when fitted to detect fatigue, attention concentrates weight on anomalous frames."""
    torch.manual_seed(42)
    net = LSTMAttentionNetwork(
        input_dim=12,
        hidden_dim=32,
        num_layers=1,
        attention_dim=16,
    )

    # Create synthetic sequence with 3 anomalous frames at index [10, 11, 12]
    seq = torch.zeros(1, 20, 12)
    seq[:, :, 0] = 0.30  # Baseline open eyes
    seq[:, :, 4] = 0.05

    # Anomalous eye closure frames
    anomaly_idx = [10, 11, 12]
    for idx in anomaly_idx:
        seq[0, idx, 0] = 0.02
        seq[0, idx, 4] = 0.98

    target_fatigue = torch.tensor([[1.0]])

    # Train for a few steps to minimize BCE loss against fatigue label
    optimizer = torch.optim.Adam(net.parameters(), lr=0.05)
    loss_fn = nn.BCELoss()

    net.train()
    for _ in range(35):
        optimizer.zero_grad()
        _, _, _, _, fatigue_pred, _ = net(seq)
        loss = loss_fn(fatigue_pred, target_fatigue)
        loss.backward()
        optimizer.step()

    net.eval()
    with torch.no_grad():
        _, _, _, weights, fatigue_pred, _ = net(seq)

    weights_np = weights[0].numpy()
    normal_weights = [weights_np[i] for i in range(20) if i not in anomaly_idx]
    anomaly_weights = [weights_np[i] for i in anomaly_idx]

    mean_anomaly_weight = float(sum(anomaly_weights) / len(anomaly_weights))
    mean_normal_weight = float(sum(normal_weights) / len(normal_weights))

    print(f"\n[Fitted Attention Test] Mean Anomaly Weight: {mean_anomaly_weight:.4f} vs Normal: {mean_normal_weight:.4f}")
    assert mean_anomaly_weight > mean_normal_weight, (
        f"Expected anomaly weight ({mean_anomaly_weight:.4f}) > normal weight ({mean_normal_weight:.4f})"
    )


def test_attention_with_padding_mask():
    """Verify that masked positions receive approximately 0.0 attention weight."""
    hidden_dim = 32
    attn = TemporalAdditiveAttention(hidden_dim=hidden_dim, attention_dim=16)

    # Sequence of length 10, but only first 6 steps are valid
    hidden_states = torch.randn(2, 10, hidden_dim)
    mask = torch.tensor([
        [True, True, True, True, True, True, False, False, False, False],
        [True, True, True, True, False, False, False, False, False, False],
    ], dtype=torch.bool)

    context_vec, weights = attn(hidden_states, mask=mask)

    # Masked positions must have zero weight
    assert torch.allclose(weights[0, 6:], torch.zeros(4), atol=1e-6)
    assert torch.allclose(weights[1, 4:], torch.zeros(6), atol=1e-6)

    # Valid positions must still sum to 1.0
    assert pytest.approx(1.0, abs=1e-5) == weights[0].sum().item()
    assert pytest.approx(1.0, abs=1e-5) == weights[1].sum().item()
