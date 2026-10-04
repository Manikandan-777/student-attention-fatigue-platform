"""Phase 8 Test Suite — LSTM Sequence Aggregator.

Spec refs: SYS-6, D10, OQ-2, implementation.md Phase 8.
Pass conditions:
- Missing weights initializes in 'heuristic' mode without error (Decision D10).
- Forward pass produces valid hidden-state outputs with expected temporal dimensions.
- Supports variable sequence lengths and empty sequences.
- Successfully loads trained weights and transitions model_mode to 'lstm'.
- Integrates seamlessly with Phase 7 TrackTemporalBuffer.to_tensor().
"""

import tempfile
from pathlib import Path
import pytest
import torch

from ai.lstm_attention import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_HIDDEN_DIM,
    LSTMAggregator,
    LSTMSequenceModel,
)
from ai.temporal import FrameFeatureSample, TrackTemporalBuffer


def test_missing_weights_flags_heuristic_mode():
    """Verify that absent weights initialize the aggregator in heuristic mode without error."""
    # Point to a guaranteed non-existent file
    bogus_path = Path("models/non_existent_weights.pt")
    agg = LSTMAggregator(weights_path=bogus_path)

    assert agg.model_mode == "heuristic", f"Expected 'heuristic', got {agg.model_mode}"

    # Forward pass must still succeed without error
    dummy_input = torch.randn(2, 30, DEFAULT_EMBEDDING_DIM)
    out = agg(dummy_input)

    assert out.model_mode == "heuristic"
    assert out.sequence_features.shape == (2, 30, DEFAULT_HIDDEN_DIM)
    assert out.last_hidden.shape == (2, DEFAULT_HIDDEN_DIM)


def test_forward_pass_dimensions():
    """Verify standard forward pass input/output dimensions and shape handling."""
    agg = LSTMAggregator(weights_path=None, hidden_dim=64, num_layers=2)

    # 1. Batched 3D input: (Batch=4, Seq_Len=30, Dim=12)
    x_3d = torch.randn(4, 30, 12)
    out_3d = agg.forward(x_3d)

    assert out_3d.batch_size == 4
    assert out_3d.seq_len == 30
    assert out_3d.sequence_features.shape == (4, 30, 64)
    assert out_3d.last_hidden.shape == (4, 64)

    # 2. Single 2D sequence input: (Seq_Len=30, Dim=12) -> auto-unsqueezed to batch 1
    x_2d = torch.randn(30, 12)
    out_2d = agg.forward(x_2d)

    assert out_2d.batch_size == 1
    assert out_2d.seq_len == 30
    assert out_2d.sequence_features.shape == (1, 30, 64)
    assert out_2d.last_hidden.shape == (1, 64)

    # 3. Invalid shapes must raise ValueError
    with pytest.raises(ValueError):
        agg.forward(torch.randn(12))  # 1D tensor

    with pytest.raises(ValueError):
        agg.forward(torch.randn(2, 30, 15))  # Wrong embedding dim


def test_bidirectional_mode():
    """Verify bidirectional mode scales output dimension by 2."""
    agg = LSTMAggregator(weights_path=None, hidden_dim=64, bidirectional=True)
    x = torch.randn(2, 30, 12)
    out = agg(x)

    assert out.sequence_features.shape == (2, 30, 128)
    assert out.last_hidden.shape == (2, 128)


def test_weights_saving_loading_sets_lstm_mode():
    """Verify that saving and loading weights transitions model_mode to 'lstm'."""
    # Create temporary weights file
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create a model and save its state dict
        model = LSTMSequenceModel(input_dim=12, hidden_dim=64, num_layers=2)
        torch.save(model.state_dict(), tmp_path)

        # Initialize aggregator pointing to existing weights
        agg = LSTMAggregator(weights_path=tmp_path)
        assert agg.model_mode == "lstm", f"Expected 'lstm', got {agg.model_mode}"

        x = torch.randn(1, 30, 12)
        out = agg(x)
        assert out.model_mode == "lstm"

        # Runtime reload test
        agg2 = LSTMAggregator(weights_path=None)
        assert agg2.model_mode == "heuristic"
        loaded = agg2.load_weights(tmp_path)
        assert loaded is True
        assert agg2.model_mode == "lstm"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_variable_and_empty_sequence_lengths():
    """Verify handling of varying sequence lengths (1 to 30) and empty sequences."""
    agg = LSTMAggregator(weights_path=None, hidden_dim=64)

    # Varying sequence lengths
    for seq_len in [1, 5, 15, 30]:
        x = torch.randn(2, seq_len, 12)
        out = agg(x)
        assert out.sequence_features.shape == (2, seq_len, 64)
        assert out.last_hidden.shape == (2, 64)

    # Empty sequence
    empty_x = torch.zeros(1, 0, 12)
    empty_out = agg(empty_x)
    assert empty_out.seq_len == 0
    assert empty_out.sequence_features.shape == (1, 0, 64)
    assert empty_out.last_hidden.shape == (1, 64)


def test_integration_with_temporal_buffer():
    """Verify direct integration with TrackTemporalBuffer from Phase 7."""
    buf = TrackTemporalBuffer(track_id=1, label="S001", window_frames=30)
    dummy_emotions = {
        "Angry": 0.0, "Disgust": 0.0, "Fear": 0.0, "Happy": 0.8,
        "Sad": 0.0, "Surprise": 0.1, "Neutral": 0.1,
    }

    # Fill buffer with 30 frames
    for i in range(30):
        sample = FrameFeatureSample(
            ear=0.28,
            mar=0.15,
            head_yaw=2.0,
            head_pitch=1.0,
            p_drowsy=0.05,
            emotion_probs=dummy_emotions,
            timestamp=float(i),
        )
        buf.push(sample)

    # Export tensor from Phase 7 buffer
    tensor = buf.to_tensor()
    assert tensor.shape == (30, 12)

    # Feed into Phase 8 LSTM aggregator
    agg = LSTMAggregator(weights_path=None)
    out = agg(tensor)

    assert out.batch_size == 1
    assert out.seq_len == 30
    assert out.sequence_features.shape == (1, 30, DEFAULT_HIDDEN_DIM)
    assert out.last_hidden.shape == (1, DEFAULT_HIDDEN_DIM)
    assert not torch.isnan(out.sequence_features).any()
    assert not torch.isnan(out.last_hidden).any()
