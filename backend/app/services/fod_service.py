import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
import torch

from backend.app.core.config import settings
from backend.app.core.logging import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("Ultralytics not installed. Falling back to PyTorch for FOD service.")

def get_optimal_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

class FODService:
    """
    Dedicated service for Foreign Object Debris (FOD) Detection
    Uses FOD_Karhtikeyan.pt with high-performance hardware acceleration (CUDA/MPS/CPU).
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.FOD_MODEL_PATH
        self.model = None
        self.classes: Dict[int, str] = {0: "FOD"}
        self.loaded: bool = False
        self.status: str = "INITIALIZING"
        self.device = get_optimal_device()
        self.confidence: float = settings.FOD_CONFIDENCE
        self.iou: float = settings.IOU_THRESHOLD
        self.imgsz: int = getattr(settings, "FOD_IMGSZ", 640)
        self.error: Optional[str] = None
        self.load_model()

    def get_optimal_device(self) -> str:
        return str(self.device.type if hasattr(self.device, "type") else self.device)

    def load_model(self) -> bool:
        self.status = "LOADING"
        resolved_path = Path(self.model_path)
        if not resolved_path.is_absolute():
            resolved_path = Path(os.getcwd()) / resolved_path

        if not resolved_path.exists():
            # Check fallback in ml_engine/models/
            fallback = Path(os.getcwd()) / "ml_engine" / "models" / "FOD_Karhtikeyan.pt"
            if fallback.exists():
                resolved_path = fallback

        if not resolved_path.exists():
            self.status = "ERROR"
            self.error = f"FOD model file not found at: {resolved_path}"
            logger.error(self.error)
            return False

        logger.info(f"[FOD_SERVICE] Loading FOD model from {resolved_path} onto {self.device}")
        try:
            if ULTRALYTICS_AVAILABLE:
                try:
                    self.model = YOLO(str(resolved_path))
                    if hasattr(self.model, "names") and self.model.names:
                        self.classes = {int(k): str(v) for k, v in self.model.names.items()}
                    self.loaded = True
                    self.status = "READY"
                    self.model_path = str(resolved_path)
                    logger.info(f"[FOD_SERVICE] FOD model loaded successfully via Ultralytics with classes {self.classes}")
                    return True
                except Exception as ex_ultra:
                    logger.warning(f"[FOD_SERVICE] Ultralytics loading failed: {ex_ultra}. Trying PyTorch...")

            checkpoint = torch.load(str(resolved_path), map_location=self.device, weights_only=False)
            if isinstance(checkpoint, dict):
                if "classes" in checkpoint:
                    self.classes = checkpoint["classes"]
                elif "names" in checkpoint:
                    self.classes = {int(k): str(v) for k, v in checkpoint["names"].items()}
            self.model = checkpoint
            self.loaded = True
            self.status = "READY"
            self.model_path = str(resolved_path)
            logger.info(f"[FOD_SERVICE] FOD checkpoint loaded successfully via PyTorch with classes {self.classes}")
            return True
        except Exception as e:
            self.status = "ERROR"
            self.error = str(e)
            logger.error(f"[FOD_SERVICE] Failed to load FOD model: {e}")
            return False

    def predict(
        self,
        frame: np.ndarray,
        conf: Optional[float] = None,
        iou: Optional[float] = None,
        imgsz: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs hardware-accelerated inference for FOD detection.
        Returns list of detections with normalized schema:
        {
            "model": "fod",
            "class_id": 0,
            "class_name": "FOD",
            "confidence": 0.91,
            "bbox": [x1, y1, x2, y2],
            "bbox_dict": {"x1": ..., "y1": ..., "x2": ..., "y2": ...},
            "xyxy": [x1, y1, x2, y2],
            "bbox_xywh": [x, y, w, h]
        }
        """
        if frame is None or frame.size == 0 or not self.loaded or self.model is None:
            return []

        c = conf if conf is not None else self.confidence
        i = iou if iou is not None else self.iou
        sz = imgsz if imgsz is not None else self.imgsz
        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []

        if ULTRALYTICS_AVAILABLE and hasattr(self.model, "predict"):
            try:
                results = self.model.predict(
                    source=frame,
                    conf=c,
                    iou=i,
                    imgsz=sz,
                    device=str(self.device),
                    verbose=False
                )
                for res in results:
                    boxes = res.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            score = float(box.conf[0].item())
                            cls_id = int(box.cls[0].item())
                            cls_name = self.classes.get(cls_id, "FOD")
                            rx1, ry1, rx2, ry2 = round(float(x1), 1), round(float(y1), 1), round(float(x2), 1), round(float(y2), 1)
                            bw = max(1.0, rx2 - rx1)
                            bh = max(1.0, ry2 - ry1)
                            if (bw * bh) > 0.65 * (w * h) and (bw > 0.80 * w or bh > 0.80 * h):
                                # Reject full-frame ground hallucination per PRD Section 1.2 & 4.3
                                continue

                            detections.append({
                                "model": "fod",
                                "class_id": cls_id,
                                "class_name": cls_name,
                                "confidence": round(score, 3),
                                "bbox": [rx1, ry1, rx2, ry2],
                                "bbox_dict": {
                                    "x1": rx1,
                                    "y1": ry1,
                                    "x2": rx2,
                                    "y2": ry2,
                                },
                                "xyxy": [rx1, ry1, rx2, ry2],
                                "bbox_xywh": [
                                    rx1,
                                    ry1,
                                    round(float(rx2 - rx1), 1),
                                    round(float(ry2 - ry1), 1),
                                ]
                            })
            except Exception as e:
                logger.error(f"[FOD_SERVICE] Inference error: {e}")

        return detections

fod_service = FODService()
