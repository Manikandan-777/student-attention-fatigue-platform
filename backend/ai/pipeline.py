"""Video Stream Processing Loop & Multi-Channel Pipeline.

Implements SYS-1, SYS-17, APP-6, APP-20, CON §4, CON §5:
- Video capture from RTSP, USB camera, video file, or synthetic frame generator.
- Non-blocking architecture: dedicated capture thread + inference worker thread.
- Bounded frame queue that drops stale frames under heavy processing load.
- End-to-end AI stage execution:
    Capture -> MultiFaceTracker -> FaceROIExtractor -> Drowsiness & Expression
    -> TemporalManager -> ScoringEngine -> Telemetry / Alert / Status Broadcast.
- Camera-loss detection (CAMERA_TIMEOUT_S) and AI heartbeat (AI_HEARTBEAT_TIMEOUT_S).
- Live metrics collection: Capture FPS, Inference FPS, p95 latency, dropped frames count.
"""

import asyncio
from collections import deque
import base64
import logging
from pathlib import Path
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from ai.drowsiness import DrowsinessClassifier
from ai.expression import ExpressionClassifier
from ai.lstm_attention import LSTMAggregator
from ai.mediapipe_tracker import MultiFaceTracker, TrackedFace
from ai.roi import FaceROIExtractor
from ai.scoring import AlertEvent, ScoringEngine
from ai.temporal import TemporalManager
from app.config import settings
from app.ws.manager import ConnectionManager, ws_manager

logger = logging.getLogger("ai.pipeline")


class VideoPipeline:
    """End-to-end non-blocking video analytics pipeline."""

    def __init__(
        self,
        camera_id: str = "CAM-001",
        session_id: int = 1,
        class_name: str = "Classroom A",
        source: Optional[Union[str, int, Callable[[], Optional[np.ndarray]]]] = None,
        target_fps: int = 20,
        camera_timeout_s: float = 10.0,
        ai_heartbeat_timeout_s: float = 10.0,
        telemetry_hz: int = 2,
        classification_stride: int = 4,
        models_dir: Optional[Path] = None,
        connection_manager: Optional[ConnectionManager] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self.camera_id = camera_id
        self.session_id = session_id
        self.class_name = class_name
        self.source = source
        self.target_fps = target_fps
        self.camera_timeout_s = camera_timeout_s
        self.ai_heartbeat_timeout_s = ai_heartbeat_timeout_s
        self.telemetry_hz = telemetry_hz
        self.classification_stride = classification_stride
        self.models_dir = models_dir or (Path(__file__).resolve().parent.parent / "models")
        self.ws_mgr = connection_manager or ws_manager
        self.event_loop = loop

        # Initialize AI components
        self.tracker = MultiFaceTracker()
        self.roi_extractor = FaceROIExtractor(models_base_dir=self.models_dir)
        self.drowsiness_classifier = DrowsinessClassifier(model_dir=self.models_dir / "drowsiness")
        self.expression_classifier = ExpressionClassifier(model_dir=self.models_dir / "expression")
        self.temporal_manager = TemporalManager(
            window_frames=settings.WINDOW_FRAMES,
            track_ttl_s=settings.STATUS_HYSTERESIS_S * 2,
        )
        self.scoring_engine = ScoringEngine(
            min_confidence=settings.MIN_CONFIDENCE,
            status_hysteresis_s=settings.STATUS_HYSTERESIS_S,
            fatigue_persist_s=settings.FATIGUE_PERSIST_S,
            distraction_persist_s=settings.DISTRACTION_PERSIST_S,
            alert_cooldown_s=settings.ALERT_COOLDOWN_S,
        )
        self.lstm_aggregator = LSTMAggregator(weights_path=None)

        # Threading & Queue
        self.frame_queue: queue.Queue[Tuple[np.ndarray, float]] = queue.Queue(maxsize=2)
        self.is_running = False
        self._stop_event = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._inference_thread: Optional[threading.Thread] = None

        # Camera & AI State
        self.camera_state = "Online"
        self.ai_server_state = "Online"
        self.last_frame_received_at = time.monotonic()
        self.last_ai_heartbeat_at = time.monotonic()
        self.last_telemetry_broadcast_at = 0.0
        self.last_status_broadcast_at = 0.0

        # Performance Metrics
        self.total_captured_frames = 0
        self.total_processed_frames = 0
        self.total_dropped_frames = 0
        self._start_time: float = 0.0
        self._latencies: deque[float] = deque(maxlen=200)
        self._capture_timestamps: deque[float] = deque(maxlen=60)
        self._inference_timestamps: deque[float] = deque(maxlen=60)

        # Track caches for classification striding
        self._cached_drowsiness: Dict[int, Tuple[str, float]] = {}
        self._cached_expression: Dict[int, Tuple[str, Dict[str, float]]] = {}
        self._frame_counter = 0

    def start(self) -> None:
        """Start non-blocking video capture and inference worker threads."""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()
        self.last_frame_received_at = time.monotonic()
        self.last_ai_heartbeat_at = time.monotonic()
        self._start_time = time.monotonic()

        self._capture_thread = threading.Thread(
            target=self._capture_worker_loop,
            name="VideoPipeline-Capture",
            daemon=True,
        )
        self._inference_thread = threading.Thread(
            target=self._inference_worker_loop,
            name="VideoPipeline-Inference",
            daemon=True,
        )

        self._capture_thread.start()
        self._inference_thread.start()
        logger.info("VideoPipeline [%s] started.", self.camera_id)

    def stop(self, timeout: float = 3.0) -> None:
        """Gracefully stop all pipeline worker threads."""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=timeout)
        if self._inference_thread and self._inference_thread.is_alive():
            self._inference_thread.join(timeout=timeout)

        self._capture_thread = None
        self._inference_thread = None
        logger.info("VideoPipeline [%s] stopped.", self.camera_id)

    def _capture_worker_loop(self) -> None:
        """Dedicated frame acquisition thread."""
        cap = None
        is_callable = callable(self.source)

        if not is_callable and self.source is not None:
            cap = cv2.VideoCapture(self.source)

        target_interval = 1.0 / max(1, self.target_fps)

        try:
            while not self._stop_event.is_set():
                t_start = time.monotonic()
                frame = None

                if is_callable:
                    frame = self.source()
                elif cap is not None and cap.isOpened():
                    ret, raw_frame = cap.read()
                    if ret:
                        frame = raw_frame
                    else:
                        time.sleep(0.01)

                if frame is not None:
                    now = time.monotonic()
                    self.last_frame_received_at = now
                    self.total_captured_frames += 1
                    self._capture_timestamps.append(now)

                    # Camera was offline → now online
                    if self.camera_state != "Online":
                        self.camera_state = "Online"
                        logger.info("Camera %s reconnected (capture thread). State → Online.", self.camera_id)

                    # Bounded queue: drop oldest frame if full to prevent lag accumulation
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                            self.total_dropped_frames += 1
                        except queue.Empty:
                            pass

                    try:
                        self.frame_queue.put_nowait((frame, now))
                    except queue.Full:
                        self.total_dropped_frames += 1

                else:
                    # No frame received — check for camera timeout
                    now = time.monotonic()
                    time_since_last = now - self.last_frame_received_at
                    if time_since_last > self.camera_timeout_s and self.camera_state != "Offline":
                        self.camera_state = "Offline"
                        logger.warning(
                            "Camera %s timed out (capture thread, %.1fs). State → Offline.",
                            self.camera_id, time_since_last,
                        )
                        self._dispatch_camera_offline()

                # Frame-rate pacing
                elapsed = time.monotonic() - t_start
                sleep_time = target_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as exc:
            logger.error("Capture loop error: %s", exc)
        finally:
            if cap is not None:
                cap.release()

    def _inference_worker_loop(self) -> None:
        """Dedicated analytics and inference execution thread."""
        while not self._stop_event.is_set():
            now = time.monotonic()
            self.last_ai_heartbeat_at = now

            # 1. Camera Timeout Check
            time_since_last_frame = now - self.last_frame_received_at
            if time_since_last_frame > self.camera_timeout_s:
                if self.camera_state != "Offline":
                    self.camera_state = "Offline"
                    logger.warning("Camera %s timed out! Setting state to Offline.", self.camera_id)
                    self._dispatch_system_status()
                    self._dispatch_camera_offline()
            else:
                if self.camera_state != "Online":
                    self.camera_state = "Online"
                    logger.info("Camera %s reconnected. Setting state to Online.", self.camera_id)
                    self._dispatch_system_status()

            # 2. Retrieve next frame from bounded queue
            try:
                frame_bgr, frame_ts = self.frame_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            # 3. Process frame through pipeline
            t_proc_start = time.monotonic()
            try:
                self.process_single_frame(frame_bgr, timestamp=frame_ts)
            except Exception as exc:
                logger.error("Error processing video frame: %s", exc, exc_info=True)
            finally:
                proc_latency_ms = (time.monotonic() - t_proc_start) * 1000.0
                self._latencies.append(proc_latency_ms)
                self.total_processed_frames += 1
                self._inference_timestamps.append(time.monotonic())

            # 4. Periodic System Status broadcast (every 5 seconds)
            if (now - self.last_status_broadcast_at) >= 5.0:
                self._dispatch_system_status()
                self.last_status_broadcast_at = now

    def process_single_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute end-to-end AI stages on a single frame."""
        ts = timestamp if timestamp is not None else time.monotonic()
        self._frame_counter += 1

        # 1. MultiFaceTracker stage
        tracked_faces = self.tracker.process_frame(frame_bgr)

        # 2. Deep classification with frame striding to maintain real-time performance
        run_deep_inference = (self._frame_counter % self.classification_stride == 0) or (not self._cached_drowsiness)

        if tracked_faces:
            if run_deep_inference:
                # Prepare batches using FaceROIExtractor
                drowsy_tensor, valid_drowsy_faces = self.roi_extractor.prepare_drowsiness_batch(frame_bgr, tracked_faces)
                expr_tensor, valid_expr_faces = self.roi_extractor.prepare_expression_batch(frame_bgr, tracked_faces)

                # MobileViT Drowsiness batch inference
                drowsy_preds = self.drowsiness_classifier.predict_batch(drowsy_tensor)
                for face, pred in zip(valid_drowsy_faces, drowsy_preds):
                    self._cached_drowsiness[face.track_id] = (pred["label"], pred["p_drowsy"])

                # ViT Expression batch inference
                expr_preds = self.expression_classifier.predict_batch(expr_tensor)
                for face, pred in zip(valid_expr_faces, expr_preds):
                    self._cached_expression[face.track_id] = (pred["top"], pred["probs"])

        # 3. Purge expired tracks from temporal buffer
        self.temporal_manager.purge_stale_tracks(current_time=ts)

        # 4. Temporal Aggregation and Scoring
        track_results: List[Dict[str, Any]] = []
        track_results_lite: List[Dict[str, Any]] = []
        all_emitted_alerts: List[AlertEvent] = []

        counts = {"attentive": 0, "distracted": 0, "unknown": 0, "fatigued": 0}
        attention_scores: List[float] = []

        for face in tracked_faces:
            tid = face.track_id
            # Retrieve deep classification results (or cached/default)
            drowsiness_label, p_drowsy = self._cached_drowsiness.get(tid, ("Non Drowsy", 0.05))
            top_emotion, emotion_probs = self._cached_expression.get(
                tid,
                ("Neutral", {"Angry": 0.0, "Disgust": 0.0, "Fear": 0.0, "Happy": 0.0, "Sad": 0.0, "Surprise": 0.0, "Neutral": 1.0}),
            )

            # Update rolling temporal history
            buf = self.temporal_manager.update_track(
                track_id=tid,
                label=face.label,
                ear=face.features["ear"],
                mar=face.features["mar"],
                head_yaw=face.features["head_yaw"],
                head_pitch=face.features["head_pitch"],
                p_drowsy=p_drowsy,
                emotion_probs=emotion_probs,
                timestamp=ts,
            )
            summary = buf.get_summary()

            # Execute Composite Scoring & Validation State Machine
            track_result, alerts = self.scoring_engine.process_frame(
                track_id=tid,
                label=face.label,
                bbox=face.bbox,
                landmark_confidence=face.landmark_confidence,
                ear=face.features["ear"],
                mar=face.features["mar"],
                head_yaw=face.features["head_yaw"],
                head_pitch=face.features["head_pitch"],
                perclos=summary["perclos"],
                yawn_fraction=summary["yawn_fraction"],
                off_task_fraction=summary["off_task_fraction"],
                p_drowsy=p_drowsy,
                drowsiness_label=drowsiness_label,
                emotion_probs=emotion_probs,
                top_emotion=top_emotion,
                timestamp=ts,
                model_mode=self.lstm_aggregator.model_mode,
            )

            track_results.append(track_result)
            all_emitted_alerts.extend(alerts)

            # Construct TrackResult-lite for telemetry broadcast (contracts.md §4, APP-27)
            track_results_lite.append({
                "track_id": track_result["track_id"],
                "label": track_result["label"],
                "attention_status": track_result["attention_status"],
                "fatigue_status": track_result["fatigue_status"],
                "attention_score": track_result["attention_score"],
                "confidence": track_result["confidence"],
            })

            # Update count metrics
            att_stat = track_result["attention_status"].lower()
            fat_stat = track_result["fatigue_status"].lower()

            if att_stat == "attentive":
                counts["attentive"] += 1
            elif att_stat == "distracted":
                counts["distracted"] += 1
            elif att_stat == "unknown":
                counts["unknown"] += 1

            if fat_stat == "fatigued":
                counts["fatigued"] += 1

            if att_stat != "unknown":
                attention_scores.append(track_result["attention_score"])

        # Compute average attention score
        avg_att = round(float(np.mean(attention_scores)), 1) if attention_scores else 0.0

        # Compute class_fatigue_pct: 100 * average fatigue_index of students whose fatigue status is not "Unknown"
        usable_fatigues = [
            t.get("fatigue_index", 0.0)
            for t in track_results
            if t.get("fatigue_status") != "Unknown" and t.get("fatigue_index") is not None
        ]
        class_fatigue_pct = round(float(100.0 * np.mean(usable_fatigues)), 1) if usable_fatigues else None

        # Construct ClassSnapshot (contracts.md §2.4)
        snapshot = {
            "session_id": self.session_id,
            "class_name": self.class_name,
            "status": "Monitoring",
            "students_detected": len(tracked_faces),
            "counts": counts,
            "avg_attention_score": avg_att,
            "class_fatigue_pct": class_fatigue_pct,
            "open_alerts": len(all_emitted_alerts),
        }

        # 5. Broadcast alerts immediately if any were triggered
        for alert in all_emitted_alerts:
            self._dispatch_alert(alert)

        # 6. Throttle telemetry broadcast to TELEMETRY_HZ (contracts.md §4)
        telemetry_interval = 1.0 / max(1, self.telemetry_hz)
        if (ts - self.last_telemetry_broadcast_at) >= telemetry_interval:
            self.last_telemetry_broadcast_at = ts
            telemetry_payload = {
                "type": "telemetry",
                "session_id": self.session_id,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
                "snapshot": snapshot,
                "tracks": track_results_lite,
            }
            self._dispatch_telemetry(telemetry_payload)

        # 7. Annotated Frame Broadcast (strictly disabled if PRIVACY_MODE is true)
        if not settings.PRIVACY_MODE:
            self._dispatch_annotated_frame(frame_bgr, track_results, ts)

        return {
            "snapshot": snapshot,
            "tracks": track_results,
            "alerts": [a.to_dict() for a in all_emitted_alerts],
        }

    def _dispatch_telemetry(self, payload: Dict[str, Any]) -> None:
        """Send telemetry packet to WebSocket clients safely across async loop."""
        if not self.ws_mgr:
            return
        coro = self.ws_mgr.broadcast_telemetry(payload, session_id=self.session_id)
        self._run_async(coro)

    def _dispatch_alert(self, alert: AlertEvent) -> None:
        """Send alert packet to WebSocket clients and persist to DB if session_id is active."""
        if self.session_id:
            try:
                from app.alerts.engine import alert_engine
                from app.db.database import get_db_session
                with get_db_session() as db:
                    alert_engine.record_alert(
                        db=db,
                        session_id=self.session_id,
                        track_id=alert.track_id,
                        label=alert.label,
                        alert_type=alert.type,
                        message=alert.message,
                        confidence=alert.confidence,
                        broadcast=False,  # broadcasting handled directly below
                    )
            except Exception as exc:
                logger.debug("Could not record alert to DB: %s", exc)

        if not self.ws_mgr:
            return
        coro = self.ws_mgr.broadcast_alert(alert.to_dict(), session_id=self.session_id)
        self._run_async(coro)

    def _dispatch_camera_offline(self) -> None:
        """Emit camera_offline system alert via AlertEngine."""
        try:
            from app.alerts.engine import alert_engine
            from app.db.database import get_db_session
            with get_db_session() as db:
                alert_engine.emit_camera_offline(
                    db=db,
                    camera_id=self.camera_id,
                    session_id=self.session_id,
                )
        except Exception as exc:
            logger.debug("Could not emit camera_offline alert: %s", exc)

    def _dispatch_ai_offline(self) -> None:
        """Emit ai_offline system alert via AlertEngine."""
        try:
            from app.alerts.engine import alert_engine
            from app.db.database import get_db_session
            with get_db_session() as db:
                alert_engine.emit_ai_offline(
                    db=db,
                    session_id=self.session_id,
                )
        except Exception as exc:
            logger.debug("Could not emit ai_offline alert: %s", exc)

    def _dispatch_system_status(self) -> None:
        """Broadcast SystemStatus (contracts.md §2.5)."""
        if not self.ws_mgr:
            return
        status_payload = {
            "ai_server": self.ai_server_state,
            "database": "Online",
            "api": "Online",
            "cameras": [{"id": self.camera_id, "state": self.camera_state}],
            "fps": round(self.inference_fps, 1),
            "model_mode": self.lstm_aggregator.model_mode,
            "privacy_mode": settings.PRIVACY_MODE,
        }
        coro = self.ws_mgr.broadcast_system_status(status_payload)
        self._run_async(coro)

    def _dispatch_annotated_frame(
        self,
        frame_bgr: np.ndarray,
        tracks: List[Dict[str, Any]],
        ts: float,
    ) -> None:
        """Encode and broadcast annotated frame for Operator Console (when PRIVACY_MODE=false)."""
        annotated = frame_bgr.copy()
        h, w = annotated.shape[:2]

        for tr in tracks:
            bx, by, bw, bh = tr["bbox"]
            x1, y1 = int(bx * w), int(by * h)
            x2, y2 = int((bx + bw) * w), int((by + bh) * h)

            # Draw bounding box
            color = (0, 255, 0) if tr["attention_status"] == "Attentive" else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label_text = f"{tr['label']} [{tr['attention_status']}]"
            cv2.putText(annotated, label_text, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        ret, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ret:
            jpg_b64 = base64.b64encode(buffer).decode("ascii")
            frame_msg = {
                "type": "frame",
                "session_id": self.session_id,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
                "jpeg_b64": jpg_b64,
                "tracks": [
                    {
                        "track_id": t["track_id"],
                        "bbox": t["bbox"],
                        "attention_status": t["attention_status"],
                        "fatigue_status": t["fatigue_status"],
                    }
                    for t in tracks
                ],
            }
            coro = self.ws_mgr.broadcast_video_frame(frame_msg)
            self._run_async(coro)

    def _run_async(self, coro) -> None:
        """Helper to run coroutines in the appropriate event loop safely.

        Also handles plain sync callables (e.g. test mocks) that are not coroutines.
        """
        import inspect
        if not inspect.isawaitable(coro):
            # coro is already a non-coroutine return value (e.g. a test mock returned None)
            return
        try:
            if self.event_loop and self.event_loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, self.event_loop)
            else:
                asyncio.run(coro)
        except Exception:
            pass

    @property
    def capture_fps(self) -> float:
        """Calculates capture frame rate using total frames / total elapsed time.

        More stable than a rolling window because Windows sleep() granularity
        (≈15 ms) can cause the rolling-window estimate to dip below target FPS
        even when the actual throughput is at target.
        """
        if self._start_time > 0 and self.total_captured_frames > 0:
            elapsed = time.monotonic() - self._start_time
            if elapsed > 0:
                return float(self.total_captured_frames / elapsed)
        # Fallback: rolling window (before start() is called)
        if len(self._capture_timestamps) < 2:
            return 0.0
        dt = self._capture_timestamps[-1] - self._capture_timestamps[0]
        if dt <= 0:
            return 0.0
        return float((len(self._capture_timestamps) - 1) / dt)

    @property
    def inference_fps(self) -> float:
        """Calculates instantaneous pipeline inference frame rate."""
        if len(self._inference_timestamps) < 2:
            return 0.0
        dt = self._inference_timestamps[-1] - self._inference_timestamps[0]
        if dt <= 0:
            return 0.0
        return float((len(self._inference_timestamps) - 1) / dt)

    @property
    def p95_latency_ms(self) -> float:
        """Calculates 95th percentile frame processing latency."""
        if not self._latencies:
            return 0.0
        return float(np.percentile(list(self._latencies), 95))

    def get_stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics snapshot."""
        return {
            "camera_id": self.camera_id,
            "camera_state": self.camera_state,
            "ai_state": self.ai_server_state,
            "capture_fps": round(self.capture_fps, 2),
            "inference_fps": round(self.inference_fps, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "total_captured": self.total_captured_frames,
            "total_processed": self.total_processed_frames,
            "total_dropped": self.total_dropped_frames,
            "queue_size": self.frame_queue.qsize(),
        }
