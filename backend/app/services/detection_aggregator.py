from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import numpy as np

class DetectionAggregator:
    """
    Computes real-time frame object counts, session unique totals, average confidence,
    and performance metrics.
    Implements PRD Section 10, 11, 12, 18, 21, 24, 25.
    """

    def aggregate(
        self,
        detections: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]],
        tracking_service_instance,
        inference_ms: float,
        stream_fps: float = 30.0,
        frame_id: int = 0,
        camera_id: str = "drone-01",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds the unified standard payload for WebSocket and REST APIs.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Calculate Current Visible Counts (Active in this frame)
        nav_dets = [d for d in detections if d.get("model") == "navigation"]
        fod_dets = [d for d in detections if "FOD" in str(d.get("class_name", "")).upper() or d.get("model") == "fod"]
        light_on_dets = [d for d in detections if "LIGHT ON" in str(d.get("class_name", "")).upper() or str(d.get("class_name", "")).upper() == "ON"]
        light_off_dets = [
            d for d in detections
            if "LIGHT OFF" in str(d.get("class_name", "")).upper()
            or str(d.get("class_name", "")).upper() == "OFF"
            or d.get("state") == "OFF-GAP"
        ]

        # Count confirmed runway light faults from alerts
        confirmed_faults = len([
            a for a in alerts
            if a.get("status") == "CONFIRMED" and (a.get("class_name") == "LIGHT OFF" or a.get("event_type") == "RUNWAY_LIGHT_FAULT")
        ])

        current_counts = {
            "navigation": len(nav_dets),
            "fod": len(fod_dets),
            "light_on": len(light_on_dets),
            "light_off": len(light_off_dets),
            "confirmed_faults": confirmed_faults
        }

        # 2. Session Unique Totals (PRD Section 12 & 23)
        session_unique = tracking_service_instance.get_session_unique_counts() if tracking_service_instance else {
            "navigation": len(nav_dets),
            "fod": len(fod_dets),
            "light_on": len(light_on_dets),
            "light_off": len(light_off_dets),
            "total_unique": len(detections)
        }
        session_totals = {
            "navigation": max(session_unique.get("navigation", 0), len(nav_dets)),
            "fod": max(session_unique.get("fod", 0), len(fod_dets)),
            "light_on": max(session_unique.get("light_on", 0), len(light_on_dets)),
            "light_off": max(session_unique.get("light_off", 0), len(light_off_dets)),
            "confirmed_faults": confirmed_faults,
            "total_unique": max(session_unique.get("total_unique", 0), len(detections))
        }

        # 3. Dynamic Classification Breakdown (PRD Section 25)
        breakdown: Dict[str, int] = {}
        for d in detections:
            cname = str(d.get("class_name", "UNKNOWN")).upper()
            breakdown[cname] = breakdown.get(cname, 0) + 1

        # 4. Average Confidence (PRD Section 24)
        if detections:
            avg_conf = float(np.mean([float(d.get("confidence", 0.0)) for d in detections]))
        elif tracking_service_instance:
            avg_conf = tracking_service_instance.get_average_session_confidence()
        else:
            avg_conf = 0.0

        # 5. Performance Metrics (PRD Section 9)
        inf_ms = max(0.1, float(inference_ms))
        inf_fps = round(1000.0 / inf_ms, 1)

        performance = {
            "stream_fps": round(float(stream_fps), 1),
            "inference_fps": inf_fps,
            "inference_ms": round(inf_ms, 1),
            "latency_ms": round(inf_ms, 1)
        }

        # Normalized detection list matching PRD Section 10
        norm_detections = []
        for d in detections:
            bx = d.get("bbox", {})
            if isinstance(bx, dict):
                bbox_dict = {
                    "x1": round(float(bx.get("x1", 0)), 1),
                    "y1": round(float(bx.get("y1", 0)), 1),
                    "x2": round(float(bx.get("x2", 0)), 1),
                    "y2": round(float(bx.get("y2", 0)), 1)
                }
            elif isinstance(bx, (list, tuple)) and len(bx) >= 4:
                bbox_dict = {
                    "x1": round(float(bx[0]), 1),
                    "y1": round(float(bx[1]), 1),
                    "x2": round(float(bx[2]), 1),
                    "y2": round(float(bx[3]), 1)
                }
            else:
                bbox_dict = {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}

            norm_detections.append({
                "model": d.get("model", ""),
                "class_name": d.get("class_name", ""),
                "confidence": round(float(d.get("confidence", 0.0)), 3),
                "bbox": bbox_dict,
                "track_id": d.get("track_id"),
                "state": d.get("state"),
                "inferred": d.get("inferred", False)
            })

        return {
            "type": "detection_update",
            "camera_id": camera_id,
            "session_id": session_id,
            "frame_id": frame_id,
            "timestamp": now_iso,
            "counts": current_counts,
            "session_totals": session_totals,
            "breakdown": breakdown,
            "average_confidence": round(avg_conf, 3),
            "performance": performance,
            "stream_fps": round(float(stream_fps), 1),
            "inference_ms": round(inf_ms, 1),
            "inference_fps": inf_fps,
            "alerts": alerts,
            "detections": norm_detections,
            "total_objects": len(norm_detections)
        }

detection_aggregator = DetectionAggregator()
