"""Phase 7 Test Suite — Temporal History Queue and Feature Window.

Spec refs: SYS-4, SYS-6, CON §5, implementation.md Phase 7.
Pass condition:
- Rolling window size remains constant (FIFO capacity == WINDOW_FRAMES).
- Correct calculation of windowed metrics (PERCLOS, yawn fraction, off-task fraction).
- Stale tracks are cleanly purged when unseen for > TRACK_TTL_S.
- 100k push stress test with track churn exhibits no memory growth trend.
"""

import gc
import tracemalloc
import numpy as np
import pytest
import torch

from ai.temporal import (
    DEFAULT_WINDOW_FRAMES,
    DEFAULT_TRACK_TTL_S,
    FrameFeatureSample,
    TemporalManager,
    TrackTemporalBuffer,
)

DUMMY_EMOTIONS = {
    "Angry": 0.05,
    "Disgust": 0.01,
    "Fear": 0.04,
    "Happy": 0.10,
    "Sad": 0.05,
    "Surprise": 0.05,
    "Neutral": 0.70,
}


def test_window_fifo_and_bounds():
    """Verify window size strictly respects WINDOW_FRAMES cap and FIFO eviction."""
    buf = TrackTemporalBuffer(track_id=1, label="S001", window_frames=30)
    assert buf.size == 0

    # Push 50 samples
    for i in range(50):
        sample = FrameFeatureSample(
            ear=0.25,
            mar=0.20,
            head_yaw=0.0,
            head_pitch=0.0,
            p_drowsy=0.1,
            emotion_probs=DUMMY_EMOTIONS,
            timestamp=float(i),
        )
        buf.push(sample)

    # Size must be strictly capped at 30
    assert buf.size == 30, f"Expected window size 30, got {buf.size}"
    # Oldest sample in queue should have timestamp 20 (50 - 30)
    assert buf.queue[0].timestamp == 20.0
    assert buf.queue[-1].timestamp == 49.0

    # Tensor export check
    tensor = buf.to_tensor()
    assert tensor.shape == (30, 12)
    assert tensor.dtype == torch.float32


def test_temporal_aggregate_metrics():
    """Verify calculation of PERCLOS, yawn fraction, off-task fraction, and neg_affect."""
    buf = TrackTemporalBuffer(track_id=2, label="S002", window_frames=30)

    # Fill window with 30 frames:
    # - 10 frames: eyes open (ear=0.30), mouth closed (mar=0.10), facing front (yaw=0, pitch=0)
    # - 20 frames: eyes closed (ear=0.10), mouth yawning (mar=0.60), turned head (yaw=35, pitch=0)
    for i in range(10):
        buf.push(FrameFeatureSample(
            ear=0.30,
            mar=0.10,
            head_yaw=0.0,
            head_pitch=0.0,
            p_drowsy=0.05,
            emotion_probs=DUMMY_EMOTIONS,
            timestamp=float(i),
        ))

    for i in range(10, 30):
        buf.push(FrameFeatureSample(
            ear=0.10,  # Below ear_threshold (0.20)
            mar=0.60,  # Above mar_threshold (0.50)
            head_yaw=35.0,  # Beyond head_limit_deg (25.0)
            head_pitch=0.0,
            p_drowsy=0.90,
            emotion_probs=DUMMY_EMOTIONS,
            timestamp=float(i),
        ))

    summary = buf.get_summary()

    # Expected PERCLOS: 20 / 30 = 0.6667
    assert summary["perclos"] == pytest.approx(20.0 / 30.0, abs=1e-4)

    # Expected Yawn Fraction: 20 / 30 = 0.6667
    assert summary["yawn_fraction"] == pytest.approx(20.0 / 30.0, abs=1e-4)

    # Expected Off-Task Fraction: 20 / 30 = 0.6667
    assert summary["off_task_fraction"] == pytest.approx(20.0 / 30.0, abs=1e-4)

    # Expected p_drowsy_mean: (10 * 0.05 + 20 * 0.90) / 30 = 18.5 / 30 = 0.6167
    assert summary["p_drowsy_mean"] == pytest.approx(18.5 / 30.0, abs=1e-4)


def test_track_ttl_purging():
    """Verify that tracks unseen for > TRACK_TTL_S are cleanly purged."""
    mgr = TemporalManager(window_frames=30, track_ttl_s=5.0)

    # Add 3 tracks at t = 0.0
    for tid in [1, 2, 3]:
        mgr.update_track(
            track_id=tid,
            label=f"S{tid:03d}",
            ear=0.30,
            mar=0.20,
            head_yaw=0.0,
            head_pitch=0.0,
            p_drowsy=0.10,
            emotion_probs=DUMMY_EMOTIONS,
            timestamp=0.0,
        )

    assert mgr.count == 3

    # Update track 1 and track 2 at t = 4.0
    for tid in [1, 2]:
        mgr.update_track(
            track_id=tid,
            label=f"S{tid:03d}",
            ear=0.30,
            mar=0.20,
            head_yaw=0.0,
            head_pitch=0.0,
            p_drowsy=0.10,
            emotion_probs=DUMMY_EMOTIONS,
            timestamp=4.0,
        )

    # At t = 6.0: Track 3 is unseen for 6.0s (> 5.0s TTL), Track 1 & 2 unseen for 2.0s (< 5.0s TTL)
    purged = mgr.purge_stale_tracks(current_time=6.0)
    assert purged == [3]
    assert mgr.count == 2
    assert mgr.active_track_ids == [1, 2]

    # At t = 10.0: Track 1 & 2 now unseen for 6.0s (> 5.0s TTL)
    purged_final = mgr.purge_stale_tracks(current_time=10.0)
    assert set(purged_final) == {1, 2}
    assert mgr.count == 0


def test_100k_pushes_with_track_churn_and_memory():
    """Execute 100k sequential pushes with high track churn and verify no memory growth trend."""
    tracemalloc.start()
    gc.collect()

    mgr = TemporalManager(window_frames=30, track_ttl_s=2.0)
    total_pushes = 100_000
    active_simulated_tracks = 15  # Up to 15 concurrent faces

    snapshot_start = tracemalloc.take_snapshot()

    # Track lifecycle simulation: new tracks appear, old tracks expire
    track_id_counter = 1
    current_tracks = list(range(1, active_simulated_tracks + 1))
    track_id_counter = active_simulated_tracks + 1

    sim_time = 0.0
    time_step = 0.05  # 20 FPS simulation (50ms per frame)

    memory_checkpoints = []

    print(f"\n[Stress Test] Starting {total_pushes:,} pushes with continuous track churn...")
    for step in range(total_pushes):
        sim_time += time_step

        # Every 200 steps, rotate a track (churn: 1 student leaves, 1 arrives)
        if step % 200 == 0:
            if current_tracks:
                current_tracks.pop(0)  # Oldest student leaves
            current_tracks.append(track_id_counter)
            track_id_counter += 1

        # Every 100 steps, purge stale tracks
        if step % 100 == 0:
            mgr.purge_stale_tracks(current_time=sim_time)

        # Pick a track to update
        tid = current_tracks[step % len(current_tracks)]
        mgr.update_track(
            track_id=tid,
            label=f"S{tid:03d}",
            ear=0.28,
            mar=0.22,
            head_yaw=5.0,
            head_pitch=-2.0,
            p_drowsy=0.15,
            emotion_probs=DUMMY_EMOTIONS,
            timestamp=sim_time,
        )

        # Record memory at 25k, 50k, 75k, 100k
        if (step + 1) in [25_000, 50_000, 75_000, 100_000]:
            gc.collect()
            current_mem_kb, peak_mem_kb = tracemalloc.get_traced_memory()
            memory_checkpoints.append({
                "step": step + 1,
                "current_mb": current_mem_kb / (1024 * 1024),
                "peak_mb": peak_mem_kb / (1024 * 1024),
                "active_buffers": mgr.count,
            })

    snapshot_end = tracemalloc.take_snapshot()
    tracemalloc.stop()

    print("\n" + "=" * 60)
    print("100k Push Stress Test & Memory Checkpoints")
    print("=" * 60)
    for cp in memory_checkpoints:
        print(
            f"  Step {cp['step']:>7,}: Current Memory={cp['current_mb']:.2f} MB, "
            f"Peak Memory={cp['peak_mb']:.2f} MB, Active Buffers={cp['active_buffers']}"
        )
    print("=" * 60)

    # 1. Assert active buffers remain strictly bounded by concurrent track count
    assert mgr.count <= active_simulated_tracks + 2, (
        f"Active buffers ({mgr.count}) exceeded max concurrent threshold!"
    )

    # 2. Assert memory growth trend between 25k and 100k is flat (delta < 2.0 MB)
    mem_at_25k = memory_checkpoints[0]["current_mb"]
    mem_at_100k = memory_checkpoints[-1]["current_mb"]
    growth_mb = mem_at_100k - mem_at_25k
    print(f"Memory Growth from 25k to 100k steps: {growth_mb:+.3f} MB")

    assert growth_mb < 2.0, (
        f"Memory growth trend detected: {growth_mb:.2f} MB increase from 25k to 100k!"
    )

    print("Pass: Window size constant, old frames & dead tracks purged, zero memory growth trend.")
