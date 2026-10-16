import os
import time
import json
import asyncio
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set

import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.database import SessionLocal
from backend.app.db.models import AnalysisJob, AnalysisFrame, Detection, RunwayFaultRecord
from backend.app.services.navigation_service import navigation_service
from backend.app.services.fod_service import fod_service
from backend.app.services.runway_light_service import runway_light_service
from backend.app.services.tracking_service import ObjectTracker
from backend.app.services.database_service import database_service
from backend.app.services.export_service import export_service
from backend.app.services.frame_processor import frame_processor
from backend.app.services.model_verifier import model_verifier
from backend.app.services.debris_coordinate_service import debris_coordinate_service
from backend.app.services.drone_service import drone_service

PROCESSED_DIR = Path(os.getcwd()) / "data" / "processed"
RESULTS_DIR = Path(os.getcwd()) / "data" / "results"
EXPORTS_DIR = Path(os.getcwd()) / "data" / "exports"

for d in [PROCESSED_DIR, RESULTS_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class AnalysisWorker:
    """
    Dedicated Background Analysis Worker (PRD Section 3, 4, 6, 8, 11, 13, 17, 20).
    Enforces strict model isolation:
    - NAVIGATION: navigation_best.pt ONLY
    - FOD: FOD_Karhtikeyan.pt ONLY
    - RUNWAY_LIGHT: runway_light_best.pt ONLY (scan-window, row detection, ON/OFF, tracking, faults)
    Computes real-time dynamic ETA, supports Pause/Resume/Cancel, persists results to drone_nav.db,
    and generates analyzed MP4 video and model-specific reports.
    """
    def __init__(
        self,
        job_id: str,
        file_path: str,
        analysis_type: str = "NAVIGATION",
        media_type: str = "VIDEO",
        analyze_every_frame: bool = True,
        ws_manager: Optional[Any] = None,
    ):
        self.job_id = job_id
        self.file_path = file_path
        self.analysis_type = (analysis_type or "NAVIGATION").upper()
        self.media_type = media_type
        self.analyze_every_frame = analyze_every_frame
        self.ws_manager = ws_manager

        self.is_running = False
        self.is_paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Unpaused initially
        self._stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

        self.total_frames: int = 0
        self.processed_frames: int = 0
        self.video_fps: float = 30.0
        self.processing_fps: float = 0.0
        self.start_time: float = 0.0
        self.elapsed_seconds: float = 0.0
        self.remaining_seconds: float = 0.0
        self.estimated_finish_time: str = ""

        # Detections and Unique Object Counters
        self.nav_count: int = 0
        self.fod_count: int = 0
        self.light_on_count: int = 0
        self.light_off_count: int = 0
        self.confirmed_faults: int = 0
        self.unknown_light_count: int = 0
        self.total_lights_count: int = 0
        self.rows_detected: int = 0
        self.row_results: List[Dict[str, Any]] = []
        self.runway_matrix: List[Dict[str, Any]] = []
        self.runway_faults: List[Dict[str, Any]] = []

        self.unique_nav: Set[int] = set()
        self.unique_fod: Set[int] = set()
        self.unique_light_on: Set[int] = set()
        self.unique_light_off: Set[int] = set()
        self.fault_candidate_counts: Dict[int, int] = {}
        self.confirmed_fault_ids: Set[int] = set()
        self.recent_detections: List[Dict[str, Any]] = []

        # Granular detection counters & speed tracking
        self.total_frame_detections: int = 0
        self.speed_ratio: float = 0.0
        self.class_counts: Dict[str, int] = {}
        self.detection_buffer: List[Any] = []

        # Tracker instance isolated per worker
        self.tracker = ObjectTracker()

        # Model provenance metadata
        self.model_info = model_verifier.verify_model(self.analysis_type)

    def start(self):
        """Starts background worker thread."""
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._pause_event.set()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"[ANALYSIS_WORKER] Started {self.analysis_type} job {self.job_id} for file {self.file_path}")

    def pause(self):
        """Pauses processing."""
        if not self.is_running or self.is_paused:
            return
        self.is_paused = True
        self._pause_event.clear()
        self._update_db_status("PAUSED")
        self._broadcast_progress(status="PAUSED")
        logger.info(f"[ANALYSIS_WORKER] Paused job {self.job_id} at frame {self.processed_frames}")

    def resume(self):
        """Resumes processing."""
        if not self.is_running or not self.is_paused:
            return
        self.is_paused = False
        self._pause_event.set()
        self._update_db_status("ANALYZING")
        self._broadcast_progress(status="ANALYZING")
        logger.info(f"[ANALYSIS_WORKER] Resumed job {self.job_id} at frame {self.processed_frames}")

    def cancel(self):
        """Cancels processing cleanly."""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if waiting on pause
        self.is_running = False
        self.is_paused = False
        self._update_db_status("CANCELLED")
        self._broadcast_progress(status="CANCELLED")
        logger.info(f"[ANALYSIS_WORKER] Cancelled job {self.job_id}")

    def _update_db_status(self, status: str, error: Optional[str] = None, outcome_status: Optional[str] = None):
        try:
            with SessionLocal() as db:
                job = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
                if job:
                    job.status = status
                    job.outcome_status = outcome_status or status
                    if error:
                        job.error_message = error
                    db.commit()
        except Exception as e:
            logger.error(f"[ANALYSIS_WORKER] Failed to update DB status: {e}")

    def _broadcast_progress(self, status: str = "ANALYZING", outcome_status: Optional[str] = None):
        if not self.ws_manager:
            return

        if outcome_status is None:
            if status == "COMPLETED":
                outcome_status = "COMPLETED_WITH_DETECTIONS" if self.total_frame_detections > 0 else "COMPLETED_NO_DETECTIONS"
            else:
                outcome_status = status

        progress_pct = round((self.processed_frames / max(1, self.total_frames)) * 100.0, 2)
        disp_nav = max(len(self.unique_nav), self.nav_count)
        disp_fod = max(len(self.unique_fod), self.fod_count)
        disp_lon = self.light_on_count if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY") else max(len(self.unique_light_on), self.light_on_count)
        disp_loff = self.light_off_count if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY") else max(len(self.unique_light_off), self.light_off_count)

        payload = {
            "type": "analysis_update",
            "event": "analysis_progress",
            "job_id": self.job_id,
            "id": self.job_id,
            "analysis_type": self.analysis_type,
            "status": status,
            "outcome_status": outcome_status,
            "processed_frames": self.processed_frames,
            "frames_processed": self.processed_frames,
            "total_frames": self.total_frames,
            "frames_total": self.total_frames,
            "progress": progress_pct,
            "processing_fps": round(self.processing_fps, 2),
            "fps": round(self.processing_fps, 2),
            "video_fps": round(self.video_fps, 2),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "elapsed_time": round(self.elapsed_seconds, 1),
            "remaining_seconds": round(self.remaining_seconds, 1),
            "eta_seconds": round(self.remaining_seconds, 1),
            "estimated_finish_time": self.estimated_finish_time,
            "nav_count": disp_nav if self.analysis_type in ("NAVIGATION", "ALL") else 0,
            "navigation_count": disp_nav if self.analysis_type in ("NAVIGATION", "ALL") else 0,
            "fod_count": disp_fod if self.analysis_type in ("FOD", "FOD_DEBRIS", "ALL") else 0,
            "unique_fod_count": len(self.unique_fod) if self.analysis_type in ("FOD", "FOD_DEBRIS", "ALL") else 0,
            "unique_nav_count": len(self.unique_nav) if self.analysis_type in ("NAVIGATION", "ALL") else 0,
            "total_detections": self.total_frame_detections,
            "total_frame_detections": self.total_frame_detections,
            "speed_ratio": round(self.speed_ratio, 2),
            "class_counts": self.class_counts,
            "total_lights": self.total_lights_count if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY") else 0,
            "light_on_count": disp_lon if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
            "light_off_count": disp_loff if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
            "confirmed_faults": self.confirmed_faults if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
            "unknown_light_count": self.unknown_light_count if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
            "rows_detected": self.rows_detected if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
            "row_results": self.row_results if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else [],
            "matrix": self.runway_matrix if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY") else [],
            "faults": self.runway_faults if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY") else [],
            "performance": {
                "fps": round(self.processing_fps, 2),
                "speed_ratio": round(self.speed_ratio, 2),
                "inference_ms": round((self.elapsed_seconds / max(1, self.processed_frames)) * 1000.0, 1),
            },
            "recent_detections": self.recent_detections[-10:],
        }

        # Model-isolated counts payload
        if self.analysis_type in ("NAVIGATION", "ALL"):
            payload["counts"] = {"navigation": disp_nav}
        elif self.analysis_type in ("FOD", "FOD_DEBRIS"):
            payload["counts"] = {"fod": disp_fod}
        elif self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
            payload["counts"] = {
                "total_lights": self.total_lights_count,
                "light_on": disp_lon,
                "light_off": disp_loff,
                "confirmed_faults": self.confirmed_faults,
                "unknown": self.unknown_light_count,
                "rows": self.rows_detected,
                "columns": max((s.get("column_id", 0) for s in self.runway_matrix), default=0),
            }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.ws_manager.broadcast(self.job_id, payload), loop)
            else:
                loop.run_until_complete(self.ws_manager.broadcast(self.job_id, payload))
        except Exception:
            pass

    def _draw_annotations(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """Renders bounding boxes and labels for the active model."""
        if frame is None or frame.size == 0:
            return frame
        out = frame.copy()
        h, w = out.shape[:2]

        for d in detections:
            bbox = d.get("bbox") or [0, 0, 0, 0]
            if isinstance(bbox, dict):
                x1, y1, x2, y2 = int(bbox.get("x1", 0)), int(bbox.get("y1", 0)), int(bbox.get("x2", 0)), int(bbox.get("y2", 0))
            elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                x1, y1, x2, y2 = [int(round(v)) for v in bbox[:4]]
            else:
                continue

            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w - 1, x2))
            y2 = max(0, min(h - 1, y2))
            if x2 <= x1 or y2 <= y1:
                continue

            cls_name = str(d.get("class_name", "OBJECT")).upper()
            conf = float(d.get("confidence", 0.0))
            tid = d.get("track_id")

            # User requirement: Detected objects highlighted with clear red bounding boxes
            color = (0, 0, 255)  # Bright Red in BGR
            if self.analysis_type in ("FOD", "FOD_DEBRIS"):
                label_txt = f"FOD {int(conf * 100)}%"
            else:
                label_txt = f"{cls_name} {int(conf * 100)}%"

            if tid is not None:
                label_txt += f" #{tid}"

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
            (tw, th), _ = cv2.getTextSize(label_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            by1 = max(0, y1 - th - 6)
            cv2.rectangle(out, (x1, by1), (x1 + tw + 6, y1), color, -1)
            cv2.putText(out, label_txt, (x1 + 3, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return out

    def _update_runway_stats(self, detections: List[Dict[str, Any]], frame_idx: int):
        """Updates unique runway lights, ON/OFF tracking, and row-by-row structure from grid tracker."""
        stats = runway_light_service.get_summary_stats()
        self.total_lights_count = stats.get("total_lights", 0)
        self.light_on_count = stats.get("lights_on", 0)
        self.light_off_count = stats.get("lights_off", 0)
        self.unknown_light_count = stats.get("lights_unknown", 0)
        self.confirmed_faults = stats.get("confirmed_faults", 0)
        self.rows_detected = stats.get("total_rows", 0)
        self.row_results = stats.get("row_results", [])
        self.runway_matrix = stats.get("matrix", [])
        self.runway_faults = stats.get("faults", [])

        for d in detections:
            tid = d.get("track_id")
            if tid is not None:
                state = str(d.get("slot_status", d.get("state", ""))).upper()
                if "ON" in state:
                    self.unique_light_on.add(tid)
                elif "OFF" in state:
                    self.unique_light_off.add(tid)

    def _run(self):
        self.start_time = time.time()
        cap = cv2.VideoCapture(self.file_path)
        if not cap.isOpened():
            err = f"Could not open video file: {self.file_path}"
            logger.error(f"[ANALYSIS_WORKER] {err}")
            self._update_db_status("FAILED", error=err)
            self._broadcast_progress(status="FAILED")
            self.is_running = False
            return

        # Inspect video parameters
        self.video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = self.total_frames / max(1.0, self.video_fps)

        logger.info(f"[ANALYSIS_WORKER] {self.analysis_type} pipeline initialized: {self.total_frames} frames @ {self.video_fps:.1f} FPS ({width}x{height})")

        # Update initial metadata in DB
        with SessionLocal() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
            if job:
                job.status = "ANALYZING"
                job.analysis_type = self.analysis_type
                job.total_frames = self.total_frames
                job.video_fps = self.video_fps
                job.duration_seconds = duration_sec
                job.started_at = datetime.now(timezone.utc)
                db.commit()

        stem = Path(self.file_path).stem
        analyzed_video_path = RESULTS_DIR / f"analyzed_{self.analysis_type.lower()}_{stem}_{self.job_id[:8]}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(analyzed_video_path), fourcc, max(1.0, self.video_fps), (width, height))

        last_db_flush = time.time()
        last_ws_broadcast = time.time()
        last_detection_flush = time.time()
        frame_idx = 0
        total_inference_ms = 0.0

        if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
            runway_light_service.reset_grid()

        try:
            while not self._stop_event.is_set():
                # Check for pause
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                ok, frame = cap.read()
                if not ok:
                    break  # End of video reached

                frame_idx += 1
                t_frame_start = time.time()

                if frame_idx % 50 == 0 or frame_idx == 1:
                    logger.info(f"[{self.analysis_type}_INFERENCE] Frame {frame_idx}/{self.total_frames}")

                frame_dets: List[Dict[str, Any]] = []
                annotated_frame = frame

                # ----------------------------------------------------
                # STRICT MODEL ISOLATION (PRD Section 3, 4, 6, 8, 17)
                # ----------------------------------------------------
                if self.analysis_type in ("NAVIGATION", "ALL"):
                    # Navigation Model ONLY (navigation_best.pt)
                    if navigation_service.loaded:
                        raw_dets = navigation_service.predict(frame, conf_threshold=settings.NAVIGATION_CONFIDENCE)
                        for d in raw_dets:
                            d["model"] = "navigation"
                            d["analysis_type"] = "NAVIGATION"
                        self.total_frame_detections += len(raw_dets)
                        tracked = self.tracker.update(raw_dets, frame_idx)
                        frame_dets = tracked
                        for d in tracked:
                            tid = d.get("track_id")
                            if tid is not None:
                                self.unique_nav.add(tid)
                            cls = d.get("class_name", "NAV_OBJECT")
                            self.class_counts[cls] = self.class_counts.get(cls, 0) + 1
                        self.nav_count = len(self.unique_nav) if self.unique_nav else len(tracked)
                    annotated_frame = self._draw_annotations(frame, frame_dets)

                elif self.analysis_type in ("FOD", "FOD_DEBRIS"):
                    # FOD Model ONLY (FOD_Karhtikeyan.pt)
                    if fod_service.loaded:
                        raw_dets = fod_service.predict(frame, conf=settings.FOD_CONFIDENCE, iou=settings.IOU_THRESHOLD)
                        for d in raw_dets:
                            d["model"] = "fod"
                            d["analysis_type"] = "FOD"
                        self.total_frame_detections += len(raw_dets)
                        tracked = self.tracker.update(raw_dets, frame_idx)
                        frame_dets = tracked
                        # Retrieve active drone telemetry if connected
                        active_telem = None
                        try:
                            with SessionLocal() as db_telem:
                                active_telem = drone_service.get_telemetry(db_telem)
                        except Exception:
                            active_telem = None

                        if not active_telem and getattr(self, "telemetry", None):
                            active_telem = self.telemetry

                        for d in tracked:
                            tid = d.get("track_id")
                            if tid is not None:
                                self.unique_fod.add(tid)
                            # Predict geographical coordinates (FR-03, FR-04, FR-05)
                            coords = debris_coordinate_service.predict_coordinates(
                                bbox=d.get("bbox") or d.get("xyxy"),
                                image_width=width,
                                image_height=height,
                                telemetry=active_telem
                            )
                            d["debris_coordinates"] = coords
                            d["latitude"] = coords.get("latitude")
                            d["longitude"] = coords.get("longitude")
                            d["coordinate_uncertainty_m"] = coords.get("uncertainty_m")
                            d["coordinate_status"] = coords.get("status")
                            d["coordinate_method"] = coords.get("method")
                            d["coordinate_formatted"] = coords.get("formatted")

                        self.class_counts["FOD"] = len(self.unique_fod)
                        self.fod_count = len(self.unique_fod) if self.unique_fod else len(tracked)
                    annotated_frame = self._draw_annotations(frame, frame_dets)

                elif self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
                    # Runway Light Model ONLY (runway_light_best.pt)
                    if runway_light_service.loaded:
                        raw_dets = runway_light_service.predict(frame, frame_idx=frame_idx, fps=self.video_fps, force_detect=True)
                        for d in raw_dets:
                            d["model"] = "runway_light"
                            d["analysis_type"] = "RUNWAY_LIGHT"
                        self.total_frame_detections += len(raw_dets)
                        frame_dets = raw_dets
                        self._update_runway_stats(frame_dets, frame_idx)
                        annotated_frame = runway_light_service.annotate_frame(frame, frame_dets, frame_idx=frame_idx, fps=self.video_fps)

                frame_inf_ms = (time.time() - t_frame_start) * 1000.0
                total_inference_ms += frame_inf_ms
                self.processed_frames = frame_idx
                self.recent_detections = frame_dets

                # Write frame to video
                if annotated_frame is not None and writer.isOpened():
                    writer.write(annotated_frame)

                # Persist detections to database (batched for performance)
                if frame_dets:
                    for d in frame_dets:
                        self.detection_buffer.append((frame_idx, d))
                    if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
                        try:
                            database_service.save_runway_light_results(
                                job_id=self.job_id,
                                frame_id=frame_idx,
                                detections=frame_dets,
                                timestamp=frame_idx / max(1.0, self.video_fps)
                            )
                        except Exception as ex_db:
                            logger.error(f"[ANALYSIS_WORKER] DB save runway light error: {ex_db}")

                now = time.time()
                # Batch flush detections every 60 items or every 1.0 second
                if self.detection_buffer and (len(self.detection_buffer) >= 60 or now - last_detection_flush >= 1.0):
                    try:
                        database_service.save_detections_batch(
                            session_id=self.job_id,
                            batched_items=self.detection_buffer
                        )
                        self.detection_buffer.clear()
                        last_detection_flush = now
                    except Exception as ex_db:
                        logger.error(f"[ANALYSIS_WORKER] DB batch save error: {ex_db}")

                # Real dynamic ETA & Speed Ratio Calculation (PRD Section 8, 9, 10)
                self.elapsed_seconds = max(0.1, now - self.start_time)
                self.processing_fps = self.processed_frames / self.elapsed_seconds
                self.speed_ratio = round(self.elapsed_seconds / max(0.1, duration_sec), 2)
                remaining_frames = max(0, self.total_frames - self.processed_frames)
                self.remaining_seconds = remaining_frames / max(0.1, self.processing_fps)

                finish_dt = datetime.now() + timedelta(seconds=self.remaining_seconds)
                self.estimated_finish_time = finish_dt.strftime("%-I:%M %p")

                # Throttle database write & websocket broadcasts to 4 Hz
                if now - last_ws_broadcast >= 0.25:
                    self._broadcast_progress(status="ANALYZING")
                    last_ws_broadcast = now

                if now - last_db_flush >= 1.0:
                    disp_nav = max(len(self.unique_nav), self.nav_count)
                    disp_fod = max(len(self.unique_fod), self.fod_count)
                    disp_lon = max(len(self.unique_light_on), self.light_on_count)
                    disp_loff = max(len(self.unique_light_off), self.light_off_count)

                    with SessionLocal() as db:
                        job = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
                        if job:
                            job.processed_frames = self.processed_frames
                            job.progress = round((self.processed_frames / max(1, self.total_frames)) * 100.0, 2)
                            job.processing_fps = round(self.processing_fps, 2)
                            job.elapsed_seconds = round(self.elapsed_seconds, 1)
                            job.estimated_remaining_seconds = round(self.remaining_seconds, 1)
                            job.estimated_finish_time = self.estimated_finish_time
                            job.analysis_type = self.analysis_type
                            job.total_detections = self.total_frame_detections
                            job.speed_ratio = self.speed_ratio
                            job.class_counts = json.dumps(self.class_counts)

                            if self.analysis_type in ("NAVIGATION", "ALL"):
                                job.nav_count = disp_nav
                                job.unique_nav_count = len(self.unique_nav)
                                job.fod_count = 0
                                job.light_on_count = 0
                                job.light_off_count = 0
                                job.confirmed_faults = 0
                            elif self.analysis_type in ("FOD", "FOD_DEBRIS"):
                                job.nav_count = 0
                                job.unique_nav_count = 0
                                job.fod_count = disp_fod
                                job.unique_fod_count = len(self.unique_fod)
                                job.light_on_count = 0
                                job.light_off_count = 0
                                job.confirmed_faults = 0
                            elif self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
                                job.nav_count = 0
                                job.unique_nav_count = 0
                                job.fod_count = 0
                                job.unique_fod_count = 0
                                job.light_on_count = self.light_on_count
                                job.light_off_count = self.light_off_count
                                job.unique_light_on = self.light_on_count
                                job.unique_light_off = self.light_off_count
                                job.confirmed_faults = self.confirmed_faults
                                job.unknown_light_count = self.unknown_light_count
                                job.rows_detected = self.rows_detected
                                job.row_results = json.dumps(self.row_results)

                            db.commit()
                    last_db_flush = now

            # End of processing loop
            cap.release()
            writer.release()

            # Flush any remaining detections in buffer
            if self.detection_buffer:
                try:
                    database_service.save_detections_batch(
                        session_id=self.job_id,
                        batched_items=self.detection_buffer
                    )
                    self.detection_buffer.clear()
                except Exception as ex_db:
                    logger.error(f"[ANALYSIS_WORKER] Final DB batch save error: {ex_db}")

            if self._stop_event.is_set():
                logger.info(f"[ANALYSIS_WORKER] Job {self.job_id} terminated early due to cancellation")
                return

            # Transcode output video to browser-playable H.264 (yuv420p) with faststart
            web_video_path = RESULTS_DIR / f"web_{self.analysis_type.lower()}_{stem}_{self.job_id[:8]}.mp4"
            try:
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", str(analyzed_video_path),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(web_video_path)
                ]
                ff_res = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if ff_res.returncode == 0 and web_video_path.exists() and os.path.getsize(web_video_path) > 0:
                    analyzed_video_path = web_video_path
                    logger.info(f"[ANALYSIS_WORKER] Web-optimized H.264 video generated: {web_video_path}")
                else:
                    logger.warning(f"[ANALYSIS_WORKER] ffmpeg exit code {ff_res.returncode}, keeping original mp4")
            except Exception as ex_ff:
                logger.warning(f"[ANALYSIS_WORKER] ffmpeg transcode error: {ex_ff}")

            # Finalize Job (PRD Section 23, 24, 25)
            final_elapsed = max(1.0, time.time() - self.start_time)
            avg_inf_ms = total_inference_ms / max(1, self.processed_frames)

            # Generate model-specific exports via export_service
            export_paths = export_service.export_all(self.job_id)

            disp_nav = max(len(self.unique_nav), self.nav_count)
            disp_fod = max(len(self.unique_fod), self.fod_count)
            disp_lon = self.light_on_count if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY") else max(len(self.unique_light_on), self.light_on_count)
            disp_loff = self.light_off_count if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY") else max(len(self.unique_light_off), self.light_off_count)

            outcome_st = "COMPLETED_WITH_DETECTIONS" if self.total_frame_detections > 0 else "COMPLETED_NO_DETECTIONS"

            with SessionLocal() as db:
                job = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
                if job:
                    job.status = "COMPLETED"
                    job.outcome_status = outcome_st
                    job.model_path = self.model_info.get("model_path")
                    job.model_version = self.model_info.get("sha256", "")[:16]
                    job.confidence_threshold = self.model_info.get("confidence_threshold", 0.20)
                    job.processed_frames = self.processed_frames
                    job.progress = 100.0
                    job.processing_fps = round(self.processed_frames / final_elapsed, 2)
                    job.elapsed_seconds = round(final_elapsed, 1)
                    job.estimated_remaining_seconds = 0.0
                    job.analysis_type = self.analysis_type

                    if self.analysis_type in ("NAVIGATION", "ALL"):
                        job.nav_count = disp_nav
                        job.unique_nav_count = len(self.unique_nav)
                        job.fod_count = 0
                        job.light_on_count = 0
                        job.light_off_count = 0
                        job.confirmed_faults = 0
                    elif self.analysis_type in ("FOD", "FOD_DEBRIS"):
                        job.nav_count = 0
                        job.unique_nav_count = 0
                        job.fod_count = disp_fod
                        job.unique_fod_count = len(self.unique_fod)
                        job.light_on_count = 0
                        job.light_off_count = 0
                        job.confirmed_faults = 0
                    elif self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
                        job.nav_count = 0
                        job.unique_nav_count = 0
                        job.fod_count = 0
                        job.unique_fod_count = 0
                        job.light_on_count = self.light_on_count
                        job.light_off_count = self.light_off_count
                        job.unique_light_on = self.light_on_count
                        job.unique_light_off = self.light_off_count
                        job.confirmed_faults = self.confirmed_faults
                        job.unknown_light_count = self.unknown_light_count
                        job.rows_detected = self.rows_detected
                        job.row_results = json.dumps(self.row_results)

                    job.avg_inference_ms = round(avg_inf_ms, 1)
                    job.annotated_media_path = str(analyzed_video_path)
                    final_speed_ratio = round(final_elapsed / max(0.1, duration_sec), 2)
                    self.speed_ratio = final_speed_ratio
                    job.speed_ratio = final_speed_ratio
                    job.total_detections = self.total_frame_detections
                    job.class_counts = json.dumps(self.class_counts)
                    job.report_csv_path = export_paths.get("csv")
                    job.report_json_path = export_paths.get("summary")
                    job.completed_at = datetime.now(timezone.utc)
                    if self.analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
                        try:
                            database_service.save_runway_light_summary(
                                job_id=self.job_id,
                                summary_data={
                                    "total_lights": self.total_lights_count,
                                    "lights_on": self.light_on_count,
                                    "lights_off": self.light_off_count,
                                    "lights_unknown": self.unknown_light_count,
                                    "confirmed_faults": self.confirmed_faults,
                                    "total_rows": self.rows_detected,
                                    "total_columns": max((s.get("column_id", 0) for s in self.runway_matrix), default=0),
                                    "average_confidence": sum(s.get("confidence", 0.0) for s in self.runway_matrix) / max(1, len(self.runway_matrix)),
                                    "processed_frames": self.processed_frames,
                                    "analysis_duration": round(final_elapsed, 2),
                                    "matrix": self.runway_matrix,
                                    "faults": self.runway_faults,
                                }
                            )
                        except Exception as ex_sum:
                            logger.error(f"[ANALYSIS_WORKER] Error saving final runway light summary: {ex_sum}")

                    db.commit()

                    try:
                        from backend.app.services.central_results_service import central_results_service
                        central_results_service.sync_analysis_job_to_central_result(self.job_id)
                    except Exception as ex_sync:
                        logger.error(f"[ANALYSIS_WORKER] Error syncing job to central results: {ex_sync}")

            self._broadcast_progress(status="COMPLETED", outcome_status=outcome_st)
            logger.info(f"[{self.analysis_type}_JOB] Analysis completed: {self.processed_frames} frames in {final_elapsed:.1f}s for {self.job_id}")

        except Exception as e:
            logger.error(f"[ANALYSIS_WORKER] Job {self.job_id} failed: {e}", exc_info=True)
            self._update_db_status("FAILED", error=str(e), outcome_status="FAILED")
            try:
                from backend.app.services.central_results_service import central_results_service
                central_results_service.sync_analysis_job_to_central_result(self.job_id)
            except Exception:
                pass
            self._broadcast_progress(status="FAILED", outcome_status="FAILED")
        finally:
            self.is_running = False
            self.is_paused = False
            if cap.isOpened():
                cap.release()
            if writer.isOpened():
                writer.release()
