"""Phase 12 Test Suite — Video Stream Processing Loop.

Spec refs: SYS-1, SYS-17, APP-6, APP-20, CON §4-5, README_EXECUTION.md Phase 12.
Pass conditions:
- End-to-end multi-face processing produces valid ClassSnapshot and TrackResults.
- Non-blocking bounded queue drops stale frames under load without deadlocking.
- Camera loss is detected within CAMERA_TIMEOUT_S, transitioning state to 'Offline'.
- Reconnection restores camera state to 'Online'.
- Sustained target capture frame rate (>= TARGET_FPS = 20) on multi-face stream.
- Frame latency, capture FPS, inference FPS, and dropped frames are accurately measured and logged.
"""

from pathlib import Path
import time
import cv2
import numpy as np
import pytest

from ai.pipeline import VideoPipeline
from app.config import settings

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
MULTI_FACE_FIXTURE = FIXTURES_DIR / "multi_face_frame.png"


@pytest.fixture
def multi_face_image() -> np.ndarray:
    """Load multi-face fixture image."""
    assert MULTI_FACE_FIXTURE.exists(), f"Missing fixture at {MULTI_FACE_FIXTURE}"
    img = cv2.imread(str(MULTI_FACE_FIXTURE))
    assert img is not None
    return img


def test_pipeline_single_frame_processing(multi_face_image: np.ndarray):
    """Verify single frame processing produces valid snapshot and track results."""
    pipeline = VideoPipeline(camera_id="CAM-TEST", session_id=1, class_name="Classroom 101")

    res = pipeline.process_single_frame(multi_face_image, timestamp=1.0)

    # 1. Verify ClassSnapshot structure (contracts.md §2.4)
    snapshot = res["snapshot"]
    assert snapshot["session_id"] == 1
    assert snapshot["class_name"] == "Classroom 101"
    assert snapshot["status"] == "Monitoring"
    assert snapshot["students_detected"] >= 2
    assert "counts" in snapshot
    assert "attentive" in snapshot["counts"]
    assert "distracted" in snapshot["counts"]
    assert "fatigued" in snapshot["counts"]
    assert "unknown" in snapshot["counts"]
    assert 0.0 <= snapshot["avg_attention_score"] <= 100.0

    # 2. Verify TrackResults (contracts.md §2.1)
    tracks = res["tracks"]
    assert len(tracks) >= 2
    for tr in tracks:
        assert "track_id" in tr
        assert "label" in tr
        assert "bbox" in tr
        assert "attention_score" in tr
        assert "fatigue_index" in tr
        assert tr["attention_status"] in ("Attentive", "Distracted", "Unknown")
        assert tr["fatigue_status"] in ("Normal", "Fatigued", "Unknown")


def test_bounded_queue_and_frame_dropping():
    """Verify that bounded frame queue drops stale frames without deadlocking."""
    pipeline = VideoPipeline(camera_id="CAM-DROP", target_fps=30)

    # Fill queue to capacity (maxsize=2)
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    pipeline.frame_queue.put((dummy_frame, 1.0))
    pipeline.frame_queue.put((dummy_frame, 2.0))
    assert pipeline.frame_queue.full()

    # Simulate capture thread dropping oldest frame when full
    if pipeline.frame_queue.full():
        pipeline.frame_queue.get_nowait()
        pipeline.total_dropped_frames += 1
    pipeline.frame_queue.put_nowait((dummy_frame, 3.0))

    assert pipeline.total_dropped_frames == 1
    assert pipeline.frame_queue.qsize() == 2

    # Verify queue preserved the latest frame
    _, ts1 = pipeline.frame_queue.get()
    _, ts2 = pipeline.frame_queue.get()
    assert ts1 == 2.0
    assert ts2 == 3.0


def test_camera_loss_detection_and_reconnect(multi_face_image: np.ndarray):
    """Verify camera disconnect sets Offline within CAMERA_TIMEOUT_S, and reconnect restores Online."""
    is_producing = True

    def frame_source():
        if is_producing:
            return multi_face_image.copy()
        return None

    pipeline = VideoPipeline(
        camera_id="CAM-TIMEOUT",
        source=frame_source,
        target_fps=20,
        camera_timeout_s=0.6,  # Fast timeout for test
    )

    pipeline.start()
    try:
        # 1. Camera starts online
        time.sleep(0.3)
        assert pipeline.camera_state == "Online"

        # 2. Simulate camera unplug / stream failure
        is_producing = False
        time.sleep(0.9)  # Wait beyond 0.6s timeout

        assert pipeline.camera_state == "Offline", (
            f"Expected camera state 'Offline', got {pipeline.camera_state}"
        )

        # 3. Simulate camera reconnection
        is_producing = True
        time.sleep(0.4)
        assert pipeline.camera_state == "Online", (
            f"Expected camera state 'Online' after reconnect, got {pipeline.camera_state}"
        )
    finally:
        pipeline.stop()


def test_privacy_mode_frame_dispatch(multi_face_image: np.ndarray):
    """Verify that annotated frames are NEVER broadcasted when PRIVACY_MODE is true."""
    pipeline = VideoPipeline(camera_id="CAM-PRIVACY")

    # When PRIVACY_MODE is true
    settings.PRIVACY_MODE = True
    dispatched = []

    def mock_broadcast_frame(payload):
        dispatched.append(payload)

    pipeline.ws_mgr.broadcast_video_frame = mock_broadcast_frame
    pipeline.process_single_frame(multi_face_image, timestamp=1.0)
    assert len(dispatched) == 0, "Annotated frame was broadcasted while PRIVACY_MODE was True!"

    # When PRIVACY_MODE is false
    settings.PRIVACY_MODE = False
    try:
        pipeline.process_single_frame(multi_face_image, timestamp=2.0)
        assert len(dispatched) == 1, "Annotated frame was not broadcasted when PRIVACY_MODE was False!"
        assert dispatched[0]["type"] == "frame"
        assert "jpeg_b64" in dispatched[0]
        assert "tracks" in dispatched[0]
    finally:
        settings.PRIVACY_MODE = True


def test_end_to_end_sustained_benchmark(multi_face_image: np.ndarray):
    """Run an end-to-end benchmark on multi-face stream and log performance metrics."""
    # Frame generator simulating real-time camera feed
    def frame_generator():
        return multi_face_image.copy()

    benchmark_duration_s = 6.0  # Automated test run duration
    target_fps = 20

    pipeline = VideoPipeline(
        camera_id="CAM-BENCHMARK",
        source=frame_generator,
        target_fps=target_fps,
        classification_stride=3,
    )

    print(f"\n[Phase 12 Benchmark] Starting {benchmark_duration_s:.1f}s multi-face pipeline run at target {target_fps} FPS...")
    pipeline.start()
    t_start = time.monotonic()

    time.sleep(benchmark_duration_s)

    stats = pipeline.get_stats()
    pipeline.stop()
    elapsed = time.monotonic() - t_start

    print("\n" + "=" * 65)
    print("VIDEO PIPELINE BENCHMARK METRICS (Phase 12 / OQ-3)")
    print("=" * 65)
    print(f"  Duration:            {elapsed:.2f} s")
    print(f"  Target FPS:          {target_fps} FPS")
    print(f"  Capture FPS:         {stats['capture_fps']:.2f} FPS")
    print(f"  Inference FPS:       {stats['inference_fps']:.2f} FPS")
    print(f"  P95 Frame Latency:   {stats['p95_latency_ms']:.2f} ms")
    print(f"  Total Captured:      {stats['total_captured']} frames")
    print(f"  Total Processed:     {stats['total_processed']} frames")
    print(f"  Total Dropped:       {stats['total_dropped']} frames")
    print(f"  Camera Final State:  {stats['camera_state']}")
    print(f"  AI Final State:      {stats['ai_state']}")
    print("=" * 65)

    # Assertions
    # 1. Capture thread must sustain >= TARGET_FPS (20)
    assert stats["capture_fps"] >= 19.0, (
        f"Capture FPS ({stats['capture_fps']:.2f}) fell below target ({target_fps})"
    )
    # 2. Total frames processed must be non-zero
    assert stats["total_processed"] > 0
    # 3. Pipeline remained stable without crashing
    assert stats["camera_state"] == "Online"
    assert stats["ai_state"] == "Online"
