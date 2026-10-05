"""Live Camera Inference Runner — Phase LC-2.

Performs isolated, single-connection live video frame analysis:
- Owns separate MultiFaceTracker, TemporalManager, and ScoringEngine instances.
- Reuses shared, read-only model weights (MobileViT, ViT) under torch.inference_mode().
- Enforces warming-up state (both statuses 'Unknown' until window is full).
- Suppresses alerts and database writes entirely (isolated from session pipeline).
- Emits canonical LiveTrackResult dictionaries adhering to contracts.md §6.3.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

from ai.drowsiness import DrowsinessClassifier
from ai.expression import CANONICAL_EMOTIONS, ExpressionClassifier
from ai.lstm_attention import LSTMAggregator
from ai.mediapipe_tracker import MultiFaceTracker, TrackedFace
from ai.roi import FaceROIExtractor
from ai.scoring import ScoringEngine
from ai.temporal import TemporalManager
from app.config import Settings, settings

logger = logging.getLogger("ai.live_runner")


@dataclass
class SharedLiveModels:
    """Read-only shared neural network model registry for live camera workers."""
    roi_extractor: FaceROIExtractor
    drowsiness_classifier: DrowsinessClassifier
    expression_classifier: ExpressionClassifier
    lstm_aggregator: LSTMAggregator


_SHARED_MODELS: Optional[SharedLiveModels] = None


def get_shared_live_models(models_dir: Optional[Path] = None) -> SharedLiveModels:
    """Retrieve or initialize singleton read-only deep learning models."""
    global _SHARED_MODELS
    if _SHARED_MODELS is None:
        base_dir = models_dir or (Path(__file__).resolve().parents[1] / "models")
        logger.info("Initializing shared live models from %s", base_dir)
        roi_extractor = FaceROIExtractor(models_base_dir=base_dir)
        drowsiness_classifier = DrowsinessClassifier(model_dir=base_dir / "drowsiness")
        expression_classifier = ExpressionClassifier(model_dir=base_dir / "expression")
        lstm_aggregator = LSTMAggregator(weights_path=None)
        _SHARED_MODELS = SharedLiveModels(
            roi_extractor=roi_extractor,
            drowsiness_classifier=drowsiness_classifier,
            expression_classifier=expression_classifier,
            lstm_aggregator=lstm_aggregator,
        )
    return _SHARED_MODELS


class LiveRunner:
    """Analyses frames for ONE live connection.

    Owns its own tracker, temporal buffers and scorer.
    Never interacts with the database or global alert dispatchers.
    """

    def __init__(
        self,
        models: Optional[SharedLiveModels] = None,
        cfg: Optional[Settings] = None,
        tracker: Optional[MultiFaceTracker] = None,
    ) -> None:
        self.cfg = cfg or settings
        self.models = models
        if self.models is None:
            try:
                self.models = get_shared_live_models()
            except Exception as exc:
                logger.warning("Could not load deep learning models for LiveRunner: %s", exc)
                self.models = None

        # Each live connection owns its own dedicated tracker instance
        self.tracker = tracker or MultiFaceTracker(max_num_faces=self.cfg.LIVE_MAX_FACES)

        # Dedicated temporal queue and scoring state machine
        self.temporal_manager = TemporalManager(
            window_frames=self.cfg.LIVE_WINDOW_FRAMES,
            track_ttl_s=self.cfg.STATUS_HYSTERESIS_S * 2,
        )
        self.scoring_engine = ScoringEngine(
            min_confidence=self.cfg.MIN_CONFIDENCE,
            status_hysteresis_s=self.cfg.STATUS_HYSTERESIS_S,
            fatigue_persist_s=self.cfg.FATIGUE_PERSIST_S,
            distraction_persist_s=self.cfg.DISTRACTION_PERSIST_S,
            alert_cooldown_s=self.cfg.ALERT_COOLDOWN_S,
        )

        # Per-track smoothed expression probabilities (EMA)
        self._smoothed_emotions: Dict[int, Dict[str, float]] = {}
        self._cached_drowsiness: Dict[int, Tuple[str, float]] = {}
        self._cached_expression: Dict[int, Tuple[str, Dict[str, float]]] = {}
        self._frame_count = 0

    def process(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute face tracking and validation on a single incoming frame."""
        t0 = time.perf_counter()
        ts = timestamp if timestamp is not None else time.monotonic()
        h, w = frame_bgr.shape[:2]
        self._frame_count += 1

        # 1. Detect and track faces (MediaPipe)
        tracked_faces = self.tracker.process_frame(frame_bgr)

        # 2. Deep neural classification (if models available)
        if tracked_faces and self.models is not None:
            try:
                # Prepare crops in memory
                drowsy_tensor, valid_drowsy = self.models.roi_extractor.prepare_drowsiness_batch(
                    frame_bgr, tracked_faces
                )
                expr_tensor, valid_expr = self.models.roi_extractor.prepare_expression_batch(
                    frame_bgr, tracked_faces
                )

                if valid_drowsy:
                    d_preds = self.models.drowsiness_classifier.predict_batch(drowsy_tensor)
                    for face, pred in zip(valid_drowsy, d_preds):
                        self._cached_drowsiness[face.track_id] = (pred["label"], pred["p_drowsy"])

                if valid_expr:
                    e_preds = self.models.expression_classifier.predict_batch(expr_tensor)
                    for face, pred in zip(valid_expr, e_preds):
                        self._cached_expression[face.track_id] = (pred["top"], pred["probs"])
            except Exception as exc:
                logger.warning("LiveRunner deep inference failed on frame: %s", exc)

        # 3. Purge expired tracks
        self.temporal_manager.purge_stale_tracks(current_time=ts)
        active_ids = {f.track_id for f in tracked_faces}
        self._smoothed_emotions = {
            tid: em for tid, em in self._smoothed_emotions.items() if tid in active_ids
        }
        self._cached_drowsiness = {
            tid: dr for tid, dr in self._cached_drowsiness.items() if tid in active_ids
        }
        self._cached_expression = {
            tid: ex for tid, ex in self._cached_expression.items() if tid in active_ids
        }

        # 4. Score and format canonical LiveTrackResult output
        live_tracks: List[Dict[str, Any]] = []

        for face in tracked_faces:
            tid = face.track_id
            drowsy_label, p_drowsy = self._cached_drowsiness.get(tid, ("Non Drowsy", 0.05))
            top_emo, emo_probs = self._cached_expression.get(
                tid,
                ("Neutral", {e: (1.0 if e == "Neutral" else 0.0) for e in CANONICAL_EMOTIONS}),
            )

            # Update temporal buffer
            buf = self.temporal_manager.update_track(
                track_id=tid,
                label=face.label,
                ear=face.features.get("ear", 0.30),
                mar=face.features.get("mar", 0.15),
                head_yaw=face.features.get("head_yaw", 0.0),
                head_pitch=face.features.get("head_pitch", 0.0),
                p_drowsy=p_drowsy,
                emotion_probs=emo_probs,
                timestamp=ts,
            )
            summary = buf.get_summary()

            # Warm-up check: window must be completely full
            warming_up = (buf.size < self.cfg.LIVE_WINDOW_FRAMES)

            # Score frame
            model_mode = self.models.lstm_aggregator.model_mode if self.models else "heuristic"
            scored_result, _ = self.scoring_engine.process_frame(
                track_id=tid,
                label=face.label,
                bbox=face.bbox,
                landmark_confidence=face.landmark_confidence,
                ear=face.features.get("ear", 0.30),
                mar=face.features.get("mar", 0.15),
                head_yaw=face.features.get("head_yaw", 0.0),
                head_pitch=face.features.get("head_pitch", 0.0),
                perclos=summary["perclos"],
                yawn_fraction=summary["yawn_fraction"],
                off_task_fraction=summary["off_task_fraction"],
                p_drowsy=p_drowsy,
                drowsiness_label=drowsy_label,
                emotion_probs=emo_probs,
                top_emotion=top_emo,
                timestamp=ts,
                model_mode=model_mode,
            )

            # Usability check: face size and landmark confidence
            pw = face.pixel_bbox[2] if len(face.pixel_bbox) >= 4 else 0
            ph = face.pixel_bbox[3] if len(face.pixel_bbox) >= 4 else 0
            is_usable = (
                pw >= 32
                and ph >= 32
                and face.landmark_confidence >= self.cfg.MIN_CONFIDENCE
            )

            # Determine statuses (Unknown during warmup or when low quality)
            if warming_up or not is_usable:
                attention_status = "Unknown"
                fatigue_status = "Unknown"
            else:
                attention_status = scored_result["attention_status"]
                fatigue_status = scored_result["fatigue_status"]

            # Smooth expression probabilities (EMA)
            current_smoothed = self._smoothed_emotions.get(tid, emo_probs.copy())
            alpha = 0.30
            for emo_k, emo_v in emo_probs.items():
                current_smoothed[emo_k] = alpha * emo_v + (1.0 - alpha) * current_smoothed.get(emo_k, 0.0)
            self._smoothed_emotions[tid] = current_smoothed

            # Find top smoothed emotion
            best_emo, best_prob = max(current_smoothed.items(), key=lambda item: item[1])

            expression_obj: Optional[Dict[str, Any]] = None
            if is_usable and best_prob >= self.cfg.LIVE_EMOTION_MIN_CONF:
                expression_obj = {
                    "top": best_emo,
                    "confidence": round(float(best_prob), 2),
                }

            live_tracks.append({
                "track_id": face.track_id,
                "label": face.label,
                "bbox": [round(float(v), 4) for v in face.bbox],
                "bbox_normalized": True,
                "warming_up": bool(warming_up),
                "attention_status": attention_status,
                "fatigue_status": fatigue_status,
                "attention_score": round(float(scored_result["attention_score"]), 1),
                "fatigue_index": round(float(scored_result["fatigue_index"]), 2),
                "confidence": round(float(face.landmark_confidence), 2),
                "expression": expression_obj,
            })

        latency_ms = round((time.perf_counter() - t0) * 1000)
        return {
            "frame_size": [w, h],
            "latency_ms": latency_ms,
            "tracks": live_tracks,
        }

    def close(self) -> None:
        """Release underlying MediaPipe and temporal resources cleanly."""
        if hasattr(self.tracker, "landmarker") and self.tracker.landmarker is not None:
            try:
                self.tracker.landmarker.close()
            except Exception as exc:
                logger.debug("Tracker landmarker close: %s", exc)
        self.temporal_manager.clear()
        self.scoring_engine.clear()
        self._smoothed_emotions.clear()
        self._cached_drowsiness.clear()
        self._cached_expression.clear()
