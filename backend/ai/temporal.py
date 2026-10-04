"""Temporal History Queue and Rolling Feature Window.

Implements SYS-4, SYS-6, CON §5 specifications:
- Per-track rolling FIFO buffer of exactly WINDOW_FRAMES (default 30) feature vectors.
- Computes windowed temporal aggregates:
  - PERCLOS: percentage of frames with eyes closed (EAR < EAR_THRESHOLD).
  - Yawn fraction: percentage of frames with wide mouth opening (MAR > MAR_THRESHOLD).
  - Off-task fraction: percentage of frames looking away (|head_yaw| > LIMIT or |head_pitch| > LIMIT).
  - Negative affect: mean probability mass of Sad, Fear, Angry, Disgust.
  - Mean drowsiness probability.
- Auto-purges tracks unseen for longer than TRACK_TTL_S.
- Zero memory leakage under high volume track churn.
"""

from collections import deque
from dataclasses import dataclass, field
import time
from typing import Any, Optional, Sequence
import numpy as np
import torch

from ai.expression import CANONICAL_EMOTIONS

# Default contract thresholds (configurable via env / params)
DEFAULT_WINDOW_FRAMES = 30
DEFAULT_TRACK_TTL_S = 5.0
DEFAULT_EAR_CLOSED_THRESHOLD = 0.20
DEFAULT_MAR_YAWN_THRESHOLD = 0.50
DEFAULT_HEAD_LIMIT_DEG = 25.0


@dataclass
class FrameFeatureSample:
    """Atomic feature sample for one face in one frame."""
    ear: float
    mar: float
    head_yaw: float
    head_pitch: float
    p_drowsy: float
    emotion_probs: dict[str, float]
    timestamp: float

    def to_vector(self) -> np.ndarray:
        """Convert sample into a 12-dimensional feature vector.

        [ear, mar, yaw, pitch, p_drowsy, p_Angry, p_Disgust, p_Fear, p_Happy, p_Sad, p_Surprise, p_Neutral]
        """
        emo_vals = [self.emotion_probs.get(e, 0.0) for e in CANONICAL_EMOTIONS]
        vec = [
            self.ear,
            self.mar,
            self.head_yaw / 90.0,    # Normalized orientation
            self.head_pitch / 90.0,
            self.p_drowsy,
        ] + emo_vals
        return np.array(vec, dtype=np.float32)


class TrackTemporalBuffer:
    """Fixed-capacity rolling history buffer for a single tracked face."""

    def __init__(self, track_id: int, label: str, window_frames: int = DEFAULT_WINDOW_FRAMES) -> None:
        self.track_id = track_id
        self.label = label
        self.window_frames = window_frames
        self.queue: deque[FrameFeatureSample] = deque(maxlen=window_frames)
        self.last_seen: float = time.monotonic()

    def push(self, sample: FrameFeatureSample) -> None:
        """Push a new frame sample into the FIFO queue."""
        self.queue.append(sample)
        self.last_seen = sample.timestamp

    @property
    def size(self) -> int:
        return len(self.queue)

    def compute_perclos(self, ear_threshold: float = DEFAULT_EAR_CLOSED_THRESHOLD) -> float:
        """Compute PERCLOS: fraction of frames where eyes are closed (EAR < threshold)."""
        if not self.queue:
            return 0.0
        closed_count = sum(1 for s in self.queue if s.ear < ear_threshold)
        return float(closed_count / len(self.queue))

    def compute_yawn_fraction(self, mar_threshold: float = DEFAULT_MAR_YAWN_THRESHOLD) -> float:
        """Compute fraction of frames where mouth is wide open (MAR > threshold)."""
        if not self.queue:
            return 0.0
        yawn_count = sum(1 for s in self.queue if s.mar > mar_threshold)
        return float(yawn_count / len(self.queue))

    def compute_off_task_fraction(self, head_limit_deg: float = DEFAULT_HEAD_LIMIT_DEG) -> float:
        """Compute fraction of frames where head orientation exceeds angle threshold."""
        if not self.queue:
            return 0.0
        off_count = sum(
            1 for s in self.queue
            if abs(s.head_yaw) > head_limit_deg or abs(s.head_pitch) > head_limit_deg
        )
        return float(off_count / len(self.queue))

    def compute_mean_p_drowsy(self) -> float:
        """Compute rolling average of p_drowsy across window."""
        if not self.queue:
            return 0.0
        return float(np.mean([s.p_drowsy for s in self.queue]))

    def compute_mean_neg_affect(self) -> float:
        """Compute rolling average of negative affect (Sad + Fear + Angry + Disgust)."""
        if not self.queue:
            return 0.0
        neg_masses = []
        for s in self.queue:
            p_neg = (
                s.emotion_probs.get("Sad", 0.0) +
                s.emotion_probs.get("Fear", 0.0) +
                s.emotion_probs.get("Angry", 0.0) +
                s.emotion_probs.get("Disgust", 0.0)
            )
            neg_masses.append(p_neg)
        return float(np.mean(neg_masses))

    def get_summary(
        self,
        ear_threshold: float = DEFAULT_EAR_CLOSED_THRESHOLD,
        mar_threshold: float = DEFAULT_MAR_YAWN_THRESHOLD,
        head_limit_deg: float = DEFAULT_HEAD_LIMIT_DEG,
    ) -> dict[str, Any]:
        """Return rolling window metrics conforming to contracts.md §5 and §6."""
        return {
            "perclos": round(self.compute_perclos(ear_threshold), 4),
            "yawn_fraction": round(self.compute_yawn_fraction(mar_threshold), 4),
            "off_task_fraction": round(self.compute_off_task_fraction(head_limit_deg), 4),
            "p_drowsy_mean": round(self.compute_mean_p_drowsy(), 4),
            "neg_affect_mean": round(self.compute_mean_neg_affect(), 4),
            "window_size": len(self.queue),
        }

    def to_tensor(self) -> torch.Tensor:
        """Export rolling window into a (Seq_Len, 12) PyTorch tensor for LSTM aggregator."""
        if not self.queue:
            return torch.zeros((0, 12), dtype=torch.float32)
        vectors = [s.to_vector() for s in self.queue]
        return torch.tensor(np.stack(vectors, axis=0), dtype=torch.float32)


class TemporalManager:
    """Manages rolling feature buffers across multiple active and dynamic tracks."""

    def __init__(
        self,
        window_frames: int = DEFAULT_WINDOW_FRAMES,
        track_ttl_s: float = DEFAULT_TRACK_TTL_S,
        ear_threshold: float = DEFAULT_EAR_CLOSED_THRESHOLD,
        mar_threshold: float = DEFAULT_MAR_YAWN_THRESHOLD,
        head_limit_deg: float = DEFAULT_HEAD_LIMIT_DEG,
    ) -> None:
        self.window_frames = window_frames
        self.track_ttl_s = track_ttl_s
        self.ear_threshold = ear_threshold
        self.mar_threshold = mar_threshold
        self.head_limit_deg = head_limit_deg

        self._buffers: dict[int, TrackTemporalBuffer] = {}

    def update_track(
        self,
        track_id: int,
        label: str,
        ear: float,
        mar: float,
        head_yaw: float,
        head_pitch: float,
        p_drowsy: float,
        emotion_probs: dict[str, float],
        timestamp: Optional[float] = None,
    ) -> TrackTemporalBuffer:
        """Push a feature vector to a track's temporal buffer (auto-creating buffer if needed)."""
        ts = timestamp if timestamp is not None else time.monotonic()

        if track_id not in self._buffers:
            self._buffers[track_id] = TrackTemporalBuffer(
                track_id=track_id,
                label=label,
                window_frames=self.window_frames,
            )

        buf = self._buffers[track_id]
        sample = FrameFeatureSample(
            ear=ear,
            mar=mar,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            p_drowsy=p_drowsy,
            emotion_probs=emotion_probs,
            timestamp=ts,
        )
        buf.push(sample)
        return buf

    def purge_stale_tracks(self, current_time: Optional[float] = None) -> list[int]:
        """Remove tracks that have not been observed for longer than track_ttl_s."""
        now = current_time if current_time is not None else time.monotonic()
        stale_ids = [
            tid for tid, buf in self._buffers.items()
            if (now - buf.last_seen) > self.track_ttl_s
        ]
        for tid in stale_ids:
            del self._buffers[tid]
        return stale_ids

    def get_track_summary(self, track_id: int) -> Optional[dict[str, Any]]:
        """Retrieve computed window aggregates for a track."""
        buf = self._buffers.get(track_id)
        if buf is None:
            return None
        return buf.get_summary(
            ear_threshold=self.ear_threshold,
            mar_threshold=self.mar_threshold,
            head_limit_deg=self.head_limit_deg,
        )

    def get_track_buffer(self, track_id: int) -> Optional[TrackTemporalBuffer]:
        """Retrieve buffer instance for a track."""
        return self._buffers.get(track_id)

    @property
    def active_track_ids(self) -> list[int]:
        return list(self._buffers.keys())

    @property
    def count(self) -> int:
        return len(self._buffers)

    def clear(self) -> None:
        """Clear all buffers."""
        self._buffers.clear()
