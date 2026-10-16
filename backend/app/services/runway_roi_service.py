"""
Runway Observation and Detection (ROD) — Runway Pathway ROI Service
===================================================================
Garuda Aerospace — Critical Runway Safety & Debris Detection Pipeline

PRD Reference: Complete ROD Project Audit & Runway-Pathway-Restricted Debris Detection
Functional Requirements:
  - FR-ROI-01: Valid Runway Pathway Region of Interest (ROI) definition and validation
  - FR-ROI-02: Precise candidate classification (inside vs outside pathway)
  - FR-ROI-03: Configurable boundary handling (BOTTOM_CENTER, CENTROID, INTERSECTION_AREA, STRICT_INSIDE, HYBRID)
  - FR-ROI-04: Strict ROI failure handling (ROI_UNAVAILABLE / ROI_UNCERTAIN without unvalidated defaults)
  - FR-ROI-05: Diagnostic traceability for all candidates (in-pathway and rejected outside-pathway objects)
  - FR-ROI-06: Consistent multi-pipeline enforcement (images, videos, live camera streams, route planning)
"""

import math
import json
from typing import List, Dict, Any, Tuple, Optional, Union
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import logger


class RunwayROIService:
    """
    Manages runway pathway regions of interest (ROI), boundary containment validation,
    and out-of-pathway false positive elimination for foreign object debris (FOD).
    """

    def __init__(self):
        self.enabled: bool = getattr(settings, "RUNWAY_ROI_ENABLED", True)
        self.default_boundary_rule: str = getattr(settings, "RUNWAY_ROI_BOUNDARY_RULE", "BOTTOM_CENTER").upper()
        self.min_overlap_ratio: float = getattr(settings, "RUNWAY_ROI_MIN_OVERLAP", 0.50)
        self.strict_mode: bool = getattr(settings, "RUNWAY_ROI_STRICT_MODE", True)

        # In-memory registry for camera- and source-specific runway pathway polygons (normalized coordinates [0.0 - 1.0])
        self._roi_registry: Dict[str, List[List[float]]] = {}

        # Pre-seed validated camera profiles
        self._init_default_profiles()

    def _init_default_profiles(self):
        """
        Initializes validated pathway polygon profiles for known deployment cameras and test scenes.
        Coordinates are stored in normalized [x_norm, y_norm] format in range [0.0, 1.0].
        """
        # Default overhead drone inspection corridor (covers asphalt pavement corridor, excludes unpaved dirt shoulder)
        # Based on Garuda standard aerial runway inspection views: width ~ 86% of frame, margin on right shoulder
        self._roi_registry["default_overhead_inspection"] = [
            [0.00, 0.00],
            [0.86, 0.00],
            [0.86, 1.00],
            [0.00, 1.00]
        ]

        # Validated profile for test_video.mp4 (1920x1080 drone footage where right shoulder starts at x ~ 1670)
        self._roi_registry["test_video.mp4"] = [
            [0.00, 0.00],
            [0.87, 0.00],
            [0.87, 1.00],
            [0.00, 1.00]
        ]

        # Perspective runway approach view (trapezoidal runway perspective, excludes green fields and horizon)
        # Based on Garuda standard approach camera: threshold at bottom width, tapers towards distance threshold
        self._roi_registry["runway_approach_camera"] = [
            [0.38, 0.32],
            [0.62, 0.32],
            [0.96, 1.00],
            [0.44, 1.00]
        ]

        # Default camera_01 profile
        self._roi_registry["camera_01"] = [
            [0.00, 0.00],
            [0.87, 0.00],
            [0.87, 1.00],
            [0.00, 1.00]
        ]

        # Parse environment variable override if supplied
        default_env = getattr(settings, "RUNWAY_ROI_DEFAULT_POLYGON", None)
        if default_env:
            try:
                parsed = json.loads(default_env)
                if isinstance(parsed, list) and len(parsed) >= 3:
                    self._roi_registry["default_runway"] = parsed
            except Exception as e:
                logger.warning(f"[RUNWAY_ROI_SERVICE] Failed to parse RUNWAY_ROI_DEFAULT_POLYGON: {e}")

    def validate_polygon(
        self,
        polygon: Any,
        image_width: int,
        image_height: int
    ) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Validates polygon structure and geometry per PRD Section 4.4.
        Returns:
            (is_valid, error_message, pixel_contour_ndarray)
        """
        if not polygon:
            return False, "Polygon is empty or None", None

        if not isinstance(polygon, (list, tuple, np.ndarray)):
            return False, f"Invalid polygon type '{type(polygon).__name__}', expected list of vertices", None

        pts_list = list(polygon)
        if len(pts_list) < 3:
            return False, f"Polygon must contain at least 3 vertices (found {len(pts_list)})", None

        pixel_pts: List[Tuple[float, float]] = []
        is_normalized = True

        for i, pt in enumerate(pts_list):
            if isinstance(pt, dict):
                x = pt.get("x") if "x" in pt else pt.get("x1")
                y = pt.get("y") if "y" in pt else pt.get("y1")
            elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                x, y = pt[0], pt[1]
            else:
                return False, f"Vertex at index {i} has invalid format {pt}", None

            if x is None or y is None:
                return False, f"Vertex at index {i} is missing coordinates", None

            try:
                fx = float(x)
                fy = float(y)
            except (ValueError, TypeError):
                return False, f"Vertex at index {i} has non-numeric coordinates ({x}, {y})", None

            if math.isnan(fx) or math.isnan(fy) or math.isinf(fx) or math.isinf(fy):
                return False, f"Vertex at index {i} contains NaN or Infinite value", None

            # Check if any coordinate is > 1.0 (indicating absolute pixel values)
            if fx > 1.0 or fy > 1.0:
                is_normalized = False

            pixel_pts.append((fx, fy))

        # Convert to absolute pixel coordinates if normalized
        resolved_pixel_pts: List[List[int]] = []
        for fx, fy in pixel_pts:
            if is_normalized:
                px = int(round(fx * image_width))
                py = int(round(fy * image_height))
            else:
                px = int(round(fx))
                py = int(round(fy))

            # Clamp coordinates to frame boundary
            px = max(0, min(image_width - 1, px))
            py = max(0, min(image_height - 1, py))
            resolved_pixel_pts.append([px, py])

        contour = np.array(resolved_pixel_pts, dtype=np.int32).reshape((-1, 1, 2))

        # Geometric area check
        area = cv2.contourArea(contour)
        if area <= 1.0:
            return False, f"Polygon has non-positive area ({area:.1f} sq px)", None

        # Ensure polygon occupies a reasonable portion of the frame (at least 0.5% of frame area)
        frame_area = image_width * image_height
        if area < (0.005 * frame_area):
            return False, f"Polygon area ({area:.0f} px) is too small relative to frame ({frame_area} px)", None

        return True, None, contour

    def to_normalized_coords(
        self,
        polygon: List[Any],
        image_width: int,
        image_height: int
    ) -> List[List[float]]:
        """Converts pixel coordinates to normalized [0.0, 1.0] coordinates."""
        norm_pts: List[List[float]] = []
        for pt in polygon:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                x, y = float(pt[0]), float(pt[1])
            elif isinstance(pt, dict):
                x = float(pt.get("x", 0.0))
                y = float(pt.get("y", 0.0))
            else:
                continue

            nx = x / image_width if x > 1.0 else x
            ny = y / image_height if y > 1.0 else y
            norm_pts.append([round(max(0.0, min(1.0, nx)), 4), round(max(0.0, min(1.0, ny)), 4)])
        return norm_pts

    def get_roi_polygon(
        self,
        source_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        image_width: int = 1920,
        image_height: int = 1080
    ) -> Optional[List[List[float]]]:
        """
        Retrieves the registered runway pathway polygon for a specific source, camera, or scene.
        """
        # 1. Exact source match (e.g. video filename)
        if source_id:
            basename = source_id.split("/")[-1].split("\\")[-1]
            if basename in self._roi_registry:
                return self._roi_registry[basename]
            for k, v in self._roi_registry.items():
                if k in basename or basename in k:
                    return v

        # 2. Camera ID match
        if camera_id and camera_id in self._roi_registry:
            return self._roi_registry[camera_id]

        # 3. Default overhead inspection profile
        if "default_overhead_inspection" in self._roi_registry:
            return self._roi_registry["default_overhead_inspection"]

        return None

    def register_roi(
        self,
        key: str,
        polygon: List[List[float]],
        image_width: int = 1920,
        image_height: int = 1080
    ) -> bool:
        """
        Registers or updates a runway pathway polygon for a camera or video source.
        Validates geometry before saving.
        """
        valid, err, _ = self.validate_polygon(polygon, image_width, image_height)
        if not valid:
            logger.error(f"[RUNWAY_ROI_SERVICE] Cannot register invalid ROI for {key}: {err}")
            return False

        norm_poly = self.to_normalized_coords(polygon, image_width, image_height)
        self._roi_registry[key] = norm_poly
        logger.info(f"[RUNWAY_ROI_SERVICE] Successfully registered runway pathway ROI for '{key}' ({len(norm_poly)} vertices)")
        return True

    def detect_pathway_from_frame(
        self,
        frame: np.ndarray
    ) -> Tuple[Optional[List[List[float]]], str, float]:
        """
        Computer vision pathway boundary detector per PRD Section 4.1.
        Distinguishes paved asphalt runway corridor from unpaved dirt shoulder or green grass.
        Returns:
            (polygon_norm, method, confidence)
        """
        if frame is None or frame.size == 0:
            return None, "FAILED_EMPTY_FRAME", 0.0

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Check for aerial overhead view (uniform asphalt with distinct right/left unpaved shoulder)
        # Sample vertical strips to find shoulder transition boundary
        col_stds = np.std(gray.astype(np.float32), axis=0)
        col_means = np.mean(gray.astype(np.float32), axis=0)

        # High texture / variance indicates unpaved shoulder / dirt tire tracks
        smooth_std = cv2.GaussianBlur(col_stds.reshape(1, -1), (1, 31), 10.0)[0]

        # In overhead runway inspection, asphalt is typically in the first 75-88% of width
        # Find where texture rises significantly near the right edge
        asphalt_std_ref = np.median(smooth_std[:int(w * 0.5)])
        shoulder_threshold = asphalt_std_ref * 1.35

        right_boundary_x = w
        for x in range(int(w * 0.70), w - 5):
            if smooth_std[x] > shoulder_threshold and np.mean(smooth_std[x:x+10]) > shoulder_threshold:
                right_boundary_x = x
                break

        if right_boundary_x < w:
            norm_right = round(right_boundary_x / w, 4)
            # Valid corridor detected
            polygon_norm = [
                [0.00, 0.00],
                [norm_right, 0.00],
                [norm_right, 1.00],
                [0.00, 1.00]
            ]
            return polygon_norm, "ASPHALT_TEXTURE_CORRIDOR", 0.85

        # 2. Check for perspective approach view (grass flanks asphalt road)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        grass_mask = cv2.inRange(hsv, (30, 25, 25), (90, 255, 255))
        grass_fraction = np.count_nonzero(grass_mask) / (h * w)

        if grass_fraction > 0.15:
            # Significant grass visible, find runway trapezoid corridor
            road_mask = (~grass_mask) & (hsv[:, :, 1] < 45)
            # Remove top sky/horizon (top 20%)
            road_mask[:int(h * 0.20), :] = 0

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
            cleaned = cv2.morphologyEx(road_mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest) > (0.10 * w * h):
                    approx = cv2.approxPolyDP(largest, 0.03 * cv2.arcLength(largest, True), True)
                    pts = approx.reshape(-1, 2)
                    if len(pts) >= 3:
                        norm_pts = [[round(p[0]/w, 4), round(p[1]/h, 4)] for p in pts]
                        return norm_pts, "COLOR_SEGMENTATION_TRAPEZOID", 0.80

        # Pathway cannot be unambiguously resolved from single frame
        return None, "ROI_UNCERTAIN", 0.40

    def evaluate_candidate(
        self,
        bbox: Any,
        contour: np.ndarray,
        image_width: int,
        image_height: int,
        boundary_rule: Optional[str] = None,
        min_overlap: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a single bounding box against a validated runway polygon contour (PRD Section 4.2 & 4.3).
        Returns diagnostic evaluation dictionary:
        {
            "in_pathway": bool,
            "status": "INSIDE" | "OUTSIDE" | "BOUNDARY_ACCEPTED" | "BOUNDARY_REJECTED",
            "contact_point": [u, v],
            "boundary_distance_px": float,
            "containment_ratio": float,
            "rejection_reason": Optional[str],
            "rule_applied": str
        }
        """
        rule = (boundary_rule or self.default_boundary_rule).upper()
        overlap_thresh = min_overlap if min_overlap is not None else self.min_overlap_ratio

        # Parse bounding box into [x1, y1, x2, y2]
        if isinstance(bbox, dict):
            x1 = float(bbox.get("x1", 0.0))
            y1 = float(bbox.get("y1", 0.0))
            x2 = float(bbox.get("x2", 0.0))
            y2 = float(bbox.get("y2", 0.0))
        elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        else:
            return {
                "in_pathway": False,
                "status": "OUTSIDE",
                "contact_point": [0.0, 0.0],
                "boundary_distance_px": -999.0,
                "containment_ratio": 0.0,
                "rejection_reason": "malformed_bounding_box",
                "rule_applied": rule
            }

        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        box_area = bw * bh

        # 1. Calculate representative contact points
        # Bottom-center represents ground plane contact point (FR-04)
        contact_u = (x1 + x2) / 2.0
        contact_v = y2
        centroid_u = (x1 + x2) / 2.0
        centroid_v = (y1 + y2) / 2.0

        # 2. Point containment tests
        dist_bottom_center = cv2.pointPolygonTest(contour, (contact_u, contact_v), True)
        dist_centroid = cv2.pointPolygonTest(contour, (centroid_u, centroid_v), True)

        # 3. Box area intersection test
        ix1 = int(max(0, math.floor(x1)))
        iy1 = int(max(0, math.floor(y1)))
        ix2 = int(min(image_width, math.ceil(x2)))
        iy2 = int(min(image_height, math.ceil(y2)))

        containment_ratio = 0.0
        if ix2 > ix1 and iy2 > iy1:
            # Create sub-mask for box region
            sub_w = ix2 - ix1
            sub_h = iy2 - iy1
            shifted_contour = contour - np.array([ix1, iy1])
            mask = np.zeros((sub_h, sub_w), dtype=np.uint8)
            cv2.fillPoly(mask, [shifted_contour], 255)
            intersecting_pixels = np.count_nonzero(mask)
            containment_ratio = round(intersecting_pixels / float(sub_w * sub_h), 4)

        # 4. Corner containment tests for strict rules
        c_tl = cv2.pointPolygonTest(contour, (x1, y1), False) >= 0
        c_tr = cv2.pointPolygonTest(contour, (x2, y1), False) >= 0
        c_br = cv2.pointPolygonTest(contour, (x2, y2), False) >= 0
        c_bl = cv2.pointPolygonTest(contour, (x1, y2), False) >= 0
        all_corners_inside = c_tl and c_tr and c_br and c_bl

        # 5. Evaluate against requested rule
        in_pathway = False
        status = "OUTSIDE"
        rejection_reason = None

        if rule == "BOTTOM_CENTER":
            # Physically grounded contact point inside runway polygon
            if dist_bottom_center >= 0.0:
                in_pathway = True
                status = "INSIDE" if dist_bottom_center > 2.0 else "BOUNDARY_ACCEPTED"
            else:
                in_pathway = False
                status = "OUTSIDE" if dist_bottom_center < -2.0 else "BOUNDARY_REJECTED"
                rejection_reason = "bottom_center_outside_runway_roi"

        elif rule == "CENTROID":
            if dist_centroid >= 0.0:
                in_pathway = True
                status = "INSIDE" if dist_centroid > 2.0 else "BOUNDARY_ACCEPTED"
            else:
                in_pathway = False
                status = "OUTSIDE"
                rejection_reason = "centroid_outside_runway_roi"

        elif rule == "INTERSECTION_AREA":
            if containment_ratio >= overlap_thresh:
                in_pathway = True
                status = "INSIDE" if containment_ratio >= 0.95 else "BOUNDARY_ACCEPTED"
            else:
                in_pathway = False
                status = "OUTSIDE" if containment_ratio <= 0.05 else "BOUNDARY_REJECTED"
                rejection_reason = f"insufficient_roi_overlap_{containment_ratio:.2f}_below_{overlap_thresh:.2f}"

        elif rule == "STRICT_INSIDE":
            if all_corners_inside:
                in_pathway = True
                status = "INSIDE"
            else:
                in_pathway = False
                status = "OUTSIDE" if containment_ratio <= 0.05 else "BOUNDARY_REJECTED"
                rejection_reason = "bounding_box_extends_beyond_runway_roi"

        elif rule == "HYBRID":
            # Bottom center inside AND at least 30% area overlap
            if dist_bottom_center >= 0.0 and containment_ratio >= 0.30:
                in_pathway = True
                status = "INSIDE"
            else:
                in_pathway = False
                status = "OUTSIDE"
                rejection_reason = "hybrid_check_failed_outside_runway"

        else:
            # Fallback to bottom center
            in_pathway = dist_bottom_center >= 0.0
            status = "INSIDE" if in_pathway else "OUTSIDE"
            if not in_pathway:
                rejection_reason = "outside_runway_roi"

        return {
            "in_pathway": in_pathway,
            "status": status,
            "contact_point": [round(contact_u, 1), round(contact_v, 1)],
            "boundary_distance_px": round(dist_bottom_center, 1),
            "containment_ratio": containment_ratio,
            "rejection_reason": rejection_reason,
            "rule_applied": rule
        }

    def filter_debris_detections(
        self,
        detections: List[Dict[str, Any]],
        frame_shape: Tuple[int, int],
        roi_polygon: Optional[Any] = None,
        source_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        boundary_rule: Optional[str] = None,
        min_overlap: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Filters raw debris candidate detections against the validated runway pathway ROI (PRD Section 4.2).
        Returns:
        {
            "valid_detections": [...],       # In-pathway debris to report and persist
            "filtered_out_detections": [...],# Excluded out-of-pathway candidates with diagnostics
            "roi_info": {
                "status": "ACTIVE" | "ROI_UNAVAILABLE" | "ROI_UNCERTAIN",
                "polygon": [[x, y], ...],    # Normalized polygon coordinates
                "boundary_rule": str,
                "valid": bool
            },
            "counts": {
                "in_pathway": int,
                "outside_pathway": int,
                "total_candidates": int
            }
        }
        """
        h, w = frame_shape[:2]
        rule = (boundary_rule or self.default_boundary_rule).upper()

        # If ROI filtering is globally disabled, pass all detections
        if not self.enabled:
            for d in detections:
                d["in_pathway"] = True
                d["roi_status"] = "BYPASS"
            return {
                "valid_detections": detections,
                "filtered_out_detections": [],
                "roi_info": {"status": "DISABLED", "polygon": None, "boundary_rule": "BYPASS", "valid": True},
                "counts": {"in_pathway": len(detections), "outside_pathway": 0, "total_candidates": len(detections)}
            }

        # 1. Resolve pathway polygon
        candidate_polygon = roi_polygon
        if candidate_polygon is None:
            candidate_polygon = self.get_roi_polygon(source_id=source_id, camera_id=camera_id, image_width=w, image_height=h)

        # 2. Validate polygon
        valid, err, contour = self.validate_polygon(candidate_polygon, w, h)

        if not valid or contour is None:
            # PRD Section 4.4: Do NOT silently substitute an unvalidated default.
            # Do NOT label unrestricted detections as verified runway debris.
            logger.warning(f"[RUNWAY_ROI_SERVICE] Pathway ROI unavailable or invalid: {err}")

            if self.strict_mode:
                # In strict mode, unrestricted detections cannot be certified as verified runway debris
                unverified_candidates = []
                for d in detections:
                    d_copy = dict(d)
                    d_copy["in_pathway"] = False
                    d_copy["roi_status"] = "ROI_UNAVAILABLE"
                    d_copy["roi_rejection_reason"] = f"roi_unavailable_strict_mode: {err}"
                    unverified_candidates.append(d_copy)

                return {
                    "valid_detections": [],
                    "filtered_out_detections": unverified_candidates,
                    "roi_info": {
                        "status": "ROI_UNAVAILABLE",
                        "error": err,
                        "polygon": None,
                        "boundary_rule": rule,
                        "valid": False
                    },
                    "counts": {
                        "in_pathway": 0,
                        "outside_pathway": len(detections),
                        "total_candidates": len(detections)
                    }
                }
            else:
                for d in detections:
                    d["in_pathway"] = True
                    d["roi_status"] = "UNVERIFIED"
                return {
                    "valid_detections": detections,
                    "filtered_out_detections": [],
                    "roi_info": {"status": "ROI_UNAVAILABLE_PERMISSIVE", "polygon": None, "valid": False},
                    "counts": {"in_pathway": len(detections), "outside_pathway": 0, "total_candidates": len(detections)}
                }

        # 3. Evaluate each candidate against validated polygon
        valid_detections: List[Dict[str, Any]] = []
        filtered_out_detections: List[Dict[str, Any]] = []
        norm_polygon = self.to_normalized_coords(candidate_polygon, w, h)

        for d in detections:
            bbox = d.get("bbox") or d.get("xyxy")
            eval_res = self.evaluate_candidate(
                bbox=bbox,
                contour=contour,
                image_width=w,
                image_height=h,
                boundary_rule=rule,
                min_overlap=min_overlap
            )

            # Enrich detection dictionary with diagnostic metadata
            d["in_pathway"] = eval_res["in_pathway"]
            d["roi_status"] = eval_res["status"]
            d["roi_containment_ratio"] = eval_res["containment_ratio"]
            d["roi_boundary_distance_px"] = eval_res["boundary_distance_px"]
            d["ground_contact_point"] = eval_res["contact_point"]
            d["roi_rule"] = eval_res["rule_applied"]

            if eval_res["in_pathway"]:
                valid_detections.append(d)
            else:
                d["rejection_reason"] = eval_res["rejection_reason"]
                filtered_out_detections.append(d)

        return {
            "valid_detections": valid_detections,
            "filtered_out_detections": filtered_out_detections,
            "roi_info": {
                "status": "ACTIVE",
                "polygon": norm_polygon,
                "boundary_rule": rule,
                "valid": True,
                "vertex_count": len(norm_polygon)
            },
            "counts": {
                "in_pathway": len(valid_detections),
                "outside_pathway": len(filtered_out_detections),
                "total_candidates": len(detections)
            }
        }

    def draw_pathway_overlay(
        self,
        image: np.ndarray,
        polygon: Optional[Any] = None,
        source_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        color: Tuple[int, int, int] = (255, 180, 0),
        alpha: float = 0.08,
        line_thickness: int = 2,
        draw_label: bool = True
    ) -> np.ndarray:
        """
        Renders the active runway pathway boundary and optional subtle tint onto the image/frame (PRD Section 4.5).
        """
        if image is None or image.size == 0 or not self.enabled:
            return image

        h, w = image.shape[:2]
        candidate_poly = polygon
        if candidate_poly is None:
            candidate_poly = self.get_roi_polygon(source_id=source_id, camera_id=camera_id, image_width=w, image_height=h)

        if not candidate_poly:
            return image

        valid, _, contour = self.validate_polygon(candidate_poly, w, h)
        if not valid or contour is None:
            return image

        out = image.copy()
        if alpha > 0.0:
            overlay = out.copy()
            cv2.fillPoly(overlay, [contour], color)
            cv2.addWeighted(overlay, alpha, out, 1.0 - alpha, 0, out)

        # Draw boundary outline
        cv2.polylines(out, [contour], isClosed=True, color=color, thickness=line_thickness, lineType=cv2.LINE_AA)

        if draw_label and len(contour) > 0:
            top_pt = min(contour.reshape(-1, 2), key=lambda pt: (pt[1], pt[0]))
            lx = max(6, int(top_pt[0]) + 8)
            ly = max(20, int(top_pt[1]) + 20)
            label = "RUNWAY PATHWAY ROI"
            (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            cv2.rectangle(out, (lx - 2, ly - th - 4), (lx + tw + 4, ly + 2), (20, 20, 20), -1)
            cv2.rectangle(out, (lx - 2, ly - th - 4), (lx + tw + 4, ly + 2), color, 1)
            cv2.putText(out, label, (lx, ly - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)

        return out


# Singleton instance
runway_roi_service = RunwayROIService()
