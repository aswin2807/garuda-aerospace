import time
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.navigation_service import navigation_service
from backend.app.services.fod_service import fod_service
from backend.app.services.runway_light_service import runway_light_service
from backend.app.services.alert_service import alert_service
from backend.app.services.tracking_service import tracking_service
from backend.app.services.detection_aggregator import detection_aggregator
from backend.app.services.database_service import database_service
from backend.app.services.debris_coordinate_service import debris_coordinate_service
from backend.app.services.runway_roi_service import runway_roi_service

class FrameProcessor:
    """
    Central Frame Processing Engine.
    Coordinates frame ingestion, model inference scheduling, tracking,
    alert temporal confirmation, database logging, and WebSocket broadcast.
    Implements PRD Section 7, 8, 9, 10, 11, 12, 13, 14, 36.
    """
    def __init__(self):
        # Scheduling configuration (PRD Section 8)
        self.nav_enabled: bool = True
        self.nav_every_n: int = 1

        self.fod_enabled: bool = True
        self.fod_every_n: int = 1

        self.runway_enabled: bool = True
        self.runway_every_n: int = settings.RUNWAY_DETECT_STRIDE or 10

        # Cached detections for skipped frames to prevent flickering
        self._last_nav_dets: List[Dict[str, Any]] = []
        self._last_fod_dets: List[Dict[str, Any]] = []
        self._last_runway_dets: List[Dict[str, Any]] = []

        # Debug & Pipeline Counters (PRD Section 36)
        self.frames_received: int = 0
        self.frames_processed: int = 0
        self.navigation_inferences: int = 0
        self.fod_inferences: int = 0
        self.runway_inferences: int = 0
        self.navigation_detections: int = 0
        self.fod_detections: int = 0
        self.light_on_detections: int = 0
        self.light_off_detections: int = 0
        self.detections_received: int = 0
        self.database_events: int = 0
        self.video_connected: bool = False

        self._active_session_id: Optional[str] = None
        self._frame_id_counter: int = 0

    def reset_pipeline(self, session_id: Optional[str] = None):
        """
        Resets session state, tracking IDs, and counters (PRD Section 40)
        """
        self._frame_id_counter = 0
        self._last_nav_dets.clear()
        self._last_fod_dets.clear()
        self._last_runway_dets.clear()
        self._active_session_id = session_id
        tracking_service.reset_session()
        logger.info(f"[FRAME_PROCESSOR] Reset pipeline for session: {session_id}")

    def update_scheduling(
        self,
        nav_every_n: Optional[int] = None,
        fod_every_n: Optional[int] = None,
        runway_every_n: Optional[int] = None,
        nav_enabled: Optional[bool] = None,
        fod_enabled: Optional[bool] = None,
        runway_enabled: Optional[bool] = None
    ):
        """
        Dynamically updates model scheduling per PRD Section 8
        """
        if nav_every_n is not None:
            self.nav_every_n = max(1, nav_every_n)
        if fod_every_n is not None:
            self.fod_every_n = max(1, fod_every_n)
        if runway_every_n is not None:
            self.runway_every_n = max(1, runway_every_n)
        if nav_enabled is not None:
            self.nav_enabled = nav_enabled
        if fod_enabled is not None:
            self.fod_enabled = fod_enabled
        if runway_enabled is not None:
            self.runway_enabled = runway_enabled

    def draw_annotations(self, frame: np.ndarray, detections: List[Dict[str, Any]], camera_id: Optional[str] = None) -> np.ndarray:
        """
        Renders bounding boxes with labels, confidences, track IDs, and Runway Pathway ROI overlay onto a frame copy.
        """
        if frame is None or frame.size == 0:
            return frame
        out = frame.copy()
        h, w = out.shape[:2]

        # Draw active Runway Pathway ROI boundary overlay for FOD
        if self.fod_enabled:
            out = runway_roi_service.draw_pathway_overlay(
                out,
                camera_id=camera_id or "drone-01",
                alpha=0.08,
                draw_label=True
            )

        for d in detections:
            x1, y1, x2, y2 = 0, 0, 0, 0
            if "bbox" in d and isinstance(d["bbox"], (list, tuple)) and len(d["bbox"]) >= 4:
                x1, y1, x2, y2 = [int(round(v)) for v in d["bbox"][:4]]
            elif "bbox_dict" in d:
                bd = d["bbox_dict"]
                x1, y1, x2, y2 = int(round(bd.get("x1", 0))), int(round(bd.get("y1", 0))), int(round(bd.get("x2", 0))), int(round(bd.get("y2", 0)))

            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w - 1, x2))
            y2 = max(0, min(h - 1, y2))
            if x2 <= x1 or y2 <= y1:
                continue

            cls_name = str(d.get("class_name", "OBJ")).upper()
            model_type = d.get("model", "")
            state = str(d.get("state", "")).upper()
            conf = float(d.get("confidence", 0.0))
            conf_pct = int(round(conf * 100))

            # Distinguish LIGHT ON (Emerald Green) from LIGHT OFF (Crimson Red) (PRD Section 2.3)
            if "LIGHT ON" in cls_name or state == "ON":
                color = (94, 197, 34)      # Emerald Green in BGR (RGB: 34, 197, 94)
                label_txt = f"LIGHT ON · {conf_pct}%"
            elif "LIGHT OFF" in cls_name or state in ("OFF", "OFF-GAP"):
                color = (68, 68, 239)      # Crimson Red in BGR (RGB: 239, 68, 68)
                label_txt = f"LIGHT OFF · {conf_pct}%"
            elif "FOD" in cls_name or model_type == "fod":
                color = (0, 0, 255)        # Red in BGR for FOD
                label_txt = f"FOD · {conf_pct}%"
            else:
                color = (255, 180, 0)      # Aviation Amber
                label_txt = f"{cls_name} · {conf_pct}%"

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

            # Clean label badge with smart placement (PRD Section 2.2)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.44
            (tw, th), bl = cv2.getTextSize(label_txt, font, font_scale, 1)
            pill_h = th + bl + 6
            pill_w = tw + 8

            if y1 - pill_h >= 2:
                by1 = y1 - pill_h - 2
            else:
                by1 = min(h - pill_h - 2, y2 + 2)
            bx1 = max(2, min(x1, w - pill_w - 2))
            by2 = by1 + pill_h
            bx2 = bx1 + pill_w

            cv2.rectangle(out, (bx1, by1), (bx2, by2), color, -1)
            cv2.rectangle(out, (bx1, by1), (bx2, by2), (18, 18, 18), 1, cv2.LINE_AA)
            cv2.putText(out, label_txt, (bx1 + 4, by1 + th + 3), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        return out

    def process_frame(
        self,
        frame: np.ndarray,
        frame_id: Optional[int] = None,
        camera_id: str = "drone-01",
        session_id: Optional[str] = None,
        stream_fps: float = 30.0,
        source_fps: Optional[float] = None,
        conf_thresh: Optional[float] = None,
        return_annotated: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Executes complete pipeline on a single frame.
        """
        effective_fps = source_fps if source_fps is not None else stream_fps
        t0 = time.perf_counter()
        self.frames_received += 1
        self.video_connected = True

        if frame_id is not None:
            current_frame_id = frame_id
        else:
            self._frame_id_counter += 1
            current_frame_id = self._frame_id_counter

        sess_id = session_id or self._active_session_id
        nav_conf = conf_thresh if conf_thresh is not None else settings.NAVIGATION_CONFIDENCE
        fod_conf = conf_thresh if conf_thresh is not None else settings.FOD_CONFIDENCE
        runway_conf = conf_thresh if conf_thresh is not None else settings.RUNWAY_LIGHT_CONFIDENCE
        iou_thresh = settings.IOU_THRESHOLD

        all_dets: List[Dict[str, Any]] = []

        # 1. Navigation Model Inference (Scheduled)
        if self.nav_enabled and navigation_service.loaded:
            if current_frame_id == 1 or (current_frame_id % self.nav_every_n == 0):
                self._last_nav_dets = navigation_service.predict(frame, conf_threshold=nav_conf)
                self.navigation_inferences += 1
                self.navigation_detections += len(self._last_nav_dets)
            all_dets.extend(self._last_nav_dets)

        # 2. FOD Model Inference (Scheduled with Runway Pathway ROI Filtering)
        if self.fod_enabled and fod_service.loaded:
            if current_frame_id == 1 or (current_frame_id % self.fod_every_n == 0):
                raw_fod = fod_service.predict(
                    frame,
                    conf=fod_conf,
                    iou=iou_thresh,
                    filter_pathway=True,
                    camera_id=camera_id,
                    source_id=sess_id
                )
                # Compute ground coordinates for each FOD detection (FR-03, FR-04, FR-05)
                h_f, w_f = frame.shape[:2]
                for d in raw_fod:
                    coords = debris_coordinate_service.predict_coordinates(
                        bbox=d.get("bbox") or d.get("xyxy"),
                        image_width=w_f,
                        image_height=h_f,
                        telemetry=getattr(self, "telemetry", None)
                    )
                    d["debris_coordinates"] = coords
                    d["latitude"] = coords.get("latitude")
                    d["longitude"] = coords.get("longitude")
                    d["coordinate_uncertainty_m"] = coords.get("uncertainty_m")
                    d["coordinate_status"] = coords.get("status")
                    d["coordinate_method"] = coords.get("method")
                    d["coordinate_formatted"] = coords.get("formatted")
                self._last_fod_dets = raw_fod
                self.fod_inferences += 1
                self.fod_detections += len(self._last_fod_dets)
            all_dets.extend(self._last_fod_dets)

        # 3. Runway Light Model Inference (Scheduled)
        if self.runway_enabled and runway_light_service.loaded:
            if current_frame_id == 1 or (current_frame_id % self.runway_every_n == 0):
                self._last_runway_dets = runway_light_service.predict(frame, conf=runway_conf, iou=iou_thresh)
                self.runway_inferences += 1
                self.light_on_detections += sum(1 for d in self._last_runway_dets if d.get("class_id") == 1 or "ON" in str(d.get("class_name", "")))
                self.light_off_detections += sum(1 for d in self._last_runway_dets if d.get("class_id") == 0 or "OFF" in str(d.get("class_name", "")))
            all_dets.extend(self._last_runway_dets)

        self.frames_processed += 1
        self.detections_received += len(all_dets)

        # 4. Multi-model Tracking & Deduplication (PRD Section 13 & 23)
        tracked_dets = tracking_service.update(all_dets, current_frame_id)

        # 5. Temporal Alerts & Fault Confirmation (PRD Section 14)
        alerts, _ = alert_service.process_frame_detections(tracked_dets, camera_id=camera_id)

        t1 = time.perf_counter()
        inference_ms = max(0.5, round((t1 - t0) * 1000.0, 2))

        # 6. Aggregation (Counts, Unique Totals, Average Conf, Performance) (PRD Section 10, 11, 12)
        payload = detection_aggregator.aggregate(
            detections=tracked_dets,
            alerts=alerts,
            tracking_service_instance=tracking_service,
            inference_ms=inference_ms,
            stream_fps=effective_fps,
            frame_id=current_frame_id,
            camera_id=camera_id,
            session_id=sess_id
        )

        # 7. Generate Annotated Visual Frame with Bounding Boxes (if requested)
        if return_annotated:
            payload["annotated_frame"] = self.draw_annotations(frame, tracked_dets, camera_id=camera_id)

        # 8. Database Persistence (PRD Section 15, 16, 39)
        if sess_id:
            try:
                database_service.save_detections(
                    session_id=sess_id,
                    frame_id=current_frame_id,
                    detections=tracked_dets,
                    camera_id=camera_id
                )
                database_service.record_frame(
                    session_id=sess_id,
                    frame_number=current_frame_id,
                    stream_fps=effective_fps,
                    inference_ms=inference_ms,
                    counts=payload["counts"]
                )
                self.database_events += len(tracked_dets) + 1
            except Exception as e:
                logger.error(f"[FRAME_PROCESSOR] DB persist error: {e}")

        return payload

    def get_debug_pipeline(self, active_ws_clients: int = 0) -> Dict[str, Any]:
        """
        Critical Debug Mode endpoint per PRD Section 36
        """
        return {
            "video_connected": self.video_connected,
            "frames_received": self.frames_received,
            "frames_processed": self.frames_processed,
            "navigation_inferences": self.navigation_inferences,
            "fod_inferences": self.fod_inferences,
            "runway_light_inferences": self.runway_inferences,
            "runway_inferences": self.runway_inferences,
            "navigation_detections": self.navigation_detections,
            "fod_detections": self.fod_detections,
            "light_on_detections": self.light_on_detections,
            "light_off_detections": self.light_off_detections,
            "detections_received": self.detections_received,
            "database_events": self.database_events,
            "websocket_clients": active_ws_clients,
            "scheduling": {
                "navigation_every_n_frames": self.nav_every_n,
                "fod_every_n_frames": self.fod_every_n,
                "runway_every_n_frames": self.runway_every_n
            },
            "models_ready": {
                "navigation": navigation_service.loaded,
                "fod": fod_service.loaded,
                "runway_light": runway_light_service.loaded
            }
        }

frame_processor = FrameProcessor()
