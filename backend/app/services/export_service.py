import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import cv2

from backend.app.core.logging import logger
from backend.app.services.database_service import database_service

OUTPUT_DIR = Path(os.getcwd()) / "data" / "outputs"


class ExportService:
    """
    Session Export Service (PRD Section 22).
    Exports detection records to CSV, summary statistics to JSON,
    and annotated video to MP4 in data/outputs/.
    """
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_session_csv(self, session_id: str, detections: Optional[List[Dict[str, Any]]] = None) -> Path:
        """
        Exports all detections for a session to CSV (PRD Section 22).
        Format: frame, time_sec, track_id, model, class_id, class_name, state, confidence, x1, y1, x2, y2, cx, cy
        """
        csv_file = self.output_dir / f"session_{session_id}_detections.csv"

        if detections is None:
            # Query from database service
            db_dets = database_service.get_session_detections(session_id, limit=10000)
            detections = db_dets

        fieldnames = [
            "frame",
            "time_sec",
            "track_id",
            "model",
            "class_id",
            "class_name",
            "state",
            "confidence",
            "x1",
            "y1",
            "x2",
            "y2",
            "cx",
            "cy",
        ]

        with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for d in detections:
                frame_idx = d.get("frame_id") or d.get("frame") or 0
                time_sec = d.get("time_sec")
                if time_sec is None:
                    time_sec = d.get("timestamp") or 0.0

                # Bounding box coordinates
                x1 = d.get("x1", 0)
                y1 = d.get("y1", 0)
                x2 = d.get("x2", 0)
                y2 = d.get("y2", 0)
                if "bbox" in d and isinstance(d["bbox"], (list, tuple)) and len(d["bbox"]) >= 4:
                    x1, y1, x2, y2 = [int(round(v)) for v in d["bbox"][:4]]

                cx = round((x1 + x2) / 2.0, 1)
                cy = round((y1 + y2) / 2.0, 1)

                writer.writerow({
                    "frame": frame_idx,
                    "time_sec": f"{float(time_sec):.3f}" if isinstance(time_sec, (int, float)) else time_sec,
                    "track_id": d.get("track_id", ""),
                    "model": d.get("model_name") or d.get("model", ""),
                    "class_id": d.get("class_id", 0),
                    "class_name": d.get("class_name", ""),
                    "state": d.get("state", "ON" if "ON" in str(d.get("class_name", "")) else "OFF"),
                    "confidence": f"{float(d.get('confidence', 0.0)):.3f}",
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "cx": cx,
                    "cy": cy,
                })

        logger.info(f"[EXPORT_SERVICE] Detections CSV saved to: {csv_file}")
        return csv_file

    def export_session_summary(self, session_id: str, summary_data: Optional[Dict[str, Any]] = None) -> Path:
        """
        Exports session aggregated statistics to JSON (PRD Section 22).
        """
        summary_file = self.output_dir / f"session_{session_id}_summary.json"

        if summary_data is None:
            stats = database_service.get_session_statistics(session_id)
            session_meta = database_service.get_session(session_id) or {}

            # Query AnalysisJob for isolated analysis_type and row results
            atype = session_meta.get("analysis_type", "NAVIGATION")
            row_res = []
            title_map = {
                "NAVIGATION": "NAVIGATION ANALYSIS REPORT",
                "FOD": "FOD DEBRIS ANALYSIS REPORT",
                "RUNWAY_LIGHT": "RUNWAY LIGHT FAULT ANALYSIS REPORT",
            }

            job_metrics = {}
            try:
                from backend.app.db.database import SessionLocal
                from backend.app.db.models import AnalysisJob
                with SessionLocal() as db:
                    job = db.query(AnalysisJob).filter(AnalysisJob.id == session_id).first()
                    if job:
                        atype = (job.analysis_type or "NAVIGATION").upper()
                        if job.row_results:
                            try:
                                row_res = json.loads(job.row_results)
                            except Exception:
                                row_res = []
                        cls_counts = {}
                        if job.class_counts:
                            try:
                                cls_counts = json.loads(job.class_counts)
                            except Exception:
                                cls_counts = {}
                        job_metrics = {
                            "total_frames_analyzed": job.processed_frames or job.total_frames,
                            "video_duration_seconds": job.duration_seconds,
                            "analysis_elapsed_seconds": job.elapsed_seconds,
                            "speed_ratio": job.speed_ratio or (round(job.elapsed_seconds / max(0.1, job.duration_seconds), 2) if job.duration_seconds else 0.0),
                            "processing_fps": job.processing_fps,
                            "total_frame_detections": job.total_detections,
                            "unique_tracked_objects": job.unique_fod_count if atype in ("FOD", "FOD_DEBRIS") else job.unique_nav_count,
                            "class_counts": cls_counts,
                        }
            except Exception as e:
                logger.debug(f"[EXPORT_SERVICE] Job lookup skipped: {e}")

            summary_data = {
                "session_id": session_id,
                "analysis_type": atype,
                "report_title": title_map.get(atype, f"{atype} ANALYSIS REPORT"),
                "metadata": session_meta,
                "statistics": {**(stats or {}), **job_metrics},
                "performance_metrics": job_metrics,
                "row_results": row_res,
            }

        with open(summary_file, mode="w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, default=str)

        logger.info(f"[EXPORT_SERVICE] Session summary JSON saved to: {summary_file}")
        return summary_file

    def create_video_writer(
        self,
        session_id: str,
        width: int,
        height: int,
        fps: float = 25.0,
    ) -> Tuple[cv2.VideoWriter, Path]:
        """
        Initializes an OpenCV VideoWriter for saving annotated session video (PRD Section 22 & 23).
        """
        video_path = self.output_dir / f"session_{session_id}_annotated.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(video_path), fourcc, max(1.0, fps), (width, height))
        return writer, video_path

    def export_all(self, session_id: str, detections: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """
        Exports both CSV and JSON for a given session.
        """
        csv_path = self.export_session_csv(session_id, detections=detections)
        summary_path = self.export_session_summary(session_id)
        return {
            "csv": str(csv_path),
            "summary": str(summary_path),
        }


export_service = ExportService()
