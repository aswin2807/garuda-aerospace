import os
import uuid
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import cv2

from backend.app.core.logging import logger
from backend.app.db.database import SessionLocal
from backend.app.db.models import AnalysisJob, Detection, RunwayFaultRecord
from backend.app.services.analysis_worker import AnalysisWorker
from backend.app.services.image_service import image_service
from backend.app.services.model_verifier import model_verifier

UPLOADS_DIR = Path(os.getcwd()) / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class AnalysisService:
    """
    Central Analysis Orchestration Service (PRD Section 4, 7, 8, 11, 13, 14, 37, 38).
    Manages video and image analysis jobs, worker execution, pause/resume/cancel lifecycles,
    and results retrieval.
    """
    def __init__(self):
        self.active_workers: Dict[str, AnalysisWorker] = {}
        self.ws_manager: Optional[Any] = None

    def set_ws_manager(self, manager: Any):
        self.ws_manager = manager

    def create_video_job(
        self,
        filename: str,
        file_bytes: bytes,
        job_id: Optional[str] = None,
        analysis_type: str = "NAVIGATION",
    ) -> Dict[str, Any]:
        """
        Creates an offline video analysis job (PRD Section 7 & 24).
        Saves video to data/uploads/. The video remains PAUSED on upload until start_job() is invoked.
        """
        jid = job_id or f"analysis_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
        safe_name = Path(filename).name
        dest_path = UPLOADS_DIR / f"{jid}_{safe_name}"
        atype = (analysis_type or "NAVIGATION").upper()

        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        # Inspect video metadata using OpenCV
        cap = cv2.VideoCapture(str(dest_path))
        fps = 30.0
        total_frames = 0
        duration_sec = 0.0

        if cap.isOpened():
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration_sec = round(total_frames / max(1.0, fps), 2)
            cap.release()

        mod_info = model_verifier.verify_model(atype)

        with SessionLocal() as db:
            job = AnalysisJob(
                id=jid,
                filename=safe_name,
                file_path=str(dest_path),
                media_type="VIDEO",
                analysis_type=atype,
                status="QUEUED",  # Video QUEUED & PAUSED on upload per PRD
                outcome_status="QUEUED",
                model_path=mod_info.get("model_path"),
                model_version=mod_info.get("sha256", "")[:16],
                confidence_threshold=mod_info.get("confidence_threshold", 0.20),
                total_frames=total_frames,
                processed_frames=0,
                progress=0.0,
                video_fps=fps,
                duration_seconds=duration_sec,
            )
            db.add(job)
            db.commit()

        logger.info(f"[ANALYSIS_SERVICE] Created video job {jid} [{atype}] for {safe_name} ({total_frames} frames, {duration_sec}s) - QUEUED (PAUSED)")

        return {
            "id": jid,
            "job_id": jid,
            "video_name": safe_name,
            "filename": safe_name,
            "file_path": str(dest_path),
            "media_type": "VIDEO",
            "analysis_type": atype,
            "status": "QUEUED",
            "outcome_status": "QUEUED",
            "model_path": mod_info.get("model_path"),
            "model_version": mod_info.get("sha256", "")[:16],
            "confidence_threshold": mod_info.get("confidence_threshold", 0.20),
            "progress": 0.0,
            "total_frames": total_frames,
            "frames_total": total_frames,
            "duration_seconds": duration_sec,
            "video_fps": fps,
            "message": "Video uploaded and queued. Analysis is paused until started."
        }

    def create_image_job(
        self,
        filename: str,
        file_bytes: bytes,
        job_id: Optional[str] = None,
        analysis_type: str = "NAVIGATION",
    ) -> Dict[str, Any]:
        """
        Creates an image analysis job (PRD Section 5 & 34).
        """
        jid = job_id or f"img_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
        safe_name = Path(filename).name
        dest_path = UPLOADS_DIR / f"{jid}_{safe_name}"
        atype = (analysis_type or "NAVIGATION").upper()

        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        mod_info = model_verifier.verify_model(atype)

        with SessionLocal() as db:
            job = AnalysisJob(
                id=jid,
                filename=safe_name,
                file_path=str(dest_path),
                media_type="IMAGE",
                analysis_type=atype,
                status="QUEUED",
                outcome_status="QUEUED",
                model_path=mod_info.get("model_path"),
                model_version=mod_info.get("sha256", "")[:16],
                confidence_threshold=mod_info.get("confidence_threshold", 0.20),
                total_frames=1,
                processed_frames=0,
                progress=0.0,
            )
            db.add(job)
            db.commit()

        logger.info(f"[ANALYSIS_SERVICE] Created image job {jid} [{atype}] for {safe_name} - QUEUED")

        return {
            "id": jid,
            "job_id": jid,
            "video_name": safe_name,
            "filename": safe_name,
            "file_path": str(dest_path),
            "media_type": "IMAGE",
            "analysis_type": atype,
            "status": "QUEUED",
            "outcome_status": "QUEUED",
            "model_path": mod_info.get("model_path"),
            "model_version": mod_info.get("sha256", "")[:16],
            "confidence_threshold": mod_info.get("confidence_threshold", 0.20),
            "progress": 0.0,
            "total_frames": 1,
            "frames_total": 1,
            "duration_seconds": 0.0,
            "video_fps": 0.0,
            "message": "Image uploaded and queued."
        }

    def start_job(self, job_id: str) -> Dict[str, Any]:
        """
        Starts processing for an uploaded video or image job in the background (PRD Section 8, 11).
        Does NOT block HTTP request; returns immediately with status ANALYZING.
        """
        with SessionLocal() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            if job.status == "ANALYZING":
                return {
                    "id": job_id,
                    "job_id": job_id,
                    "status": "ANALYZING",
                    "message": "Job is already analyzing"
                }

            media_type = job.media_type
            file_path = job.file_path
            analysis_type = (job.analysis_type or "NAVIGATION").upper()

        if media_type == "VIDEO":
            worker = AnalysisWorker(
                job_id=job_id,
                file_path=file_path,
                analysis_type=analysis_type,
                media_type="VIDEO",
                analyze_every_frame=True,
                ws_manager=self.ws_manager,
            )
            self.active_workers[job_id] = worker
            worker.start()

            return {
                "id": job_id,
                "job_id": job_id,
                "analysis_type": analysis_type,
                "status": "ANALYZING",
                "message": f"{analysis_type} video analysis started for job {job_id}"
            }

        elif media_type == "IMAGE":
            # Execute real image analysis strictly isolated by analysis_type
            result = image_service.analyze_image(file_path, job_id=job_id, analysis_type=analysis_type)
            counts = result.get("counts", {})
            annotated_path = result.get("annotated_image_path")
            total_dets = len(result.get("detections", []))
            outcome = "COMPLETED_WITH_DETECTIONS" if total_dets > 0 else "COMPLETED_NO_DETECTIONS"

            with SessionLocal() as db:
                j = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
                if j:
                    j.status = "COMPLETED"
                    j.outcome_status = outcome
                    j.total_detections = total_dets
                    j.processed_frames = 1
                    j.progress = 100.0
                    j.annotated_media_path = annotated_path
                    j.completed_at = datetime.now(timezone.utc)
                    j.elapsed_seconds = round(result.get("processing_time_ms", 0.0) / 1000.0, 2)
                    j.avg_inference_ms = result.get("processing_time_ms", 0.0)

                    if analysis_type in ("NAVIGATION", "ALL"):
                        j.nav_count = counts.get("navigation", 0)
                        j.unique_nav_count = counts.get("navigation", 0)
                        j.fod_count = 0
                        j.unique_fod_count = 0
                        j.light_on_count = 0
                        j.light_off_count = 0
                        j.confirmed_faults = 0
                    elif analysis_type in ("FOD", "FOD_DEBRIS"):
                        j.nav_count = 0
                        j.unique_nav_count = 0
                        j.fod_count = counts.get("fod", 0)
                        j.unique_fod_count = counts.get("fod", 0)
                        j.light_on_count = 0
                        j.light_off_count = 0
                        j.confirmed_faults = 0
                    elif analysis_type in ("RUNWAY_LIGHT", "RUNWAY"):
                        j.nav_count = 0
                        j.unique_nav_count = 0
                        j.fod_count = 0
                        j.unique_fod_count = 0
                        j.light_on_count = counts.get("light_on", 0)
                        j.light_off_count = counts.get("light_off", 0)
                        j.unique_light_on = counts.get("light_on", 0)
                        j.unique_light_off = counts.get("light_off", 0)
                        j.confirmed_faults = counts.get("confirmed_faults", 0)
                        j.unknown_light_count = counts.get("unknown_lights", 0)
                        j.rows_detected = counts.get("rows_detected", 0)
                        j.row_results = json.dumps(counts.get("row_results", []))
                    db.commit()

                    try:
                        from backend.app.services.central_results_service import central_results_service
                        central_results_service.sync_analysis_job_to_central_result(job_id)
                    except Exception as ex_sync:
                        logger.error(f"[ANALYSIS_SERVICE] Error syncing image job to central results: {ex_sync}")

            return {
                "id": job_id,
                "job_id": job_id,
                "analysis_type": analysis_type,
                "status": "COMPLETED",
                "outcome_status": outcome,
                "message": f"{analysis_type} image analysis completed for job {job_id}",
                "result": result,
            }

        return {"id": job_id, "job_id": job_id, "status": "UNKNOWN"}

    def pause_job(self, job_id: str) -> Dict[str, Any]:
        """Pauses analysis (PRD Section 13)."""
        worker = self.active_workers.get(job_id)
        if worker:
            worker.pause()
            return {"id": job_id, "job_id": job_id, "status": "PAUSED", "message": "Analysis paused"}
        raise ValueError(f"Active worker for job {job_id} not found")

    def resume_job(self, job_id: str) -> Dict[str, Any]:
        """Resumes analysis (PRD Section 13)."""
        worker = self.active_workers.get(job_id)
        if worker:
            worker.resume()
            return {"id": job_id, "job_id": job_id, "status": "ANALYZING", "message": "Analysis resumed"}
        raise ValueError(f"Active worker for job {job_id} not found")

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancels analysis (PRD Section 14)."""
        worker = self.active_workers.get(job_id)
        if worker:
            worker.cancel()
            del self.active_workers[job_id]
            return {"id": job_id, "job_id": job_id, "status": "CANCELLED", "message": "Analysis cancelled"}

        with SessionLocal() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if job:
                job.status = "CANCELLED"
                db.commit()
                return {"id": job_id, "job_id": job_id, "status": "CANCELLED", "message": "Job cancelled"}

        raise ValueError(f"Job {job_id} not found")

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Returns live job status and ETA with strict model isolation (PRD Section 9, 10, 12)."""
        worker = self.active_workers.get(job_id)
        if worker and not worker.is_running:
            self.active_workers.pop(job_id, None)
            worker = None

        if worker and worker.is_running:
            progress_pct = round((worker.processed_frames / max(1, worker.total_frames)) * 100.0, 2)
            atype = (worker.analysis_type or "NAVIGATION").upper()

            disp_nav = max(len(worker.unique_nav), worker.nav_count) if atype in ("NAVIGATION", "ALL") else 0
            disp_fod = max(len(worker.unique_fod), worker.fod_count) if atype in ("FOD", "FOD_DEBRIS") else 0
            disp_lon = max(len(worker.unique_light_on), worker.light_on_count) if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            disp_loff = max(len(worker.unique_light_off), worker.light_off_count) if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            faults = worker.confirmed_faults if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            unknown_l = worker.unknown_light_count if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            rows = worker.rows_detected if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            row_res = worker.row_results if atype in ("RUNWAY_LIGHT", "RUNWAY") else []

            return {
                "id": job_id,
                "job_id": job_id,
                "video_name": Path(worker.file_path).name,
                "filename": Path(worker.file_path).name,
                "media_type": worker.media_type,
                "analysis_type": atype,
                "status": "PAUSED" if worker.is_paused else "ANALYZING",
                "total_frames": worker.total_frames,
                "frames_total": worker.total_frames,
                "processed_frames": worker.processed_frames,
                "frames_processed": worker.processed_frames,
                "progress": progress_pct,
                "processing_fps": round(worker.processing_fps, 2),
                "fps": round(worker.processing_fps, 2),
                "video_fps": round(worker.video_fps, 2),
                "inference_ms": round((worker.elapsed_seconds / max(1, worker.processed_frames)) * 1000.0, 1),
                "elapsed_seconds": round(worker.elapsed_seconds, 1),
                "remaining_seconds": round(worker.remaining_seconds, 1),
                "eta_seconds": round(worker.remaining_seconds, 1),
                "estimated_finish_time": worker.estimated_finish_time,
                "nav_count": disp_nav,
                "navigation_count": disp_nav,
                "fod_count": disp_fod,
                "unique_fod_count": len(worker.unique_fod) if atype in ("FOD", "FOD_DEBRIS") else 0,
                "unique_nav_count": len(worker.unique_nav) if atype in ("NAVIGATION", "ALL") else 0,
                "total_detections": worker.total_frame_detections,
                "total_frame_detections": worker.total_frame_detections,
                "speed_ratio": round(worker.speed_ratio, 2),
                "class_counts": worker.class_counts,
                "light_on_count": disp_lon,
                "light_off_count": disp_loff,
                "confirmed_faults": faults,
                "unknown_light_count": unknown_l,
                "rows_detected": rows,
                "row_results": row_res,
                "counts": {
                    "navigation": disp_nav,
                    "fod": disp_fod,
                    "light_on": disp_lon,
                    "light_off": disp_loff,
                    "confirmed_faults": faults,
                    "unknown_lights": unknown_l,
                    "rows_detected": rows,
                },
                "performance": {
                    "fps": round(worker.processing_fps, 2),
                    "inference_ms": round((worker.elapsed_seconds / max(1, worker.processed_frames)) * 1000.0, 1),
                },
                "outcome_status": "PAUSED" if worker.is_paused else "ANALYZING",
                "model_path": getattr(worker, "model_info", {}).get("model_path"),
                "model_version": getattr(worker, "model_info", {}).get("sha256", "")[:16],
                "confidence_threshold": getattr(worker, "model_info", {}).get("confidence_threshold", 0.20),
            }

        with SessionLocal() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            atype = (job.analysis_type or "NAVIGATION").upper()
            row_res = []
            if job.row_results:
                try:
                    row_res = json.loads(job.row_results)
                except Exception:
                    row_res = []

            disp_nav = job.nav_count if atype in ("NAVIGATION", "ALL") else 0
            disp_fod = job.fod_count if atype in ("FOD", "FOD_DEBRIS") else 0
            disp_lon = job.light_on_count if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            disp_loff = job.light_off_count if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            faults = job.confirmed_faults if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            unknown_l = job.unknown_light_count if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            rows = job.rows_detected if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0

            cls_counts = {}
            if job.class_counts:
                try:
                    cls_counts = json.loads(job.class_counts)
                except Exception:
                    cls_counts = {}

            return {
                "id": job.id,
                "job_id": job.id,
                "video_name": job.filename,
                "filename": job.filename,
                "media_type": job.media_type,
                "analysis_type": atype,
                "status": job.status,
                "total_frames": job.total_frames,
                "frames_total": job.total_frames,
                "processed_frames": job.processed_frames,
                "frames_processed": job.processed_frames,
                "progress": job.progress,
                "processing_fps": job.processing_fps,
                "fps": job.processing_fps,
                "video_fps": job.video_fps,
                "inference_ms": job.avg_inference_ms,
                "elapsed_seconds": job.elapsed_seconds,
                "remaining_seconds": job.estimated_remaining_seconds,
                "eta_seconds": job.estimated_remaining_seconds,
                "estimated_finish_time": job.estimated_finish_time,
                "nav_count": disp_nav,
                "navigation_count": disp_nav,
                "fod_count": disp_fod,
                "unique_fod_count": job.unique_fod_count if atype in ("FOD", "FOD_DEBRIS") else 0,
                "unique_nav_count": job.unique_nav_count if atype in ("NAVIGATION", "ALL") else 0,
                "total_detections": job.total_detections or 0,
                "total_frame_detections": job.total_detections or 0,
                "speed_ratio": job.speed_ratio or 0.0,
                "class_counts": cls_counts,
                "light_on_count": disp_lon,
                "light_off_count": disp_loff,
                "confirmed_faults": faults,
                "unknown_light_count": unknown_l,
                "rows_detected": rows,
                "row_results": row_res,
                "counts": {
                    "navigation": disp_nav,
                    "fod": disp_fod,
                    "light_on": disp_lon,
                    "light_off": disp_loff,
                    "confirmed_faults": faults,
                    "unknown_lights": unknown_l,
                    "rows_detected": rows,
                },
                "performance": {
                    "fps": job.processing_fps,
                    "inference_ms": job.avg_inference_ms or 0.0,
                },
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "outcome_status": job.outcome_status or (
                    ("COMPLETED_WITH_DETECTIONS" if (job.total_detections or 0) > 0 else "COMPLETED_NO_DETECTIONS")
                    if job.status == "COMPLETED" else job.status
                ),
                "model_path": job.model_path,
                "model_version": job.model_version,
                "confidence_threshold": job.confidence_threshold,
            }

    def get_job_results(self, job_id: str) -> Dict[str, Any]:
        """Returns final analytics and report paths with strict model isolation (PRD Section 29, 32)."""
        with SessionLocal() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            atype = (job.analysis_type or "NAVIGATION").upper()
            row_res = []
            if job.row_results:
                try:
                    row_res = json.loads(job.row_results)
                except Exception:
                    row_res = []

            # Sample detections filtered by job_id and model/analysis_type
            query = db.query(Detection).filter((Detection.job_id == job_id) | (Detection.session_id == job_id))
            if atype in ("NAVIGATION", "FOD", "RUNWAY_LIGHT"):
                query = query.filter(Detection.analysis_type == atype)
            sample_dets = query.order_by(Detection.frame_number.asc()).limit(500).all()

            fps = max(1.0, float(job.video_fps or 30.0))
            formatted_sample = []
            for d in sample_dets:
                frame_num = int(d.frame_number or 0)
                ts_sec = round(frame_num / fps, 2)
                mins = int(ts_sec // 60)
                secs = int(ts_sec % 60)
                tenths = int(round((ts_sec % 1) * 10)) % 10
                ts_fmt = f"{mins:02d}:{secs:02d}.{tenths:01d}"

                is_fod = (d.analysis_type or atype) in ("FOD", "FOD_DEBRIS")
                coords = None
                if is_fod:
                    coords = {
                        "latitude": d.latitude,
                        "longitude": d.longitude,
                        "crs": d.coordinate_crs or "WGS84",
                        "uncertainty_m": d.coordinate_uncertainty_m,
                        "status": d.coordinate_status or "unavailable",
                        "method": d.coordinate_method or "none",
                        "formatted": d.coordinate_formatted or (
                            "Coordinates unavailable"
                            if d.latitude is None
                            else f"{abs(d.latitude):.6f}° {'N' if d.latitude >= 0 else 'S'}, {abs(d.longitude):.6f}° {'E' if d.longitude >= 0 else 'W'}"
                        ),
                    }
                formatted_sample.append({
                    "frame": frame_num,
                    "timestamp_seconds": ts_sec,
                    "timestamp_formatted": ts_fmt,
                    "model": d.model_name,
                    "analysis_type": d.analysis_type or atype,
                    "class_name": d.class_name,
                    "confidence": d.confidence,
                    "bbox": [d.x1, d.y1, d.x2, d.y2],
                    "track_id": d.track_id,
                    "debris_coordinates": coords,
                    "latitude": d.latitude,
                    "longitude": d.longitude,
                    "coordinate_uncertainty_m": d.coordinate_uncertainty_m,
                    "coordinate_status": d.coordinate_status or "unavailable",
                    "coordinate_method": d.coordinate_method or "none",
                    "coordinate_formatted": d.coordinate_formatted or (coords["formatted"] if coords else None),
                })

            # If formatted_sample is empty for RUNWAY_LIGHT, supplement from RunwayLightResult table
            if not formatted_sample and atype in ("RUNWAY_LIGHT", "RUNWAY"):
                from backend.app.services.database_service import database_service
                rw_dets = database_service.get_runway_light_results(job.id, limit=500)
                for r in rw_dets:
                    f_id = int(r.get("frame_id") or 0)
                    ts_sec = round(float(r.get("timestamp") or (f_id / fps)), 2)
                    mins = int(ts_sec // 60)
                    secs = int(ts_sec % 60)
                    tenths = int(round((ts_sec % 1) * 10)) % 10
                    ts_fmt = f"{mins:02d}:{secs:02d}.{tenths:01d}"

                    formatted_sample.append({
                        "frame": f_id,
                        "timestamp_seconds": ts_sec,
                        "timestamp_formatted": ts_fmt,
                        "model": "runway_light",
                        "analysis_type": "RUNWAY_LIGHT",
                        "class_name": r.get("class_name") or ("LIGHT ON" if r.get("status") == "ON" else "LIGHT OFF"),
                        "confidence": float(r.get("confidence") or 0.0),
                        "bbox": r.get("bbox") or [0, 0, 0, 0],
                        "track_id": r.get("track_id") or r.get("light_id"),
                        "status": r.get("status"),
                        "row_id": r.get("row_id"),
                        "column_id": r.get("column_id"),
                        "is_confirmed": r.get("is_confirmed", False),
                    })

            elapsed_m = int(job.elapsed_seconds // 60)
            elapsed_s = int(job.elapsed_seconds % 60)
            proc_time_str = f"{elapsed_m:02d}:{elapsed_s:02d}"

            disp_nav = job.nav_count if atype in ("NAVIGATION", "ALL") else 0
            disp_unav = job.unique_nav_count if atype in ("NAVIGATION", "ALL") else 0
            disp_fod = job.fod_count if atype in ("FOD", "FOD_DEBRIS") else 0
            disp_ufod = job.unique_fod_count if atype in ("FOD", "FOD_DEBRIS") else 0
            disp_lon = job.light_on_count if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            disp_ulon = job.unique_light_on if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            disp_loff = job.light_off_count if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            disp_uloff = job.unique_light_off if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            faults = job.confirmed_faults if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            unknown_l = job.unknown_light_count if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0
            rows = job.rows_detected if atype in ("RUNWAY_LIGHT", "RUNWAY") else 0

            summary_info = {}
            if atype in ("RUNWAY_LIGHT", "RUNWAY"):
                from backend.app.services.database_service import database_service
                summary_info = database_service.get_runway_light_summary(job.id) or {}

            cls_counts = {}
            if job.class_counts:
                try:
                    cls_counts = json.loads(job.class_counts)
                except Exception:
                    cls_counts = {}

            return {
                "id": job.id,
                "job_id": job.id,
                "video_name": job.filename,
                "filename": job.filename,
                "media_type": job.media_type,
                "analysis_type": atype,
                "status": job.status,
                "total_frames": job.total_frames,
                "frames_total": job.total_frames,
                "processed_frames": job.processed_frames,
                "frames_processed": job.processed_frames,
                "duration_seconds": job.duration_seconds,
                "processing_time_formatted": proc_time_str,
                "nav_count": disp_nav,
                "navigation_count": disp_nav,
                "fod_count": disp_fod,
                "total_detections": job.total_detections or 0,
                "total_frame_detections": job.total_detections or 0,
                "speed_ratio": job.speed_ratio or 0.0,
                "class_counts": cls_counts,
                "total_lights": summary_info.get("total_lights", disp_lon + disp_loff + unknown_l),
                "light_on_count": disp_lon,
                "light_off_count": disp_loff,
                "confirmed_faults": faults,
                "unknown_light_count": unknown_l,
                "rows_detected": rows,
                "row_results": row_res,
                "matrix": summary_info.get("matrix", []),
                "faults": summary_info.get("faults", []),
                "unique_nav_count": disp_unav,
                "unique_fod_count": disp_ufod,
                "unique_light_on": disp_ulon,
                "unique_light_off": disp_uloff,
                "avg_confidence": job.avg_confidence,
                "average_confidence": job.avg_confidence,
                "avg_inference_ms": job.avg_inference_ms,
                "inference_ms": job.avg_inference_ms,
                "annotated_media_path": job.annotated_media_path,
                "file_path": job.file_path,
                "video_fps": job.video_fps,
                "report_csv_path": job.report_csv_path,
                "report_json_path": job.report_json_path,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "error_message": job.error_message,
                "outcome_status": job.outcome_status or (
                    ("COMPLETED_WITH_DETECTIONS" if (job.total_detections or 0) > 0 else "COMPLETED_NO_DETECTIONS")
                    if job.status == "COMPLETED" else job.status
                ),
                "model_path": job.model_path,
                "model_version": job.model_version,
                "confidence_threshold": job.confidence_threshold,
                "sample_detections": formatted_sample,
            }

    def get_runway_summary(self, job_id: str) -> Dict[str, Any]:
        """Returns dedicated runway grid summary, matrix slots, and fault records."""
        from backend.app.services.database_service import database_service

        worker = self.active_workers.get(job_id)
        if worker and worker.is_running:
            return {
                "job_id": job_id,
                "status": "ANALYZING",
                "total_lights": worker.total_lights_count,
                "lights_on": worker.light_on_count,
                "lights_off": worker.light_off_count,
                "lights_unknown": worker.unknown_light_count,
                "confirmed_faults": worker.confirmed_faults,
                "total_rows": worker.rows_detected,
                "total_columns": max((s.get("column_id", 0) for s in worker.runway_matrix), default=0),
                "average_confidence": sum(s.get("confidence", 0.0) for s in worker.runway_matrix) / max(1, len(worker.runway_matrix)),
                "processed_frames": worker.processed_frames,
                "analysis_duration": round(worker.elapsed_seconds, 2),
                "matrix": worker.runway_matrix,
                "row_results": worker.row_results,
                "faults": worker.runway_faults,
            }

        summary = database_service.get_runway_light_summary(job_id)
        if summary:
            with SessionLocal() as db:
                job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
                if job and job.row_results:
                    try:
                        summary["row_results"] = json.loads(job.row_results)
                    except Exception:
                        summary["row_results"] = []
                else:
                    summary["row_results"] = []
                summary["status"] = job.status if job else "COMPLETED"
            return summary

        with SessionLocal() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                raise ValueError(f"Runway Light job {job_id} not found")
            row_res = []
            if job.row_results:
                try:
                    row_res = json.loads(job.row_results)
                except Exception:
                    row_res = []
            return {
                "job_id": job.id,
                "status": job.status,
                "total_lights": job.light_on_count + job.light_off_count + job.unknown_light_count,
                "lights_on": job.light_on_count,
                "lights_off": job.light_off_count,
                "lights_unknown": job.unknown_light_count,
                "confirmed_faults": job.confirmed_faults,
                "total_rows": job.rows_detected,
                "total_columns": 0,
                "average_confidence": job.avg_confidence,
                "processed_frames": job.processed_frames,
                "analysis_duration": job.elapsed_seconds,
                "matrix": [],
                "row_results": row_res,
                "faults": [],
            }

    def list_jobs(self, limit: int = 50, analysis_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists historical analysis jobs, optionally filtered by analysis_type."""
        with SessionLocal() as db:
            query = db.query(AnalysisJob)
            if analysis_type:
                query = query.filter(AnalysisJob.analysis_type == analysis_type.upper())
            jobs = (
                query.order_by(AnalysisJob.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": j.id,
                    "job_id": j.id,
                    "video_name": j.filename,
                    "filename": j.filename,
                    "media_type": j.media_type,
                    "analysis_type": j.analysis_type,
                    "status": j.status,
                    "total_frames": j.total_frames,
                    "frames_total": j.total_frames,
                    "processed_frames": j.processed_frames,
                    "frames_processed": j.processed_frames,
                    "progress": j.progress,
                    "nav_count": j.nav_count if j.analysis_type == "NAVIGATION" else 0,
                    "fod_count": j.fod_count if j.analysis_type == "FOD" else 0,
                    "light_on_count": j.light_on_count if j.analysis_type == "RUNWAY_LIGHT" else 0,
                    "light_off_count": j.light_off_count if j.analysis_type == "RUNWAY_LIGHT" else 0,
                    "confirmed_faults": j.confirmed_faults if j.analysis_type == "RUNWAY_LIGHT" else 0,
                    "unknown_light_count": j.unknown_light_count if j.analysis_type == "RUNWAY_LIGHT" else 0,
                    "rows_detected": j.rows_detected if j.analysis_type == "RUNWAY_LIGHT" else 0,
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                }
                for j in jobs
            ]

analysis_service = AnalysisService()
