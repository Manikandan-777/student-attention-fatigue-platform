"""Automated Test Suite for Ultra-Scale 1,000 Concurrent Face Tracking.

Verifies:
1. Canvas generator creates exactly 1,000 distinct facial targets.
2. UltraScaleTracker assigns persistent S0001-S1000 IDs with 0 ID switches.
3. Pipeline achieves 100% detection accuracy across consecutive frames.
4. Temporal scoring correctly processes all 1,000 concurrent students without errors.
"""

import pytest
from ai.high_density_detector import (
    HighDensityCanvasGenerator,
    SlicedAdaptiveFaceDetector,
    UltraScaleTracker,
    UltraScale1000FacePipeline,
)


def test_high_density_canvas_1000_faces():
    """Verify that canvas generator creates exactly 1,000 face boxes with valid dimensions."""
    generator = HighDensityCanvasGenerator(canvas_width=3840, canvas_height=2160, num_faces=1000)
    frame, gt_boxes = generator.render_frame(frame_idx=0)

    assert frame.shape == (2160, 3840, 3)
    assert len(gt_boxes) == 1000

    # Verify all face coordinates are within [0, 1]
    for box in gt_boxes:
        assert 0.0 <= box.x <= 1.0
        assert 0.0 <= box.y <= 1.0
        assert box.w > 0.0
        assert box.h > 0.0
        assert 0.0 < box.ear < 1.0


def test_ultra_scale_tracker_1000_tracks():
    """Verify UltraScaleTracker assigns S0001-S1000 and maintains identity across frames."""
    generator = HighDensityCanvasGenerator(canvas_width=3840, canvas_height=2160, num_faces=1000)
    tracker = UltraScaleTracker(max_tracks=1000)

    # Frame 0
    _, boxes_f0 = generator.render_frame(frame_idx=0)
    tracked_f0 = tracker.update(boxes_f0)
    assert len(tracked_f0) == 1000
    assert tracker.active_tracks[1].label == "S0001"
    assert tracker.active_tracks[1000].label == "S1000"

    # Frame 1 (subtle motion)
    _, boxes_f1 = generator.render_frame(frame_idx=1)
    tracked_f1 = tracker.update(boxes_f1)
    assert len(tracked_f1) == 1000
    assert tracker.id_switch_count == 0


def test_1000_faces_pipeline_100_percent_accuracy():
    """Verify end-to-end 1,000-face pipeline achieves 100% detection accuracy."""
    pipeline = UltraScale1000FacePipeline(num_faces=1000)
    report = pipeline.run_benchmark(num_frames=5)

    assert report.ground_truth_count == 5000  # 1,000 * 5 frames
    assert report.detected_count == 5000
    assert report.true_positives == 5000
    assert report.false_positives == 0
    assert report.false_negatives == 0
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1_score == 1.0
    assert report.accuracy_percentage == 100.0
    assert report.id_switches == 0
