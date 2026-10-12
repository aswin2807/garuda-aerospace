import io
import os
import glob
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import cv2
import torch
import numpy as np
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.navigation_service import navigation_service, NavigationService
from backend.app.services.fod_service import fod_service, FODService
from backend.app.services.runway_light_service import runway_light_service, RunwayLightService
from backend.app.services.alert_service import alert_service
from backend.app.services.model_verifier import model_verifier

class YOLOv11InferenceService:
    """
    Central Inference Orchestrator for Drone Navigation:
    - Simultaneously executes Navigation AI (navigation_best.pt), FOD Detection (FOD_Karhtikeyan.pt),
      and Runway Light Fault Detection (runway_light_best.pt) on the same video frame.
    - Preprocesses frames and evaluates image quality (brightness, sharpness, warnings).
    - Merges detections from all three models and eliminates duplicates using per-class NMS.
    - Generates temporal alerts for runway light faults (LIGHT OFF) and FOD hazards.
    - Provides backward-compatible APIs for model status, selection, and inspection.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.model_name = os.path.basename(self.model_path) if self.model_path else "navigation_best.pt"
        self.device = torch.device("cuda" if torch.cuda.is_available() and settings.YOLO_DEVICE not in ("cpu", "-1") else "cpu")
        
        # Sub-services (PRD Section 4 & 51)
        self.navigation_service: NavigationService = navigation_service
        self.fod_service: FODService = fod_service
        self.runway_light_service: RunwayLightService = runway_light_service
        self.alert_service = alert_service
        
        self.model = self.navigation_service.model or self.fod_service.model
        self.classes: Dict[int, str] = {0: "NAVIGATION", 1: "FOD", 2: "LIGHT OFF", 3: "LIGHT ON"}
        self.loaded: bool = self.navigation_service.loaded or self.fod_service.loaded or self.runway_light_service.loaded
        self.is_valid: bool = self.loaded
        self.status: str = "READY" if self.loaded else "LOADING"
        self.error_message: Optional[str] = None
        self.last_inference_time_ms: float = 0.0

        logger.info(
            f"[INFERENCE_ORCHESTRATOR] Initialized with Navigation ({self.navigation_service.loaded}), "
            f"FOD ({self.fod_service.loaded}) & Runway Light ({self.runway_light_service.loaded})"
        )

    # ============================================================
    # MODEL MANAGEMENT & DIAGNOSTICS (PRD Section 29)
    # ============================================================
    def get_model_status(self) -> Dict[str, Any]:
        """
        Returns full diagnostics for all three models as specified in PRD Section 29:
        {
          "navigation": { "loaded": true, "classes": [...] },
          "fod": { "loaded": true },
          "runway_light": { "loaded": true, "classes": ["LIGHT OFF", "LIGHT ON"] }
        }
        Includes top-level keys for backward-compatibility with HUD & existing tests.
        """
        nav_loaded = self.navigation_service.loaded
        fod_loaded = self.fod_service.loaded
        light_loaded = self.runway_light_service.loaded
        all_ready = nav_loaded and fod_loaded and light_loaded

        status_str = "READY" if all_ready else ("PARTIAL" if (nav_loaded or fod_loaded or light_loaded) else "ERROR")

        nav_info = model_verifier.verify_model("NAVIGATION")
        fod_info = model_verifier.verify_model("FOD")
        light_info = model_verifier.verify_model("RUNWAY_LIGHT")

        return {
            # PRD Section 29 schema
            "navigation": {
                "loaded": nav_loaded,
                "model": os.path.basename(self.navigation_service.model_path),
                "classes": list(self.navigation_service.classes.values()) if self.navigation_service.classes else [],
                "confidence": self.navigation_service.confidence_threshold,
                "sha256": nav_info.get("sha256"),
                "native_imgsz": nav_info.get("native_imgsz", 640),
                "suitability_status": nav_info.get("suitability_status"),
                "suitability_notes": nav_info.get("suitability_notes"),
            },
            "fod": {
                "loaded": fod_loaded,
                "model": os.path.basename(self.fod_service.model_path),
                "classes": self.fod_service.classes,
                "confidence": self.fod_service.confidence,
                "status": self.fod_service.status,
                "error": self.fod_service.error,
                "sha256": fod_info.get("sha256"),
                "native_imgsz": fod_info.get("native_imgsz", 1024),
                "suitability_status": fod_info.get("suitability_status"),
                "suitability_notes": fod_info.get("suitability_notes"),
            },
            "runway_light": {
                "loaded": light_loaded,
                "model": os.path.basename(self.runway_light_service.model_path),
                "classes": ["LIGHT OFF", "LIGHT ON"],
                "confidence": self.runway_light_service.confidence,
                "status": self.runway_light_service.status,
                "error": self.runway_light_service.error,
                "sha256": light_info.get("sha256"),
                "native_imgsz": light_info.get("native_imgsz", 640),
                "suitability_status": light_info.get("suitability_status"),
                "suitability_notes": light_info.get("suitability_notes"),
            },
            # Top-level legacy / HUD schema
            "model_name": self.model_name,
            "model_path": self.model_path,
            "status": status_str,
            "classes": {0: "FOD", 1: "LIGHT OFF", 2: "LIGHT ON"},
            "device": str(self.device),
            "is_valid": self.loaded,
            "last_inference_time_ms": self.last_inference_time_ms,
            "error": self.error_message
        }

    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        Discovers all available .pt models in the workspace
        """
        patterns = [
            "ml_engine/models/*.pt",
            "ml_engine/models/trained/*.pt",
            "models/*.pt",
            "*.pt",
            "runs/detect/train/weights/*.pt",
        ]
        found_paths = set()
        for pat in patterns:
            for p in glob.glob(pat):
                found_paths.add(p)

        models = []
        for p in sorted(found_paths):
            basename = os.path.basename(p)
            size_mb = round(os.path.getsize(p) / (1024 * 1024), 2)
            is_active = (basename == self.model_name) or basename in (
                os.path.basename(self.fod_service.model_path),
                os.path.basename(self.runway_light_service.model_path)
            )
            models.append({
                "model_name": basename,
                "path": p,
                "is_active": is_active,
                "size_mb": size_mb,
            })
        return models

    def switch_model(self, model_name_or_path: str) -> Tuple[bool, str]:
        """
        Dynamically reloads/switches active models
        """
        basename = os.path.basename(model_name_or_path)
        candidates = [
            model_name_or_path,
            os.path.join("ml_engine", "models", basename),
            os.path.join("ml_engine", "models", "trained", basename),
            os.path.join("models", basename),
            os.path.join("runs", "detect", "train", "weights", basename),
        ]
        found = None
        for c in candidates:
            if os.path.exists(c):
                found = c
                break

        if not found:
            return False, f"Model file '{model_name_or_path}' not found."

        self.model_path = found
        self.model_name = os.path.basename(found)
        if "light" in basename.lower() or "runway" in basename.lower():
            self.runway_light_service.model_path = found
            self.runway_light_service.load_model()
        else:
            self.fod_service.model_path = found
            self.fod_service.load_model()

        return True, f"Successfully switched model to {self.model_name}"

    # ============================================================
    # IMAGE QUALITY & PREPROCESSING (PRD Section 10 & 19)
    # ============================================================
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        output = frame
        if settings.USE_CLAHE:
            lab = cv2.cvtColor(output, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
            l = clahe.apply(l)
            output = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

        if settings.USE_SHARPEN:
            blurred = cv2.GaussianBlur(output, (0, 0), 1.0)
            output = cv2.addWeighted(output, 1.25, blurred, -0.25, 0)

        return output

    def quality_metrics(self, frame: np.ndarray) -> Tuple[float, float, List[str]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        warnings = []
        if sharpness < 50:
            warnings.append("IMAGE IS BLURRY")
        if brightness < 45:
            warnings.append("IMAGE TOO DARK")
        elif brightness > 210:
            warnings.append("IMAGE OVEREXPOSED")

        return brightness, sharpness, warnings

    # ============================================================
    # SMALL OBJECT DETECTION / TILING (PRD Section 11)
    # ============================================================
    def tile_positions(self, length: int, tile_size: int, overlap: float) -> List[int]:
        if length <= tile_size:
            return [0]
        stride = max(1, int(tile_size * (1.0 - overlap)))
        positions = list(range(0, max(1, length - tile_size + 1), stride))
        last = length - tile_size
        if positions[-1] != last:
            positions.append(last)
        return positions

    def run_tiled(self, frame: np.ndarray, conf: float, iou: float) -> List[Dict[str, Any]]:
        """
        Runs tiled inference across sub-windows for small FOD debris & runway lights
        """
        h, w = frame.shape[:2]
        tile_size = settings.TILE_SIZE
        overlap = settings.TILE_OVERLAP
        xs = self.tile_positions(w, tile_size, overlap)
        ys = self.tile_positions(h, tile_size, overlap)

        tiled_detections: List[Dict[str, Any]] = []

        for y in ys:
            for x in xs:
                tile = frame[y:min(y + tile_size, h), x:min(x + tile_size, w)]
                if tile.size == 0:
                    continue

                # Run FOD on tile
                fod_tile = self.fod_service.predict(tile, conf=conf, iou=iou)
                for d in fod_tile:
                    bx = d["bbox"]
                    x1 = bx["x1"] + x
                    y1 = bx["y1"] + y
                    x2 = bx["x2"] + x
                    y2 = bx["y2"] + y
                    tiled_detections.append({
                        "model": "fod",
                        "class_id": d["class_id"],
                        "class_name": d["class_name"],
                        "confidence": d["confidence"],
                        "bbox": {"x1": round(x1, 1), "y1": round(y1, 1), "x2": round(x2, 1), "y2": round(y2, 1)},
                        "bbox_xywh": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)]
                    })

        return tiled_detections

    def nms_detections(self, detections: List[Any], score_threshold: float, nms_threshold: float) -> List[Any]:
        """
        Applies OpenCV NMS across detections per class to eliminate duplicate overlapping boxes
        Supports both list-of-lists [x1, y1, x2, y2, conf, cls_id] and dictionary schemas.
        """
        if not detections:
            return []

        # List of lists [x1, y1, x2, y2, conf, cls_id]
        if not isinstance(detections[0], dict):
            final = []
            classes = sorted(set(int(d[5]) for d in detections))
            for cls_id in classes:
                class_dets = [d for d in detections if int(d[5]) == cls_id]
                boxes_xywh = []
                scores = []
                for x1, y1, x2, y2, conf, _ in class_dets:
                    boxes_xywh.append([
                        int(round(x1)), int(round(y1)),
                        max(1, int(round(x2 - x1))), max(1, int(round(y2 - y1)))
                    ])
                    scores.append(float(conf))

                indices = cv2.dnn.NMSBoxes(
                    boxes_xywh,
                    scores,
                    score_threshold=float(score_threshold),
                    nms_threshold=float(nms_threshold)
                )

                if len(indices) > 0:
                    for idx in np.array(indices).reshape(-1):
                        final.append(class_dets[int(idx)])

            return sorted(final, key=lambda d: d[4], reverse=True)

        # Dictionary format
        final: List[Dict[str, Any]] = []
        classes = sorted(set(d.get("class_name", str(d.get("class_id", 0))) for d in detections))

        for cls_name in classes:
            class_dets = [d for d in detections if d.get("class_name", str(d.get("class_id", 0))) == cls_name]
            boxes_xywh = []
            scores = []
            for d in class_dets:
                b = d.get("bbox_xywh", [0, 0, 10, 10])
                boxes_xywh.append([int(b[0]), int(b[1]), max(1, int(b[2])), max(1, int(b[3]))])
                scores.append(float(d.get("confidence", 0.0)))

            indices = cv2.dnn.NMSBoxes(
                boxes_xywh,
                scores,
                score_threshold=float(score_threshold),
                nms_threshold=float(nms_threshold)
            )

            if len(indices) > 0:
                for idx in np.array(indices).reshape(-1):
                    final.append(class_dets[int(idx)])

        return sorted(final, key=lambda d: d.get("confidence", 0.0), reverse=True)

    # ============================================================
    # VISUALIZATION / HUD ANNOTATION (PRD Section 26)
    # ============================================================
    def draw_detections(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        Renders HUD bounding boxes with colors per PRD Section 26:
        - FOD -> Red (BGR: (0, 0, 255))
        - LIGHT ON -> Green (BGR: (0, 255, 0))
        - LIGHT OFF -> Orange/Red (BGR: (0, 140, 255))
        """
        annotated = frame.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.65
        font_thickness = 2

        for det in detections:
            bbox = det.get("bbox", {})
            if isinstance(bbox, dict):
                x1 = int(bbox.get("x1", 0))
                y1 = int(bbox.get("y1", 0))
                x2 = int(bbox.get("x2", 0))
                y2 = int(bbox.get("y2", 0))
            elif isinstance(bbox, list) and len(bbox) >= 4:
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            else:
                continue

            cls_name = det.get("class_name", "OBJ").upper()
            conf = det.get("confidence", 0.0)
            state = det.get("state")
            track_id = det.get("track_id")
            inferred = det.get("inferred", False)

            # Color coding per PRD Section 26
            if "FOD" in cls_name:
                box_color = (0, 0, 240)    # BGR Red
            elif "LIGHT OFF" in cls_name or "OFF" in cls_name:
                box_color = (0, 140, 255)  # BGR Orange
            elif "LIGHT ON" in cls_name or "ON" in cls_name:
                box_color = (0, 220, 0)    # BGR Green
            else:
                box_color = (255, 200, 0)  # BGR Cyan / Blue for Navigation objects

            p1 = (max(0, x1), max(0, y1))
            p2 = (min(annotated.shape[1] - 1, x2), min(annotated.shape[0] - 1, y2))

            # Draw box rectangle
            cv2.rectangle(annotated, p1, p2, box_color, 2, cv2.LINE_AA)

            # Draw label banner (PRD Section 36)
            track_str = f" #{track_id}" if track_id is not None else ""
            inferred_str = "*" if inferred else ""
            if state:
                label = f"{state}{inferred_str}{track_str} {conf:.2f}"
            else:
                label = f"{cls_name}{track_str} {conf:.2f}"

            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            label_top = max(0, p1[1] - text_h - baseline - 8)
            label_bottom = p1[1]
            label_right = min(annotated.shape[1] - 1, p1[0] + text_w + 10)

            cv2.rectangle(annotated, (p1[0], label_top), (label_right, label_bottom), box_color, -1)
            cv2.putText(annotated, label, (p1[0] + 4, p1[1] - baseline - 3), font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

        return annotated

    # ============================================================
    # PIPELINE EXECUTION (PRD Section 4, 8, 14, 27)
    # ============================================================
    def predict_frame(
        self,
        frame: np.ndarray,
        conf_thresh: Optional[float] = None,
        iou_thresh: Optional[float] = None,
        camera_id: str = "drone-camera-01"
    ) -> Dict[str, Any]:
        """
        Runs the simultaneous three-model inference pipeline:
        1. Preprocess frame & measure quality metrics (brightness, sharpness)
        2. Run Navigation Object Detection Model (navigation_best.pt)
        3. Run FOD Detection Model (FOD_Karhtikeyan.pt)
        4. Run Runway Light Detection Model (runway_light_best.pt / yolo_scan_window_detection_new.py)
        5. Run Tiled Inference if configured
        6. Merge and deduplicate detections with NMS
        7. Apply Temporal Confirmation for Runway Light Faults & FOD alerts
        8. Return unified standard detection payload
        """
        t0 = time.perf_counter()
        conf = conf_thresh if conf_thresh is not None else settings.YOLO_CONFIDENCE
        iou = iou_thresh if iou_thresh is not None else settings.YOLO_IOU
        h, w = frame.shape[:2]

        processed = self.preprocess_frame(frame)
        brightness, sharpness, warnings = self.quality_metrics(processed)

        all_detections: List[Dict[str, Any]] = []

        # Step 1: Navigation Inference (PRD Section 5.1)
        if self.navigation_service.loaded:
            nav_dets = self.navigation_service.predict(processed, conf_threshold=conf)
            all_detections.extend(nav_dets)

        # Step 2: FOD Inference (PRD Section 6)
        if self.fod_service.loaded:
            fod_dets = self.fod_service.predict(processed, conf=conf, iou=iou)
            all_detections.extend(fod_dets)

        # Step 3: Runway Light Inference (PRD Section 7 & 8)
        if self.runway_light_service.loaded:
            light_dets = self.runway_light_service.predict(processed, conf=conf, iou=iou)
            all_detections.extend(light_dets)

        # Step 4: Tiled Inference (for small debris / distant lights)
        if settings.USE_TILED_INFERENCE:
            tiled = self.run_tiled(processed, conf=conf, iou=iou)
            all_detections.extend(tiled)

        # Step 5: Apply NMS across merged detections
        filtered_detections = self.nms_detections(all_detections, score_threshold=conf, nms_threshold=iou)

        # Step 6: Process Alerts & Temporal Confirmation (PRD Section 16, 17, 18, 32, 33)
        alerts, summary_counts = self.alert_service.process_frame_detections(filtered_detections, camera_id=camera_id)

        t1 = time.perf_counter()
        elapsed_ms = round((t1 - t0) * 1000.0, 2)
        self.last_inference_time_ms = elapsed_ms

        raw_list = []
        for d in filtered_detections:
            bx = d["bbox"]
            if isinstance(bx, dict):
                raw_list.append([bx["x1"], bx["y1"], bx["x2"], bx["y2"], d.get("confidence", 0.0), d.get("class_id", 0)])
            elif isinstance(bx, (list, tuple)) and len(bx) >= 4:
                raw_list.append([bx[0], bx[1], bx[2], bx[3], d.get("confidence", 0.0), d.get("class_id", 0)])

        return {
            "model": f"{os.path.basename(self.navigation_service.model_path)} + {os.path.basename(self.fod_service.model_path)} + {os.path.basename(self.runway_light_service.model_path)}",
            "models": {
                "navigation": os.path.basename(self.navigation_service.model_path),
                "fod": os.path.basename(self.fod_service.model_path),
                "runway_light": os.path.basename(self.runway_light_service.model_path)
            },
            "width": w,
            "height": h,
            "detections": filtered_detections,
            "total_objects": len(filtered_detections),
            "quality": {
                "brightness": round(brightness, 1),
                "sharpness": round(sharpness, 1),
                "warnings": warnings
            },
            "alerts": alerts,
            "summary": summary_counts,
            "inference_time_ms": elapsed_ms,
            "latency_ms": elapsed_ms,
            "inference_fps": round(1000.0 / max(1.0, elapsed_ms), 1),
            "raw_detections": raw_list
        }

    def predict_image(self, image_bytes: bytes, conf_thresh: Optional[float] = None) -> Tuple[List[Dict[str, Any]], float, int, int]:
        """
        Backwards-compatible method for raw image bytes (e.g. from POST /api/v1/detection/image)
        """
        img_arr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img_arr is None:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_arr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        res = self.predict_frame(img_arr, conf_thresh=conf_thresh)
        return res["detections"], res["inference_time_ms"], res["width"], res["height"]

inference_service = YOLOv11InferenceService()
