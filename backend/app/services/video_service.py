import os
import cv2
import time
import base64
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.frame_processor import frame_processor
from backend.app.services.database_service import database_service
from backend.app.services.inference_service import inference_service
from backend.app.services.export_service import export_service

class VideoAnalysisWorker:
    """
    Background worker that opens a video file with OpenCV, reads frames sequentially,
    runs the tri-model inference pipeline, annotates frames, saves records to DB,
    and broadcasts detection updates through WebSockets in real time.
    Implements PRD Section 6, 7, 27, 41, 42.
    """
    def __init__(self, session_id: str, video_path: str, loop: bool = False):
        self.session_id = session_id
        self.video_path = video_path
        self.loop = loop
        self.is_running = False
        self._stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.frames_read: int = 0
        self.frames_processed: int = 0
        self.latest_frame_payload: Optional[Dict[str, Any]] = None
        self.latest_annotated_jpeg: Optional[str] = None
        self.video_fps: float = 30.0

    def start(self):
        self.is_running = True
        self._stop_event.clear()
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name=f"VideoWorker-{self.session_id}")
        self.thread.start()
        logger.info(f"[VIDEO_SERVICE] Started video analysis worker for session {self.session_id} on {self.video_path}")

    def stop(self):
        self._stop_event.set()
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info(f"[VIDEO_SERVICE] Stopped video worker for {self.session_id}")

    def _run_loop(self):
        from backend.app.websocket.detection_ws import manager

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"[VIDEO_SERVICE] Failed to open video file: {self.video_path}")
            self.is_running = False
            database_service.update_session(self.session_id, status="ERROR")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps and fps > 0 and fps < 120:
            self.video_fps = fps
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        frame_interval = 1.0 / max(1.0, min(self.video_fps, 30.0))
        frame_idx = 0

        frame_processor.reset_pipeline(session_id=self.session_id)

        try:
            while not self._stop_event.is_set():
                t_frame_start = time.perf_counter()
                ret, frame = cap.read()
                if not ret:
                    if self.loop and not self._stop_event.is_set():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.info(f"[VIDEO_SERVICE] Video reached EOF: {self.video_path}")
                        break

                frame_idx += 1
                self.frames_read += 1

                # Run Tri-Model Pipeline
                payload = frame_processor.process_frame(
                    frame=frame,
                    frame_id=frame_idx,
                    camera_id=self.session_id,
                    session_id=self.session_id,
                    stream_fps=self.video_fps
                )
                self.frames_processed += 1

                # Generate Annotated Frame (PRD Section 27)
                annotated = inference_service.draw_detections(frame, payload.get("detections", []))
                _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
                b64_frame = "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")

                payload["image_base64"] = b64_frame
                payload["total_frames_in_file"] = total_video_frames
                self.latest_frame_payload = payload
                self.latest_annotated_jpeg = b64_frame

                # Broadcast to WebSocket clients (PRD Section 18)
                try:
                    asyncio.run(manager.broadcast(self.session_id, payload))
                    # Also broadcast to DR-01 / default HUD channel so existing dashboards receive updates immediately
                    asyncio.run(manager.broadcast("DR-01", payload))
                except Exception as ws_err:
                    pass

                # Rate pacing
                t_spent = time.perf_counter() - t_frame_start
                delay = frame_interval - t_spent
                if delay > 0.001:
                    time.sleep(delay)

        except Exception as e:
            logger.error(f"[VIDEO_SERVICE] Exception in video worker {self.session_id}: {e}")
        finally:
            cap.release()
            self.end_time = time.time()
            self.is_running = False

            # Compile Final Statistics (PRD Section 41 & 42)
            duration_sec = max(1.0, round(self.end_time - self.start_time, 1))
            last_counts = self.latest_frame_payload.get("session_totals", {}) if self.latest_frame_payload else {}

            final_stats = {
                "session_id": self.session_id,
                "duration_seconds": duration_sec,
                "duration_formatted": f"{int(duration_sec // 60):02d}:{int(duration_sec % 60):02d}",
                "total_frames": self.frames_read,
                "processed_frames": self.frames_processed,
                "nav_count": last_counts.get("navigation", 0),
                "fod_count": last_counts.get("fod", 0),
                "light_on_count": last_counts.get("light_on", 0),
                "light_off_count": last_counts.get("light_off", 0),
                "confirmed_faults": last_counts.get("confirmed_faults", 0),
                "avg_confidence": self.latest_frame_payload.get("average_confidence", 0.0) if self.latest_frame_payload else 0.0,
                "avg_inference_ms": self.latest_frame_payload.get("inference_ms", 0.0) if self.latest_frame_payload else 0.0,
            }

            database_service.complete_session(self.session_id, final_stats)
            try:
                export_service.export_all(self.session_id)
            except Exception as ex_exp:
                logger.warning(f"[VIDEO_SERVICE] Auto-export failed for session {self.session_id}: {ex_exp}")

            # Notify WebSocket clients that session is completed (PRD Section 41)
            completion_msg = {
                "type": "session_completed",
                "session_id": self.session_id,
                "summary": final_stats
            }
            try:
                asyncio.run(manager.broadcast(self.session_id, completion_msg))
                asyncio.run(manager.broadcast("DR-01", completion_msg))
            except Exception:
                pass

            logger.info(f"[VIDEO_SERVICE] Session {self.session_id} finalized: {final_stats}")

class VideoService:
    """
    Manages video file analysis sessions per PRD Section 6, 30.
    """
    def __init__(self):
        self.active_workers: Dict[str, VideoAnalysisWorker] = {}

    def start_session(self, source_path: str, loop: bool = False, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Starts video analysis for a video file or generated demo feed.
        """
        # If source is demo or does not exist, check fallback demo videos
        if not os.path.exists(source_path):
            candidates = [
                "data/videos/runway_demo.mp4",
                "data/videos/demo_runway.mp4",
                os.path.join(os.getcwd(), "data", "videos", "runway_demo.mp4")
            ]
            for cand in candidates:
                if os.path.exists(cand):
                    source_path = cand
                    break

        sid = database_service.create_session(source=source_path, source_type="VIDEO_FILE", session_id=session_id)
        worker = VideoAnalysisWorker(session_id=sid, video_path=source_path, loop=loop)
        self.active_workers[sid] = worker
        worker.start()

        return {
            "session_id": sid,
            "status": "RUNNING",
            "source": source_path,
            "message": f"Video analysis started for session {sid}"
        }

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        worker = self.active_workers.get(session_id)
        if worker:
            worker.stop()
            del self.active_workers[session_id]

        stats = database_service.get_session_statistics(session_id)
        return {
            "session_id": session_id,
            "status": "COMPLETED",
            "statistics": stats
        }

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        worker = self.active_workers.get(session_id)
        if worker and worker.is_running:
            return {
                "session_id": session_id,
                "status": "RUNNING",
                "frames_read": worker.frames_read,
                "frames_processed": worker.frames_processed,
                "latest": worker.latest_frame_payload
            }

        stats = database_service.get_session(session_id)
        return stats or {"session_id": session_id, "status": "NOT_FOUND"}

video_service = VideoService()
