from typing import List, Dict, Any, Optional, Set, Tuple
import numpy as np

def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    """
    Computes Intersection-over-Union between two boxes [x1, y1, x2, y2]
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interW = max(0.0, xB - xA)
    interH = max(0.0, yB - yA)
    interArea = interW * interH

    boxAArea = max(0.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(0.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    union = boxAArea + boxBArea - interArea

    return interArea / union if union > 0 else 0.0

class TrackedItem:
    def __init__(self, track_id: int, model: str, class_name: str, bbox: List[float], conf: float, frame_id: int):
        self.track_id: int = track_id
        self.model: str = model
        self.class_name: str = class_name
        self.bbox: List[float] = bbox
        self.confidence: float = conf
        self.first_frame: int = frame_id
        self.last_frame: int = frame_id
        self.hits: int = 1
        self.missed_frames: int = 0
        self.confidences: List[float] = [conf]

    def update(self, bbox: List[float], conf: float, frame_id: int):
        self.bbox = bbox
        self.confidence = conf
        self.last_frame = frame_id
        self.hits += 1
        self.missed_frames = 0
        self.confidences.append(conf)

class ObjectTracker:
    """
    Multi-model real-time object tracker (ByteTrackLite / IoU Association).
    Assigns persistent track_id per object across frames and maintains session
    unique object event counts per PRD Section 12, 13, 23.
    """
    def __init__(self, iou_thresh: float = 0.25, max_missed: int = 20, max_disappeared: Optional[int] = None):
        if max_disappeared is not None:
            max_missed = max_disappeared
        self.iou_thresh = iou_thresh
        self.max_missed = max_missed
        self._next_track_id: int = 1
        self.active_tracks: Dict[int, TrackedItem] = {}

        # Unique tracks observed in the entire session (PRD Section 12 & 23)
        self.session_unique_nav: Set[int] = set()
        self.session_unique_fod: Set[int] = set()
        self.session_unique_light_on: Set[int] = set()
        self.session_unique_light_off: Set[int] = set()
        self.all_session_confidences: List[float] = []

    def reset_session(self):
        """
        Resets active tracks and session unique counters for a new video/stream (PRD Section 40)
        """
        self._next_track_id = 1
        self.active_tracks.clear()
        self.session_unique_nav.clear()
        self.session_unique_fod.clear()
        self.session_unique_light_on.clear()
        self.session_unique_light_off.clear()
        self.all_session_confidences.clear()

    def _extract_box(self, d: Dict[str, Any]) -> List[float]:
        bx = d.get("bbox", {})
        if isinstance(bx, dict):
            return [float(bx.get("x1", 0)), float(bx.get("y1", 0)), float(bx.get("x2", 0)), float(bx.get("y2", 0))]
        elif isinstance(bx, (list, tuple)) and len(bx) >= 4:
            return [float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])]
        return [0.0, 0.0, 1.0, 1.0]

    def update(self, detections: List[Dict[str, Any]], frame_id: int = 0, frame_idx: Optional[int] = None) -> List[Dict[str, Any]]:
        if frame_idx is not None:
            frame_id = frame_idx
        """
        Associates incoming detections with existing tracks and assigns track_ids.
        """
        # If detection already has a runway track_id (from ByteTrackLite in runway_light_service), preserve it
        tracked_results: List[Dict[str, Any]] = []
        unmatched_dets = []

        for det in detections:
            conf = float(det.get("confidence", 0.0))
            self.all_session_confidences.append(conf)

            # If runway service already provided a track ID
            if det.get("track_id") is not None:
                tid = int(det["track_id"])
                tracked_results.append(det)
                self._record_session_track(det.get("model", ""), det.get("class_name", ""), tid)
            else:
                unmatched_dets.append(det)

        import math

        # Match remaining detections with active tracks using combined IoU and centroid proximity
        candidates = []
        for det_idx, det in enumerate(unmatched_dets):
            det_box = self._extract_box(det)
            model_name = det.get("model", "")
            cls_name = det.get("class_name", "").upper()

            cx_det = (det_box[0] + det_box[2]) / 2.0
            cy_det = (det_box[1] + det_box[3]) / 2.0
            w_det = max(1.0, det_box[2] - det_box[0])
            h_det = max(1.0, det_box[3] - det_box[1])
            area_det = w_det * h_det

            for tid, trk in self.active_tracks.items():
                if trk.model != model_name or trk.class_name != cls_name:
                    continue

                iou = calculate_iou(det_box, trk.bbox)

                cx_trk = (trk.bbox[0] + trk.bbox[2]) / 2.0
                cy_trk = (trk.bbox[1] + trk.bbox[3]) / 2.0
                dist = math.hypot(cx_det - cx_trk, cy_det - cy_trk)

                w_trk = max(1.0, trk.bbox[2] - trk.bbox[0])
                h_trk = max(1.0, trk.bbox[3] - trk.bbox[1])
                area_trk = w_trk * h_trk
                area_ratio = area_det / max(1.0, area_trk)

                delta_frames = max(1, frame_id - trk.last_frame)
                max_dist = max(50.0, max(w_trk, h_trk) * 2.5) * min(3.0, 1.0 + (delta_frames - 1) * 0.4)

                dist_score = 0.0
                if 0.25 <= area_ratio <= 4.0 and dist <= max_dist:
                    dist_score = max(0.0, 1.0 - (dist / max_dist)) * 0.65

                match_score = max(iou, dist_score)
                if match_score >= 0.15:
                    candidates.append((match_score, det_idx, tid))

        # Sort candidates descending by match score
        candidates.sort(key=lambda x: x[0], reverse=True)

        matched_dets = set()
        matched_track_ids = set()

        for score, det_idx, tid in candidates:
            if det_idx in matched_dets or tid in matched_track_ids:
                continue

            det = unmatched_dets[det_idx]
            det_box = self._extract_box(det)
            conf = float(det.get("confidence", 0.0))

            self.active_tracks[tid].update(det_box, conf, frame_id)
            det["track_id"] = tid
            self._record_session_track(det.get("model", ""), det.get("class_name", ""), tid)
            tracked_results.append(det)

            matched_dets.add(det_idx)
            matched_track_ids.add(tid)

        # Create new tracks for unmatched detections
        for det_idx, det in enumerate(unmatched_dets):
            if det_idx in matched_dets:
                continue

            det_box = self._extract_box(det)
            conf = float(det.get("confidence", 0.0))
            model_name = det.get("model", "")
            cls_name = det.get("class_name", "").upper()

            tid = self._next_track_id
            self._next_track_id += 1
            self.active_tracks[tid] = TrackedItem(tid, model_name, cls_name, det_box, conf, frame_id)
            det["track_id"] = tid
            self._record_session_track(model_name, cls_name, tid)
            tracked_results.append(det)
            matched_track_ids.add(tid)

        # Update missed frames for unobserved tracks
        dead_tracks = []
        for tid, trk in self.active_tracks.items():
            if tid not in matched_track_ids:
                trk.missed_frames += 1
                if trk.missed_frames > self.max_missed:
                    dead_tracks.append(tid)

        for tid in dead_tracks:
            del self.active_tracks[tid]

        return detections

    def _record_session_track(self, model: str, class_name: str, track_id: int):
        c_up = class_name.upper()
        if "FOD" in c_up or model == "fod":
            self.session_unique_fod.add(track_id)
        elif "LIGHT OFF" in c_up or c_up == "OFF":
            self.session_unique_light_off.add(track_id)
        elif "LIGHT ON" in c_up or c_up == "ON":
            self.session_unique_light_on.add(track_id)
        elif model == "navigation" or "NAV" in c_up:
            self.session_unique_nav.add(track_id)

    def get_session_unique_counts(self) -> Dict[str, int]:
        return {
            "navigation": len(self.session_unique_nav),
            "fod": len(self.session_unique_fod),
            "light_on": len(self.session_unique_light_on),
            "light_off": len(self.session_unique_light_off),
            "total_unique": len(self.session_unique_nav | self.session_unique_fod | self.session_unique_light_on | self.session_unique_light_off)
        }

    def get_average_session_confidence(self) -> float:
        if not self.all_session_confidences:
            return 0.0
        return float(np.mean(self.all_session_confidences))

tracking_service = ObjectTracker()
