import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import cv2
import numpy as np

from backend.app.core.logging import logger
from backend.app.services.navigation_service import navigation_service
from backend.app.services.fod_service import fod_service
from backend.app.services.runway_light_service import runway_light_service
from backend.app.services.debris_coordinate_service import debris_coordinate_service
from backend.app.services.runway_roi_service import runway_roi_service

RESULTS_DIR = Path(os.getcwd()) / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CLASS_COLORS = {
    "NAVIGATION": (255, 200, 0),    # Cyan/Yellow in BGR
    "FOD": (0, 0, 255),             # Red
    "LIGHT ON": (94, 197, 34),      # Emerald Green in BGR (RGB: 34, 197, 94)
    "LIGHT OFF": (68, 68, 239),     # Coral Red in BGR (RGB: 239, 68, 68)
}

class ImageService:
    """
    Image Analysis Service (PRD Section 5 & 34).
    Analyzes static images using the 3 real YOLO models:
    navigation_best.pt, FOD_Karhtikeyan.pt, and runway_light_best.pt.
    Enforces Runway Pathway ROI filtering for FOD debris detections.
    Generates annotated images and real counts with zero random or simulated values.
    """
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or RESULTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_image(
        self,
        image_path: str,
        job_id: Optional[str] = None,
        analysis_type: str = "NAVIGATION",
        conf_threshold: float = 0.20,
        telemetry: Optional[Dict[str, Any]] = None,
        roi_polygon: Optional[Any] = None,
        boundary_rule: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes model-specific AI inference on an uploaded image.
        Strictly isolates Navigation, FOD, and Runway Light models.
        Enforces Runway Pathway ROI filtering for FOD debris.
        """
        t0 = time.time()
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image file at {image_path}")

        h, w = img.shape[:2]
        all_detections: List[Dict[str, Any]] = []
        target_type = (analysis_type or "NAVIGATION").upper()

        # 1. Navigation Model ONLY
        if target_type in ("NAVIGATION", "ALL") and navigation_service.loaded:
            try:
                nav_dets = navigation_service.predict(img, conf_threshold=conf_threshold)
                for d in nav_dets:
                    d["model_name"] = "navigation"
                    d["analysis_type"] = "NAVIGATION"
                    all_detections.append(d)
            except Exception as e:
                logger.error(f"[IMAGE_SERVICE] Navigation inference error: {e}")

        # 2. FOD Model ONLY (Enforcing Runway Pathway ROI Filtering)
        elif target_type in ("FOD", "FOD_DEBRIS", "ALL") and fod_service.loaded:
            try:
                fod_dets = fod_service.predict(
                    img,
                    conf=conf_threshold,
                    filter_pathway=True,
                    roi_polygon=roi_polygon,
                    source_id=image_path,
                    boundary_rule=boundary_rule
                )
                for d in fod_dets:
                    d["model_name"] = "fod"
                    d["analysis_type"] = "FOD"
                    # Calculate debris coordinates (FR-03, FR-04, FR-05)
                    coords = debris_coordinate_service.predict_coordinates(
                        bbox=d.get("bbox") or d.get("xyxy"),
                        image_width=w,
                        image_height=h,
                        telemetry=telemetry
                    )
                    d["debris_coordinates"] = coords
                    d["latitude"] = coords.get("latitude")
                    d["longitude"] = coords.get("longitude")
                    d["coordinate_uncertainty_m"] = coords.get("uncertainty_m")
                    d["coordinate_status"] = coords.get("status")
                    d["coordinate_method"] = coords.get("method")
                    d["coordinate_formatted"] = coords.get("formatted")
                    all_detections.append(d)
            except Exception as e:
                logger.error(f"[IMAGE_SERVICE] FOD inference error: {e}")

        # 3. Runway Light Model ONLY
        elif target_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") and runway_light_service.loaded:
            try:
                light_dets = runway_light_service.predict(img, conf=conf_threshold, force_detect=True)
                for d in light_dets:
                    d["model_name"] = "runway_light"
                    d["analysis_type"] = "RUNWAY_LIGHT"
                    all_detections.append(d)
            except Exception as e:
                logger.error(f"[IMAGE_SERVICE] Runway Light inference error: {e}")

        # Calculate Real Counts strictly isolated per target_type (PRD Section 4 & 6)
        nav_count = sum(1 for d in all_detections if d.get("model_name") == "navigation")
        fod_count = sum(1 for d in all_detections if d.get("model_name") == "fod" or "FOD" in str(d.get("class_name", "")).upper())
        light_on_count = sum(1 for d in all_detections if d.get("class_name") == "LIGHT ON" or d.get("state") == "ON")
        light_off_count = sum(1 for d in all_detections if d.get("class_name") == "LIGHT OFF" or d.get("state") in ("OFF", "OFF-GAP"))

        counts = {
            "navigation": nav_count if target_type in ("NAVIGATION", "ALL") else 0,
            "fod": fod_count if target_type in ("FOD", "FOD_DEBRIS", "ALL") else 0,
            "light_on": light_on_count if target_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
            "light_off": light_off_count if target_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
            "confirmed_faults": light_off_count if target_type in ("RUNWAY_LIGHT", "RUNWAY", "ALL") else 0,
        }

        # Draw Annotations onto Image
        annotated_img = img.copy()

        # If FOD analysis, draw Runway Pathway ROI boundary & rejected candidates
        roi_info = None
        outside_pathway_candidates: List[Dict[str, Any]] = []
        if target_type in ("FOD", "FOD_DEBRIS", "ALL") and hasattr(fod_service, "last_roi_result") and fod_service.last_roi_result:
            last_res = fod_service.last_roi_result
            roi_info = last_res.get("roi_info")
            outside_pathway_candidates = last_res.get("filtered_out_detections", [])
            poly = (roi_info or {}).get("polygon")
            if poly:
                annotated_img = runway_roi_service.draw_pathway_overlay(
                    annotated_img,
                    polygon=poly,
                    color=(255, 180, 0),
                    alpha=0.08,
                    draw_label=True
                )

            # Draw rejected outside-pathway candidates in muted grey/slate styling
            for rej in outside_pathway_candidates:
                bx = rej.get("bbox") or rej.get("xyxy") or [0, 0, 0, 0]
                if isinstance(bx, (list, tuple)) and len(bx) >= 4:
                    rx1, ry1, rx2, ry2 = [int(round(v)) for v in bx[:4]]
                elif isinstance(bx, dict):
                    rx1 = int(round(bx.get("x1", 0)))
                    ry1 = int(round(bx.get("y1", 0)))
                    rx2 = int(round(bx.get("x2", 0)))
                    ry2 = int(round(bx.get("y2", 0)))
                else:
                    continue

                cv2.rectangle(annotated_img, (rx1, ry1), (rx2, ry2), (120, 120, 140), 1, cv2.LINE_AA)
                conf_pct = int(round(float(rej.get("confidence", 0.0)) * 100))
                rej_lbl = f"OUTSIDE ROI · {conf_pct}%"
                (tw, th), _ = cv2.getTextSize(rej_lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                cv2.rectangle(annotated_img, (rx1, max(0, ry1 - th - 4)), (rx1 + tw + 4, ry1), (40, 40, 50), -1)
                cv2.putText(annotated_img, rej_lbl, (rx1 + 2, ry1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 190), 1, cv2.LINE_AA)

        # Draw verified in-pathway detections
        for d in all_detections:
            x1, y1, x2, y2 = 0, 0, 0, 0
            if "bbox" in d:
                bx = d["bbox"]
                if isinstance(bx, (list, tuple)) and len(bx) >= 4:
                    x1, y1, x2, y2 = [int(round(v)) for v in bx[:4]]
                elif isinstance(bx, dict):
                    x1 = int(round(bx.get("x1", 0)))
                    y1 = int(round(bx.get("y1", 0)))
                    x2 = int(round(bx.get("x2", 0)))
                    y2 = int(round(bx.get("y2", 0)))
            elif "xyxy" in d and len(d["xyxy"]) >= 4:
                x1, y1, x2, y2 = [int(round(v)) for v in d["xyxy"][:4]]

            cls_name = str(d.get("class_name", "OBJECT")).upper()
            color = (0, 255, 255)
            for k, c in CLASS_COLORS.items():
                if k in cls_name:
                    color = c
                    break

            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
            conf_val = float(d.get("display_conf", d.get("conf", d.get("confidence", 0.0))))
            conf_pct = int(round(conf_val * 100))
            label = f"{cls_name} — {conf_pct}%"
            (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated_img, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), color, -1)
            cv2.putText(annotated_img, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Save annotated image
        stem = Path(image_path).stem
        ext = Path(image_path).suffix or ".jpg"
        out_filename = f"annotated_{stem}{ext}"
        out_path = self.output_dir / out_filename
        cv2.imwrite(str(out_path), annotated_img)

        elapsed_ms = round((time.time() - t0) * 1000.0, 1)
        logger.info(f"[IMAGE_SERVICE] Analyzed {image_path}: {len(all_detections)} detections in {elapsed_ms}ms")

        return {
            "image_path": image_path,
            "annotated_image_path": str(out_path),
            "detections": all_detections,
            "counts": counts,
            "processing_time_ms": elapsed_ms,
            "width": w,
            "height": h,
            "roi_info": roi_info,
            "outside_pathway_candidates": outside_pathway_candidates,
            "pathway_filtered_count": len(outside_pathway_candidates),
        }

image_service = ImageService()
