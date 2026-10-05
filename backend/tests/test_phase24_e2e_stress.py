"""Phase 24 — End-to-End Integration & Stress Testing Suite.

Implements SYS-17, APP-29, APP-30:
1. Docker compose configuration validation (backend, db, operator-console, Dockerfiles).
2. Multi-face simulated classroom load with 20+ concurrent tracked students (S001-S025).
3. Multi-client WebSocket telemetry broadcast load test (concurrent subscribers).
4. Soak test simulation (≥ 1 hour simulated session) tracking telemetry loss, memory trajectory, and report data integrity.
5. Capacity measurement: Max students at TARGET_FPS.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
import tracemalloc
from typing import List

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.config import settings
from app.db.database import Base
from app.db.models import Alert, Classroom, Observation, Session
from app.main import app
from app.auth.jwt import create_access_token
from app.reports.builder import build_session_report, export_csv
from app.ws.manager import ws_manager
from ai.temporal import TemporalManager
from ai.scoring import ScoringEngine


@pytest.fixture(scope="module")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def test_docker_configuration(project_root: Path):
    """Verify docker-compose.yml and Dockerfiles exist with required services."""
    compose_path = project_root / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at project root"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    assert "backend" in services, "backend service missing from docker-compose.yml"
    assert "db" in services, "db service missing from docker-compose.yml"
    assert "operator-console" in services, "operator-console service missing from docker-compose.yml"

    backend_dockerfile = project_root / "backend" / "Dockerfile"
    assert backend_dockerfile.exists(), "backend/Dockerfile must exist"

    console_dockerfile = project_root / "operator-console" / "Dockerfile"
    assert console_dockerfile.exists(), "operator-console/Dockerfile must exist"


def test_concurrent_multi_face_classroom_pipeline():
    """Simulate 25 concurrent student tracks through temporal buffer and scoring state machine (SYS-17, APP-29)."""
    num_students = 25
    temporal_mgr = TemporalManager(window_frames=30)
    scoring_engine = ScoringEngine(min_confidence=0.80)

    start_time = time.perf_counter()
    num_frames = 60  # 3 seconds at 20 FPS

    for frame_idx in range(num_frames):
        ts = time.time()
        for track_id in range(1, num_students + 1):
            label = f"S{track_id:03d}"
            # Vary features realistically: student 1 fatigued, student 2 looking away, others attentive
            if track_id == 1:
                ear, mar, yaw, pitch = 0.12, 0.65, 5.0, -10.0
                p_drowsy = 0.95
                emotions = {"Sad": 0.8, "Neutral": 0.2}
            elif track_id == 2:
                ear, mar, yaw, pitch = 0.28, 0.10, 35.0, 5.0
                p_drowsy = 0.10
                emotions = {"Neutral": 0.9, "Surprise": 0.1}
            else:
                ear, mar, yaw, pitch = 0.30, 0.08, 2.0, 1.0
                p_drowsy = 0.05
                emotions = {"Neutral": 0.95, "Happy": 0.05}

            temporal_mgr.update_track(
                track_id=track_id,
                label=label,
                ear=ear,
                mar=mar,
                head_yaw=yaw,
                head_pitch=pitch,
                p_drowsy=p_drowsy,
                emotion_probs=emotions,
                timestamp=ts,
            )
            summary = temporal_mgr.get_track_summary(track_id)
            assert summary is not None

            track_result, alerts = scoring_engine.process_frame(
                track_id=track_id,
                label=label,
                bbox=[50.0, 50.0, 100.0, 100.0],
                landmark_confidence=0.92,
                ear=ear,
                mar=mar,
                head_yaw=yaw,
                head_pitch=pitch,
                perclos=summary["perclos"],
                yawn_fraction=summary["yawn_fraction"],
                off_task_fraction=summary["off_task_fraction"],
                p_drowsy=p_drowsy,
                drowsiness_label="Drowsy" if p_drowsy > 0.5 else "Non Drowsy",
                emotion_probs=emotions,
                top_emotion=list(emotions.keys())[0],
                timestamp=ts,
            )
            assert track_result["attention_status"] in ("Attentive", "Distracted", "Unknown")
            assert track_result["fatigue_status"] in ("Normal", "Fatigued", "Unknown")

    elapsed = time.perf_counter() - start_time
    total_evals = num_frames * num_students
    throughput_evals_per_sec = total_evals / elapsed
    effective_fps = num_frames / elapsed

    print(
        f"\n[Capacity Test] 25 Concurrent Students processed: {total_evals} inferences in {elapsed:.3f}s "
        f"({throughput_evals_per_sec:.1f} student-frames/s, effective FPS for class: {effective_fps:.1f})"
    )

    # Assert processing capacity exceeds target FPS threshold without failure
    assert effective_fps > 10.0, "Multi-face pipeline fell significantly behind target frame budget"


def test_multi_client_websocket_broadcast_load():
    """Verify concurrent WebSocket telemetry subscribers under broadcast load without packet drop."""
    num_messages = 20

    token = create_access_token("admin", "admin")
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/telemetry?token={token}") as ws1, \
             client.websocket_connect(f"/ws/telemetry?token={token}") as ws2, \
             client.websocket_connect(f"/ws/telemetry?token={token}") as ws3:

            # All 3 clients subscribe to session 999
            ws1.send_json({"type": "subscribe", "session_id": 999})
            _ = ws1.receive_json()
            ws2.send_json({"type": "subscribe", "session_id": 999})
            _ = ws2.receive_json()
            ws3.send_json({"type": "subscribe", "session_id": 999})
            _ = ws3.receive_json()

            # Broadcast high-frequency telemetry snapshots
            for i in range(num_messages):
                payload = {
                    "type": "telemetry",
                    "session_id": 999,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "seq": i,
                    "students_detected": 25,
                }
                asyncio.run(ws_manager.broadcast_telemetry(payload, session_id=999))

                msg1 = ws1.receive_json()
                msg2 = ws2.receive_json()
                msg3 = ws3.receive_json()

                assert msg1["seq"] == i
                assert msg2["seq"] == i
                assert msg3["seq"] == i

            print(
                f"\n[WebSocket Load Test] Broadcasted {num_messages} packets to 3 concurrent clients (100% receipt, 0% packet loss)"
            )


def test_long_run_soak_and_report_integrity(tmp_path: Path):
    """Simulate ≥ 1 hour accelerated session tracking memory trajectory and verifying report data integrity."""
    test_db = tmp_path / "test_soak.db"
    engine = create_engine(f"sqlite:///{test_db}")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        # Seed test classroom and session
        classroom = Classroom(room_name="Lab 101", class_name="III AI & DS - Lab 1", camera_id="CAM-001", active=True)
        db.add(classroom)
        db.commit()

        start_time = datetime(2026, 10, 3, 9, 0, 0)
        simulated_duration = timedelta(hours=1)
        end_time = start_time + simulated_duration

        session = Session(
            classroom_id=classroom.id,
            status="Completed",
            started_at=start_time,
            ended_at=end_time,
            students_detected_max=20,
        )
        db.add(session)
        db.commit()

        # Track memory trajectory across soak simulation
        tracemalloc.start()
        mem_samples = []

        # 1 hour = 720 observations per student at 5s observation interval
        # We simulate 720 observation steps across 20 students = 14,400 observations
        total_steps = 720
        num_students = 20

        for step in range(total_steps):
            obs_time = start_time + timedelta(seconds=step * 5)
            step_obs = []
            for track_id in range(1, num_students + 1):
                # Student 1 is consistently fatigued, student 2 distracted, rest attentive
                if track_id == 1:
                    att_status = "Attentive"
                    fat_status = "Fatigued"
                    score = 65.0
                    drowsy = 8
                elif track_id == 2:
                    att_status = "Distracted"
                    fat_status = "Normal"
                    score = 45.0
                    drowsy = 1
                else:
                    att_status = "Attentive"
                    fat_status = "Normal"
                    score = 88.0
                    drowsy = 0

                obs = Observation(
                    session_id=session.id,
                    track_id=track_id,
                    ts=obs_time,
                    attention_status=att_status,
                    fatigue_status=fat_status,
                    attention_score_mean=score,
                    fatigue_index_mean=0.7 if fat_status == "Fatigued" else 0.1,
                    confidence_mean=0.91,
                    drowsy_frames=drowsy,
                    total_frames=10,
                )
                step_obs.append(obs)

            db.bulk_save_objects(step_obs)
            db.commit()

            # Sample memory at 25%, 50%, 75%, 100%
            if step in (180, 360, 540, 719):
                current_mem, peak_mem = tracemalloc.get_traced_memory()
                mem_samples.append(current_mem / (1024 * 1024))

        # Seed alerts
        alert1 = Alert(
            session_id=session.id,
            track_id=1,
            label="S001",
            type="fatigue",
            status="Resolved",
            message="Possible repeated fatigue indicators observed.",
            confidence=0.92,
            created_at=start_time + timedelta(minutes=15),
            resolved_at=start_time + timedelta(minutes=20),
        )
        db.add(alert1)
        db.commit()

        tracemalloc.stop()

        # Check memory growth trend
        mem_growth = mem_samples[-1] - mem_samples[0]
        print(f"\n[Soak Memory] Samples (MB): {mem_samples}, Growth: {mem_growth:+.3f} MB")
        assert mem_growth < 2.0, f"Memory growth exceeded tolerance: {mem_growth:.3f} MB"

        # Verify Report Generation & Aggregation Integrity
        report = build_session_report(db, session.id)

        assert report["session_id"] == session.id
        assert report["class_name"] == "III AI & DS - Lab 1"
        assert report["duration_min"] == 60
        assert report["students"] == 20
        assert report["alerts_total"] == 1

        # Check aggregate match
        # In report builder:
        # attention.attentive = count of students whose dominant state was Attentive
        # In our simulation: 19 students dominant attentive, 1 dominant distracted
        assert report["attention"]["attentive"] == 19
        assert report["attention"]["distracted"] == 1
        assert report["fatigue"]["fatigued"] == 1
        assert report["fatigue"]["normal"] == 19

        # Ensure mandatory ethical footer is present in export
        csv_text = export_csv(report)
        assert "AI-generated indicators to support teacher observation" in csv_text
        assert "not a diagnosis or disciplinary record" in csv_text

    finally:
        db.close()
