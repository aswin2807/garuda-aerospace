import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.alert import AlertItem

class AlertService:
    """
    Manages event generation, FOD alerts, and temporal confirmation for Runway Light faults.
    PRD Section 16, 17, 18, 32, 33
    """
    def __init__(self):
        self.confirm_threshold_frames: int = settings.LIGHT_FAULT_CONFIRM_FRAMES
        # Tracks consecutive frames per camera or global
        self._consecutive_light_off: Dict[str, int] = {}
        self._consecutive_fod: Dict[str, int] = {}
        self._active_alerts: Dict[str, List[Dict[str, Any]]] = {}

    def process_frame_detections(
        self,
        detections: List[Dict[str, Any]],
        camera_id: str = "drone-camera-01"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Processes frame detections and generates alerts based on temporal logic.
        Returns:
            (active_alerts, counts_dict)
        """
        nav_detections = [d for d in detections if d.get("model") == "navigation"]
        fod_detections = [d for d in detections if d.get("class_name", "").upper() == "FOD"]
        light_off_direct = [
            d for d in detections
            if d.get("class_name", "").upper() in ("LIGHT OFF", "OFF") and not d.get("inferred", False)
        ]
        light_off_gap = [
            d for d in detections
            if d.get("state") == "OFF-GAP" or d.get("inferred", False)
        ]
        light_off_all = light_off_direct + light_off_gap
        light_on_detections = [
            d for d in detections
            if d.get("class_name", "").upper() in ("LIGHT ON", "ON")
        ]

        now_str = datetime.now(timezone.utc).isoformat()
        alerts: List[Dict[str, Any]] = []

        # 1. Direct Runway Light Fault Temporal Logic (Section 16, 17, 33)
        if light_off_direct:
            self._consecutive_light_off[camera_id] = self._consecutive_light_off.get(camera_id, 0) + 1
            consec = self._consecutive_light_off[camera_id]
            is_confirmed = consec >= self.confirm_threshold_frames
            status_str = "CONFIRMED" if is_confirmed else "POTENTIAL"
            max_conf = max([d.get("confidence", 0.0) for d in light_off_direct])
            sample_bbox = light_off_direct[0].get("bbox")
            track_id = light_off_direct[0].get("track_id")

            alert = {
                "event_type": "RUNWAY_LIGHT_FAULT",
                "severity": "HIGH",
                "class_name": "LIGHT OFF",
                "confidence": round(float(max_conf), 3),
                "status": status_str,
                "consecutive_frames": consec,
                "track_id": track_id,
                "timestamp": now_str,
                "bbox": sample_bbox,
                "message": (
                    f"CONFIRMED RUNWAY LIGHT FAULT ({consec} consecutive frames)"
                    if is_confirmed
                    else f"Potential Runway Light Fault detected ({consec}/{self.confirm_threshold_frames} frames)"
                )
            }
            alerts.append(alert)
        else:
            self._consecutive_light_off[camera_id] = 0

        # 2. Inferred Gap Fault Alert (PRD Section 18 & 32)
        if light_off_gap:
            max_gap_conf = max([d.get("confidence", 0.0) for d in light_off_gap])
            alerts.append({
                "event_type": "POSSIBLE_RUNWAY_LIGHT_FAULT",
                "severity": "WARNING",
                "class_name": "LIGHT OFF",
                "state": "OFF-GAP",
                "confidence": round(float(max_gap_conf), 3),
                "status": "POTENTIAL",
                "consecutive_frames": 1,
                "timestamp": now_str,
                "bbox": light_off_gap[0].get("bbox"),
                "message": f"POSSIBLE RUNWAY LIGHT FAULT (Inferred OFF-GAP in light row)"
            })

        # 3. FOD Alert Logic (PRD Section 18 & 32)
        if fod_detections:
            self._consecutive_fod[camera_id] = self._consecutive_fod.get(camera_id, 0) + 1
            max_conf = max([d.get("confidence", 0.0) for d in fod_detections])
            sample_bbox = fod_detections[0].get("bbox")

            alert = {
                "event_type": "FOD_DETECTED",
                "severity": "CRITICAL",
                "class_name": "FOD",
                "confidence": round(float(max_conf), 3),
                "status": "CONFIRMED",
                "consecutive_frames": self._consecutive_fod[camera_id],
                "timestamp": now_str,
                "bbox": sample_bbox,
                "message": f"Foreign Object Debris detected on runway (Confidence: {max_conf:.0%})"
            }
            alerts.append(alert)
        else:
            self._consecutive_fod[camera_id] = 0

        counts = {
            "nav_count": len(nav_detections),
            "fod_count": len(fod_detections),
            "light_on_count": len(light_on_detections),
            "light_off_count": len(light_off_all),
            "light_off_gap_count": len(light_off_gap),
            "total_detections": len(detections)
        }

        self._active_alerts[camera_id] = alerts
        return alerts, counts

    def create_system_alert(self, event_type: str, message: str, severity: str = "HIGH", camera_id: str = "drone-camera-01") -> Dict[str, Any]:
        """Creates a system alert such as CAMERA DISCONNECTED or AI MODEL ERROR (PRD Section 32)."""
        alert = {
            "event_type": event_type,
            "severity": severity,
            "status": "CONFIRMED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message
        }
        if camera_id not in self._active_alerts:
            self._active_alerts[camera_id] = []
        self._active_alerts[camera_id].insert(0, alert)
        return alert

    def get_active_alerts(self, camera_id: str = "drone-camera-01") -> List[Dict[str, Any]]:
        return self._active_alerts.get(camera_id, [])


alert_service = AlertService()
