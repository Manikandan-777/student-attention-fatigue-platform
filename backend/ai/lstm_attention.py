"""LSTM Sequence Aggregator and Temporal Self-Attention.

Implements SYS-6, SYS-7, D10, OQ-2:
- Processes sequences of temporal feature vectors (B, T, D=12).
- Temporal Additive Self-Attention computes attention weights across the temporal window.
- Computes attention-weighted context vector (pooled representation).
- Provides optional prediction heads for LSTM-based fatigue & attention scoring (contracts.md §6).
- Gracefully handles absent weights by operating in 'heuristic' mode (D10, OQ-2).
- When trained weights are provided, flags 'lstm' mode.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger("ai.lstm_attention")

DEFAULT_EMBEDDING_DIM = 12
DEFAULT_HIDDEN_DIM = 64
DEFAULT_NUM_LAYERS = 2
DEFAULT_ATTENTION_DIM = 32
DEFAULT_DROPOUT = 0.1
DEFAULT_MODEL_WEIGHTS_PATH = Path(__file__).resolve().parent.parent / "models" / "lstm_attention.pt"


class LSTMSequenceModel(nn.Module):
    """PyTorch LSTM module for temporal sequence processing."""

    def __init__(
        self,
        input_dim: int = DEFAULT_EMBEDDING_DIM,
        hidden_dim: int = DEFAULT_HIDDEN_DIM,
        num_layers: int = DEFAULT_NUM_LAYERS,
        bidirectional: bool = False,
        dropout: float = DEFAULT_DROPOUT,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.output_dim = hidden_dim * (2 if bidirectional else 1)

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )

    def forward(
        self,
        x: torch.Tensor,
        hx: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """Forward pass through LSTM."""
        lstm_out, (h_n, c_n) = self.lstm(x, hx)
        return lstm_out, (h_n, c_n)


class TemporalAdditiveAttention(nn.Module):
    """Additive (Bahdanau-style) Temporal Self-Attention over sequential hidden states.

    Given sequence representations H = [h_1, ..., h_T] in R^(B x T x D):
    1. Score: e_t = v^T * tanh(W_a * h_t + b_a)
    2. Weights: alpha = softmax(e, dim=time) in R^(B x T), sum(alpha) == 1.0
    3. Context vector: c = sum_t (alpha_t * h_t) in R^(B x D)
    """

    def __init__(
        self,
        hidden_dim: int = DEFAULT_HIDDEN_DIM,
        attention_dim: int = DEFAULT_ATTENTION_DIM,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.attention_dim = attention_dim

        self.w_proj = nn.Linear(hidden_dim, attention_dim, bias=True)
        self.v_proj = nn.Linear(attention_dim, 1, bias=False)

    def forward(
        self,
        hidden_states: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute context vector and temporal attention weights.

        Args:
            hidden_states: Tensor of shape (Batch, Seq_Len, Hidden_Dim)
            mask: Optional boolean tensor of shape (Batch, Seq_Len), True for valid positions

        Returns:
            context_vector: Pooled tensor of shape (Batch, Hidden_Dim)
            attention_weights: Normalized weights of shape (Batch, Seq_Len)
        """
        batch_size, seq_len, _ = hidden_states.shape

        if seq_len == 0:
            empty_ctx = torch.zeros((batch_size, self.hidden_dim), device=hidden_states.device)
            empty_weights = torch.zeros((batch_size, 0), device=hidden_states.device)
            return empty_ctx, empty_weights

        # 1. Project: (B, T, D) -> (B, T, A)
        energy = torch.tanh(self.w_proj(hidden_states))

        # 2. Score vector: (B, T, A) -> (B, T, 1) -> (B, T)
        scores = self.v_proj(energy).squeeze(-1)

        # 3. Apply optional mask
        if mask is not None:
            scores = scores.masked_fill(~mask, -1e9)

        # 4. Normalize along time axis
        attention_weights = F.softmax(scores, dim=-1)

        # 5. Compute weighted context vector: (B, 1, T) x (B, T, D) -> (B, 1, D) -> (B, D)
        context_vector = torch.bmm(attention_weights.unsqueeze(1), hidden_states).squeeze(1)

        return context_vector, attention_weights


class LSTMAttentionNetwork(nn.Module):
    """Composite Neural Architecture: LSTM + Temporal Attention + Scoring Heads."""

    def __init__(
        self,
        input_dim: int = DEFAULT_EMBEDDING_DIM,
        hidden_dim: int = DEFAULT_HIDDEN_DIM,
        num_layers: int = DEFAULT_NUM_LAYERS,
        attention_dim: int = DEFAULT_ATTENTION_DIM,
        bidirectional: bool = False,
        dropout: float = DEFAULT_DROPOUT,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.output_dim = hidden_dim * (2 if bidirectional else 1)

        self.lstm = LSTMSequenceModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            bidirectional=bidirectional,
            dropout=dropout,
        )

        self.attention = TemporalAdditiveAttention(
            hidden_dim=self.output_dim,
            attention_dim=attention_dim,
        )

        # Optional prediction heads for fatigue & distraction
        self.fatigue_head = nn.Sequential(
            nn.Linear(self.output_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
        self.distraction_head = nn.Sequential(
            nn.Linear(self.output_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full forward pass: LSTM -> Attention -> Scoring.

        Returns:
            lstm_out: (B, T, Output_Dim)
            last_hidden: (B, Output_Dim)
            context_vector: (B, Output_Dim)
            attention_weights: (B, T)
            fatigue_pred: (B, 1) in [0, 1]
            distraction_pred: (B, 1) in [0, 1]
        """
        lstm_out, (h_n, _) = self.lstm(x)

        if self.bidirectional:
            last_fwd = h_n[-2, :, :]
            last_bwd = h_n[-1, :, :]
            last_hidden = torch.cat([last_fwd, last_bwd], dim=-1)
        else:
            last_hidden = h_n[-1, :, :]

        context_vector, attention_weights = self.attention(lstm_out, mask=mask)
        fatigue_pred = self.fatigue_head(context_vector)
        distraction_pred = self.distraction_head(context_vector)

        return lstm_out, last_hidden, context_vector, attention_weights, fatigue_pred, distraction_pred


@dataclass
class LSTMAttentionOutput:
    """Encapsulates output of LSTM + Temporal Attention sequence processing."""
    sequence_features: torch.Tensor   # (Batch, Seq_Len, Output_Dim)
    last_hidden: torch.Tensor         # (Batch, Output_Dim)
    context_vector: torch.Tensor      # (Batch, Output_Dim)
    attention_weights: torch.Tensor   # (Batch, Seq_Len), strictly sums to 1.0 per item
    model_mode: str                   # 'heuristic' or 'lstm'
    seq_len: int
    batch_size: int
    fatigue_index_lstm: Optional[torch.Tensor] = None   # (Batch, 1)
    distraction_lstm: Optional[torch.Tensor] = None     # (Batch, 1)


# Maintain alias for backward compatibility with Phase 8
LSTMOutput = LSTMAttentionOutput


class LSTMAggregator:
    """Aggregator managing temporal sequence model lifecycle and fallback mode.

    Per Decision D10 / contracts.md §6:
    - If trained weights are found and loaded: model_mode = 'lstm'
    - If weights are absent or untrained: model_mode = 'heuristic'
    """

    def __init__(
        self,
        weights_path: Optional[Union[str, Path]] = DEFAULT_MODEL_WEIGHTS_PATH,
        input_dim: int = DEFAULT_EMBEDDING_DIM,
        hidden_dim: int = DEFAULT_HIDDEN_DIM,
        num_layers: int = DEFAULT_NUM_LAYERS,
        attention_dim: int = DEFAULT_ATTENTION_DIM,
        bidirectional: bool = False,
        dropout: float = DEFAULT_DROPOUT,
        device: Optional[Union[str, torch.device]] = None,
    ) -> None:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.attention_dim = attention_dim
        self.bidirectional = bidirectional
        self.dropout = dropout
        self.output_dim = hidden_dim * (2 if bidirectional else 1)
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        self.model = LSTMAttentionNetwork(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            attention_dim=attention_dim,
            bidirectional=bidirectional,
            dropout=dropout,
        ).to(self.device)

        self.model.eval()
        self.model_mode: str = "heuristic"
        self.weights_path: Optional[Path] = Path(weights_path) if weights_path else None

        if self.weights_path and self.weights_path.is_file():
            self._load_weights(self.weights_path)
        else:
            logger.info(
                "No trained LSTM weights found at %s. Operating in '%s' mode (Decision D10).",
                self.weights_path,
                self.model_mode,
            )

    def _load_weights(self, path: Path) -> bool:
        """Load state dict into model."""
        try:
            state = torch.load(path, map_location=self.device, weights_only=True)
            if isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]
            self.model.load_state_dict(state, strict=False)
            self.model.eval()
            self.model_mode = "lstm"
            logger.info("Successfully loaded LSTM-attention weights from %s. Mode set to 'lstm'.", path)
            return True
        except Exception as exc:
            logger.warning(
                "Failed to load LSTM weights from %s (%s). Reverting to 'heuristic' mode.",
                path,
                exc,
            )
            self.model_mode = "heuristic"
            return False

    def load_weights(self, path: Union[str, Path]) -> bool:
        """Public method to load weights at runtime."""
        p = Path(path)
        if not p.is_file():
            logger.warning("Weights path %s does not exist. Remaining in '%s' mode.", p, self.model_mode)
            self.model_mode = "heuristic"
            return False
        self.weights_path = p
        return self._load_weights(p)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> LSTMAttentionOutput:
        """Run inference across input sequence tensor."""
        if x.ndim == 2:
            x = x.unsqueeze(0)  # Shape (1, Seq_Len, Embedding_Dim)

        if x.ndim != 3:
            raise ValueError(f"Expected 2D or 3D tensor, got shape {x.shape}")

        if x.shape[-1] != self.input_dim:
            raise ValueError(f"Expected embedding dimension {self.input_dim}, got {x.shape[-1]}")

        batch_size, seq_len, _ = x.shape

        if seq_len == 0:
            empty_seq = torch.zeros((batch_size, 0, self.output_dim), device=self.device, dtype=torch.float32)
            empty_last = torch.zeros((batch_size, self.output_dim), device=self.device, dtype=torch.float32)
            empty_weights = torch.zeros((batch_size, 0), device=self.device, dtype=torch.float32)
            return LSTMAttentionOutput(
                sequence_features=empty_seq,
                last_hidden=empty_last,
                context_vector=empty_last,
                attention_weights=empty_weights,
                model_mode=self.model_mode,
                seq_len=0,
                batch_size=batch_size,
            )

        x_dev = x.to(self.device, dtype=torch.float32)
        mask_dev = mask.to(self.device) if mask is not None else None

        with torch.inference_mode():
            lstm_out, last_hidden, ctx_vec, attn_w, fat_p, dist_p = self.model(x_dev, mask=mask_dev)

        return LSTMAttentionOutput(
            sequence_features=lstm_out,
            last_hidden=last_hidden,
            context_vector=ctx_vec,
            attention_weights=attn_w,
            model_mode=self.model_mode,
            seq_len=seq_len,
            batch_size=batch_size,
            fatigue_index_lstm=fat_p,
            distraction_lstm=dist_p,
        )

    def __call__(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> LSTMAttentionOutput:
        return self.forward(x, mask=mask)
