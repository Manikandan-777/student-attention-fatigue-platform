"""Phase 3 Test Suite — MediaPipe Multi-Face Pipeline and Tracking.

Spec refs: SYS-2, SYS-3, SYS-4, CON §2.1, implementation.md Phase 3.
Pass condition:
- All faces in fixtures detected with >= 95% landmark confidence.
- Track IDs persist across consecutive frames without swapping.
- Closed-eye EAR < open-eye EAR.
"""

from pathlib import Path
import cv2
import pytest

from ai.features import calculate_eye_aspect_ratio, extract_features
from ai.mediapipe_tracker import MultiFaceTracker

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"


@pytest.fixture
def tracker():
    return MultiFaceTracker()


def test_ear_open_vs_closed(tracker):
    """Assert that closed-eye EAR is strictly less than open-eye EAR."""
    open_img_path = FIXTURES_DIR / "face_open_eyes.png"
    closed_img_path = FIXTURES_DIR / "face_closed_eyes.png"

    assert open_img_path.exists(), f"Missing fixture: {open_img_path}"
    assert closed_img_path.exists(), f"Missing fixture: {closed_img_path}"

    tracker.reset()
    tracks_open = tracker.process_frame(cv2.imread(str(open_img_path)))
    assert len(tracks_open) == 1, f"Expected 1 face in open_eyes fixture, got {len(tracks_open)}"
    ear_open = tracks_open[0].features["ear"]

    tracker.reset()
    tracks_closed = tracker.process_frame(cv2.imread(str(closed_img_path)))
    assert len(tracks_closed) == 1, f"Expected 1 face in closed_eyes fixture, got {len(tracks_closed)}"
    ear_closed = tracks_closed[0].features["ear"]

    print(f"\n[Test EAR] Open Eye EAR: {ear_open:.4f}, Closed Eye EAR: {ear_closed:.4f}")
    assert ear_closed < ear_open, f"Expected closed EAR ({ear_closed}) < open EAR ({ear_open})"
    # Distinct separation
    assert ear_open - ear_closed >= 0.10, "Expected significant separation between open and closed eyes"


def test_multi_face_clip_tracking(tracker):
    """Pass 15 consecutive multi-face clip frames through tracker and assert:

    1. All fixture faces detected with landmark confidence >= 95%.
    2. IDs persist across frames (no dropouts).
    3. Zero ID swaps (left face track remains left face, right face track remains right face).
    """
    clip_dir = FIXTURES_DIR / "clip"
    frame_files = sorted(clip_dir.glob("frame_*.png"))
    assert len(frame_files) >= 10, f"Expected at least 10 clip frames in {clip_dir}"

    tracker.reset()
    frame_history = []

    for idx, f_path in enumerate(frame_files):
        frame = cv2.imread(str(f_path))
        tracks = tracker.process_frame(frame)
        assert len(tracks) == 2, f"Frame {idx}: Expected 2 tracked faces, got {len(tracks)}"

        # Assert landmark confidence >= 0.95
        for trk in tracks:
            assert trk.landmark_confidence >= 0.95, (
                f"Frame {idx}, Track {trk.label}: confidence {trk.landmark_confidence} < 0.95"
            )
            # Verify feature schema
            for feat_key in ["ear", "mar", "head_yaw", "head_pitch"]:
                assert feat_key in trk.features, f"Missing feature '{feat_key}' in {trk.label}"

        # Sort tracks by X position: left face, right face
        tracks_by_x = sorted(tracks, key=lambda t: t.bbox[0])
        left_track = tracks_by_x[0]
        right_track = tracks_by_x[1]

        frame_history.append({
            "frame": idx,
            "left_id": left_track.track_id,
            "left_label": left_track.label,
            "right_id": right_track.track_id,
            "right_label": right_track.label,
            "left_ear": left_track.features["ear"],
            "right_ear": right_track.features["ear"],
        })

    # Assert stable ID persistence across all frames
    initial_left_id = frame_history[0]["left_id"]
    initial_right_id = frame_history[0]["right_id"]
    assert initial_left_id != initial_right_id, "Tracks must have distinct IDs"

    print("\n[Test Tracking Stability] Frame-by-Frame ID Audit:")
    for h in frame_history:
        print(
            f" Frame {h['frame']:02d}: Left Face ID={h['left_id']} ({h['left_label']}), "
            f"Right Face ID={h['right_id']} ({h['right_label']})"
        )
        # ID Persistence and No Swap assertion
        assert h["left_id"] == initial_left_id, (
            f"ID swap or reset on left face at frame {h['frame']}! Expected {initial_left_id}, got {h['left_id']}"
        )
        assert h["right_id"] == initial_right_id, (
            f"ID swap or reset on right face at frame {h['frame']}! Expected {initial_right_id}, got {h['right_id']}"
        )

    print("\nTracking PASSED: All faces detected at >= 95% confidence, IDs persisted, zero ID swaps.")
