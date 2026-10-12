import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import numpy as np

from backend.app.core.logging import logger
from backend.app.services.navigation_service import navigation_service
from backend.app.services.fod_service import fod_service
from backend.app.services.runway_light_service import runway_light_service
from backend.app.services.alert_service import alert_service


class DetectionService:
    """
    Unified Detection Service Orchestrator (PRD Section 4, 21, 27).
    Executes simultaneous multi-model inference across:
      1. Navigation AI (navigation_best.pt)
      2. FOD Detection (FOD_Karhtikeyan.pt)
      3. Runway Light AI (runway_light_best.pt / yolo_scan_window_detection_new.py)
    Outputs Unified Detection JSON schema.
    """
    def __init__(self):
        self.frame_id_counter: int = 0

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "drone-camera-01",
        frame_id: Optional[int] = None,
        fps: float = 25.0,
        enable_navigation: bool = True,
        enable_fod: bool = True,
        enable_runway_light: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs all three models on the ingested video frame concurrently.
        Produces Unified Detection JSON (PRD Section 27).
        """
        start_time = time.time()
        if frame_id is not None:
            self.frame_id_counter = frame_id
        else:
            self.frame_id_counter += 1
        current_frame_id = self.frame_id_counter
        timestamp_str = datetime.now(timezone.utc).isoformat()

        all_detections: List[Dict[str, Any]] = []

        # 1. Navigation AI Detection (PRD Section 5.1)
        if enable_navigation and navigation_service.loaded:
            try:
                nav_dets = navigation_service.predict(frame)
                all_detections.extend(nav_dets)
            except Exception as e:
                logger.error(f"[DETECTION_SERVICE] Navigation inference error: {e}")

        # 2. FOD AI Detection (PRD Section 6)
        if enable_fod and fod_service.loaded:
            try:
                fod_dets = fod_service.predict(frame)
                all_detections.extend(fod_dets)
            except Exception as e:
                logger.error(f"[DETECTION_SERVICE] FOD inference error: {e}")

        # 3. Runway Light Detection (PRD Section 7 & 8)
        if enable_runway_light and runway_light_service.loaded:
            try:
                runway_dets = runway_light_service.predict(
                    frame,
                    frame_idx=current_frame_id,
                    fps=fps
                )
                all_detections.extend(runway_dets)
            except Exception as e:
                logger.error(f"[DETECTION_SERVICE] Runway Light inference error: {e}")

        latency_ms = round((time.time() - start_time) * 1000, 2)
        inference_fps = round(1000.0 / max(latency_ms, 1.0), 1)

        # Process alerts and temporal confirmations (PRD Section 32, 33)
        alerts, counts = alert_service.process_frame_detections(all_detections, camera_id=camera_id)

        # Summary counts
        nav_count = sum(1 for d in all_detections if d.get("model") == "navigation")
        fod_count = sum(1 for d in all_detections if d.get("model") == "fod" or d.get("class_name") == "FOD")
        light_on_count = sum(1 for d in all_detections if d.get("class_name") in ("LIGHT ON", "ON"))
        light_off_count = sum(1 for d in all_detections if d.get("class_name") in ("LIGHT OFF", "OFF"))
        light_off_gap_count = sum(1 for d in all_detections if d.get("state") == "OFF-GAP")

        summary = {
            "nav_count": nav_count,
            "fod_count": fod_count,
            "light_on_count": light_on_count,
            "light_off_count": light_off_count,
            "light_off_gap_count": light_off_gap_count,
            "total_detections": len(all_detections),
        }

        # PRD Section 27 Unified JSON Output
        return {
            "frame_id": current_frame_id,
            "timestamp": timestamp_str,
            "camera_id": camera_id,
            "latency_ms": latency_ms,
            "inference_fps": inference_fps,
            "detections": all_detections,
            "alerts": alerts,
            "summary": summary,
        }

    def save_detections(
        self,
        db,
        detections: List[Dict[str, Any]],
        drone_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        image_url: Optional[str] = None,
        frame_number: int = 0
    ):
        """Persists detection events to database (PRD Section 38)."""
        from backend.app.db.models import Detection

        saved = []
        for det in detections:
            bbox = det.get("bbox", {})
            if isinstance(bbox, dict):
                x = bbox.get("x1", 0.0)
                y = bbox.get("y1", 0.0)
                w = bbox.get("x2", 0.0) - x
                h = bbox.get("y2", 0.0) - y
            elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                x = bbox[0]
                y = bbox[1]
                w = bbox[2] - bbox[0] if bbox[2] > bbox[0] else bbox[2]
                h = bbox[3] - bbox[1] if bbox[3] > bbox[1] else bbox[3]
            else:
                x, y, w, h = 0.0, 0.0, 10.0, 10.0

            d_record = Detection(
                drone_id=drone_id,
                mission_id=mission_id,
                class_name=det.get("class_name", "UNKNOWN"),
                class_id=det.get("class_id", 0),
                confidence=det.get("confidence", 0.0),
                x=float(x),
                y=float(y),
                width=float(w),
                height=float(h),
                frame_number=frame_number,
                image_url=image_url
            )
            db.add(d_record)
            saved.append(d_record)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[DETECTION_SERVICE] DB commit error: {e}")
        return saved

    def get_history(
        self,
        db,
        drone_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        class_name: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ):
        """Retrieves detection history with filters."""
        from backend.app.db.models import Detection

        query = db.query(Detection)
        if drone_id:
            query = query.filter(Detection.drone_id == drone_id)
        if mission_id:
            query = query.filter(Detection.mission_id == mission_id)
        if class_name:
            query = query.filter(Detection.class_name == class_name)
        if min_confidence is not None:
            query = query.filter(Detection.confidence >= min_confidence)
        return query.order_by(Detection.timestamp.desc()).offset(offset).limit(limit).all()


detection_service = DetectionService()
