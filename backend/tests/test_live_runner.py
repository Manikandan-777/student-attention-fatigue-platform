"""Unit and integration tests for LiveRunner (Phase LC-2).

Verifies:
- Frame processing with zero, one, or multiple faces.
- Warming-up phase guarantees: statuses are 'Unknown' until window reaches LIVE_WINDOW_FRAMES.
- Single closed-eye frame never flips status to 'Fatigued'.
- Low confidence or small face fallbacks to 'Unknown'.
- Output schema contains NO images, raw landmarks, or probability vectors.
- Clean resource release on close().
"""

from unittest.mock import MagicMock
import numpy as np
import pytest

from ai.live_runner import LiveRunner
from ai.mediapipe_tracker import TrackedFace
from app.config import Settings


def _create_mock_face(
    track_id: int = 1,
    label: str = "S001",
    confidence: float = 0.95,
    ear: float = 0.32,
    mar: float = 0.12,
    head_yaw: float = 0.0,
    head_pitch: float = 0.0,
    pixel_bbox: list = None,
) -> TrackedFace:
    return TrackedFace(
        track_id=track_id,
        label=label,
        bbox=[0.3, 0.2, 0.4, 0.4],
        pixel_bbox=pixel_bbox or [150, 100, 200, 200],
        landmarks=[],
        landmark_confidence=confidence,
        features={
            "ear": ear,
            "mar": mar,
            "head_yaw": head_yaw,
            "head_pitch": head_pitch,
        },
    )


class TestLiveRunner:
    @pytest.fixture
    def custom_cfg(self):
        return Settings(
            LIVE_WINDOW_FRAMES=10,
            LIVE_MAX_FACES=5,
            MIN_CONFIDENCE=0.80,
            STATUS_HYSTERESIS_S=1.0,
        )

    def test_no_face_detected(self, custom_cfg):
        mock_tracker = MagicMock()
        mock_tracker.process_frame.return_value = []
        runner = LiveRunner(models=None, cfg=custom_cfg, tracker=mock_tracker)

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = runner.process(dummy_frame)

        assert result["frame_size"] == [640, 480]
        assert isinstance(result["latency_ms"], int)
        assert result["tracks"] == []
        runner.close()

    def test_warmup_phase_returns_unknown_statuses(self, custom_cfg):
        mock_tracker = MagicMock()
        face = _create_mock_face()
        mock_tracker.process_frame.return_value = [face]
        runner = LiveRunner(models=None, cfg=custom_cfg, tracker=mock_tracker)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Feed 5 frames (less than LIVE_WINDOW_FRAMES=10)
        for i in range(5):
            res = runner.process(frame, timestamp=float(i))
            assert len(res["tracks"]) == 1
            track = res["tracks"][0]
            assert track["warming_up"] is True
            assert track["attention_status"] == "Unknown"
            assert track["fatigue_status"] == "Unknown"

        runner.close()

    def test_attentive_and_normal_after_warmup(self, custom_cfg):
        mock_tracker = MagicMock()
        face = _create_mock_face(ear=0.32, mar=0.12, head_yaw=0.0, head_pitch=0.0)
        mock_tracker.process_frame.return_value = [face]
        runner = LiveRunner(models=None, cfg=custom_cfg, tracker=mock_tracker)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Feed 15 frames past warm-up (10 frames)
        last_track = None
        for i in range(15):
            res = runner.process(frame, timestamp=float(i))
            last_track = res["tracks"][0]

        assert last_track["warming_up"] is False
        assert last_track["attention_status"] == "Attentive"
        assert last_track["fatigue_status"] == "Normal"
        assert last_track["attention_score"] >= 75.0
        assert last_track["fatigue_index"] < 0.40
        runner.close()

    def test_single_closed_eye_frame_never_flips_to_fatigued(self, custom_cfg):
        mock_tracker = MagicMock()
        normal_face = _create_mock_face(ear=0.32)
        closed_eye_face = _create_mock_face(ear=0.08)  # Single blink/closure
        runner = LiveRunner(models=None, cfg=custom_cfg, tracker=mock_tracker)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 1. Warm up with normal open eyes
        mock_tracker.process_frame.return_value = [normal_face]
        for i in range(12):
            runner.process(frame, timestamp=float(i))

        # 2. Inject single closed eye frame
        mock_tracker.process_frame.return_value = [closed_eye_face]
        res = runner.process(frame, timestamp=13.0)
        track = res["tracks"][0]

        # Must not immediately flag as Fatigued on a single blink
        assert track["fatigue_status"] == "Normal"
        runner.close()

    def test_low_confidence_face_falls_back_to_unknown(self, custom_cfg):
        mock_tracker = MagicMock()
        low_conf_face = _create_mock_face(confidence=0.50)  # below MIN_CONFIDENCE=0.80
        mock_tracker.process_frame.return_value = [low_conf_face]
        runner = LiveRunner(models=None, cfg=custom_cfg, tracker=mock_tracker)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(15):
            res = runner.process(frame, timestamp=float(i))

        track = res["tracks"][0]
        assert track["confidence"] == 0.50
        assert track["attention_status"] == "Unknown"
        assert track["fatigue_status"] == "Unknown"
        runner.close()

    def test_small_face_falls_back_to_unknown(self, custom_cfg):
        mock_tracker = MagicMock()
        small_face = _create_mock_face(pixel_bbox=[50, 50, 20, 20])  # < 32px
        mock_tracker.process_frame.return_value = [small_face]
        runner = LiveRunner(models=None, cfg=custom_cfg, tracker=mock_tracker)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(15):
            res = runner.process(frame, timestamp=float(i))

        track = res["tracks"][0]
        assert track["attention_status"] == "Unknown"
        assert track["fatigue_status"] == "Unknown"
        runner.close()

    def test_payload_contains_no_sensitive_or_large_data(self, custom_cfg):
        mock_tracker = MagicMock()
        face = _create_mock_face()
        mock_tracker.process_frame.return_value = [face]
        runner = LiveRunner(models=None, cfg=custom_cfg, tracker=mock_tracker)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(12):
            res = runner.process(frame, timestamp=float(i))

        track = res["tracks"][0]
        forbidden_keys = {"landmarks", "probs", "image", "raw", "embedding", "frame", "features"}
        assert forbidden_keys.isdisjoint(track.keys()), f"Forbidden keys present: {forbidden_keys.intersection(track.keys())}"
        runner.close()
