import os
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import torch
from backend.app.core.config import settings
from backend.app.core.logging import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


def get_optimal_device() -> torch.device:
    """Returns optimal torch device: CUDA, Apple Silicon MPS, or CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class NavigationService:
    """
    Dedicated Navigation Model Inference Service (PRD Section 5.1).
    Loads navigation_best.pt and dynamically loads class names from model.names.
    Does NOT hard-code class names.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.NAVIGATION_MODEL_PATH
        self.confidence_threshold = settings.NAVIGATION_CONFIDENCE
        self.iou_threshold = settings.IOU_THRESHOLD
        self.device = str(get_optimal_device())
        self.model = None
        self.classes: Dict[int, str] = {}
        self.loaded = False
        self._lock = threading.Lock()
        self.load_model()

    def load_model(self) -> bool:
        with self._lock:
            path_obj = Path(self.model_path)
            if not path_obj.is_absolute():
                base_dir = Path(__file__).resolve().parent.parent.parent.parent
                path_obj = base_dir / self.model_path

            if not path_obj.exists():
                logger.warning(f"[NAVIGATION_SERVICE] Model file not found at {path_obj}")
                self.loaded = False
                return False

            try:
                if ULTRALYTICS_AVAILABLE:
                    logger.info(f"[NAVIGATION_SERVICE] Loading Navigation model from {path_obj} onto {self.device}")
                    self.model = YOLO(str(path_obj))
                    # Read classes dynamically from model.names (PRD Section 5.1 & 30)
                    if hasattr(self.model, "names") and self.model.names:
                        self.classes = {int(k): str(v) for k, v in self.model.names.items()}
                    else:
                        self.classes = {0: "OBJECT"}
                    self.loaded = True
                    logger.info(f"[NAVIGATION_SERVICE] Navigation model loaded successfully with {len(self.classes)} dynamic classes")
                    return True
                else:
                    logger.info(f"[NAVIGATION_SERVICE] Ultralytics unavailable, loading PyTorch checkpoint: {path_obj}")
                    ckpt = torch.load(str(path_obj), map_location=self.device)
                    if isinstance(ckpt, dict) and "model" in ckpt:
                        self.model = ckpt["model"]
                        names = getattr(self.model, "names", ckpt.get("names", {}))
                        if names:
                            self.classes = {int(k): str(v) for k, v in names.items()}
                    self.loaded = True
                    return True
            except Exception as e:
                logger.error(f"[NAVIGATION_SERVICE] Failed to load Navigation model: {e}")
                self.loaded = False
                return False

    def predict(self, frame: np.ndarray, conf_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Runs navigation object detection on the given frame.
        Returns list of detection dicts with dynamic class names.
        """
        if not self.loaded or self.model is None:
            return []

        conf = conf_threshold if conf_threshold is not None else self.confidence_threshold
        detections: List[Dict[str, Any]] = []

        try:
            if ULTRALYTICS_AVAILABLE and isinstance(self.model, YOLO):
                results = self.model.predict(
                    frame,
                    conf=conf,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=False,
                )
                if results and len(results) > 0:
                    r = results[0]
                    # Update classes if dynamically discovered
                    if hasattr(r, "names") and r.names and not self.classes:
                        self.classes = {int(k): str(v) for k, v in r.names.items()}

                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        box_conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].tolist()
                        x1, y1, x2, y2 = [int(round(coord)) for coord in xyxy]
                        cls_name = self.classes.get(cls_id, f"OBJECT_{cls_id}")

                        detections.append({
                            "model": "navigation",
                            "class_id": cls_id,
                            "class_name": cls_name,
                            "confidence": round(box_conf, 3),
                            "bbox": [x1, y1, x2, y2],
                            "bbox_xywh": [x1, y1, max(0, x2 - x1), max(0, y2 - y1)],
                        })
            else:
                # Simulated / fallback detection if torch module cannot run full ultralytics
                pass
        except Exception as e:
            logger.error(f"[NAVIGATION_SERVICE] Inference error: {e}")

        return detections

    def get_classes(self) -> Dict[int, str]:
        """Returns the dynamic class dictionary from model.names."""
        return self.classes


navigation_service = NavigationService()
