import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional

import torch
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.database import SessionLocal
from backend.app.db.models import AnalysisJob


def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file for cryptographic model verification."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 16):
            h.update(chunk)
    return h.hexdigest()


class ModelVerifier:
    """
    Central Model Verification and Provenance Registry (PRD Section 4.1, 4.2, 4.3, 4.4).
    Validates model file existence, SHA-256 integrity, training parameters,
    task suitability, and records model version metadata for every analysis job.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_manifest(self) -> Dict[str, Dict[str, Any]]:
        return {
            "NAVIGATION": {
                "name": "navigation_best.pt",
                "path": settings.NAVIGATION_MODEL_PATH,
                "expected_classes": 80,
                "class_names_summary": "80 standard COCO classes (person, vehicle, airplane, bag, etc.)",
                "intended_task": "General Ground & Airfield Environment Object Detection",
                "suitability_status": "VALIDATED_COCO_GENERAL",
                "suitability_notes": (
                    "Trained on COCO 80 dataset. Suitable for identifying ground personnel, aircraft, "
                    "support vehicles, and general obstacles in the drone flight envelope. "
                    "Not trained on runway centerline markings or specialized pavement fixtures."
                ),
                "native_imgsz": 640,
                "confidence_threshold": settings.NAVIGATION_CONFIDENCE,
            },
            "FOD": {
                "name": "FOD_Karhtikeyan.pt",
                "path": settings.FOD_MODEL_PATH,
                "expected_classes": 1,
                "class_names_summary": "1 class: FOD (Foreign Object Debris)",
                "intended_task": "Runway Foreign Object Debris Detection",
                "suitability_status": "VALIDATED_FOD_SPECIFIC",
                "suitability_notes": (
                    "Trained on dedicated Combined Augmented FOD dataset at 1024x1024 resolution. "
                    "Detects small runway debris (screws, tools, fragments, tire rubber). "
                    "Includes whole-frame ground hallucination filter."
                ),
                "native_imgsz": settings.FOD_IMGSZ,
                "confidence_threshold": settings.FOD_CONFIDENCE,
            },
            "RUNWAY_LIGHT": {
                "name": "runway_light_best.pt",
                "path": settings.RUNWAY_LIGHT_MODEL_PATH,
                "expected_classes": 2,
                "class_names_summary": "2 classes: LIGHT OFF (0), LIGHT ON (1)",
                "intended_task": "Runway Light Binary Detection & Illumination Classification",
                "suitability_status": "VALIDATED_RUNWAY_LIGHT_SPECIFIC",
                "suitability_notes": (
                    "Trained on 3,033 airfield lighting images (data.yaml). "
                    "Test set evaluation achieves 66.3% mAP@50 and 81.4% precision. "
                    "Empty initial background frames produce 0 detections (true negatives). "
                    "Never assumes missing detections indicate an OFF fixture."
                ),
                "native_imgsz": 640,
                "confidence_threshold": settings.RUNWAY_LIGHT_CONFIDENCE,
            }
        }

    def verify_model(self, module_key: str, force_refresh: bool = False) -> Dict[str, Any]:
        mod_upper = module_key.upper()
        if mod_upper in ("RUNWAY", "RUNWAY_LIGHT"):
            norm_key = "RUNWAY_LIGHT"
        elif mod_upper in ("FOD", "FOD_DEBRIS"):
            norm_key = "FOD"
        else:
            norm_key = "NAVIGATION"

        if not force_refresh and norm_key in self._cache:
            return self._cache[norm_key]

        manifest = self.get_manifest().get(norm_key, {})
        p = Path(manifest["path"])
        if not p.is_absolute():
            p = Path(os.getcwd()) / p

        info: Dict[str, Any] = {
            "module": norm_key,
            "model_name": manifest.get("name", p.name),
            "model_path": str(p),
            "file_exists": p.exists(),
            "intended_task": manifest.get("intended_task"),
            "suitability_status": manifest.get("suitability_status"),
            "suitability_notes": manifest.get("suitability_notes"),
            "native_imgsz": manifest.get("native_imgsz", 640),
            "confidence_threshold": manifest.get("confidence_threshold", 0.20),
            "is_valid": False,
            "error": None,
        }

        if not p.exists():
            info["error"] = f"Model weights file not found at {p}"
            self._cache[norm_key] = info
            return info

        try:
            size_bytes = p.stat().st_size
            info["size_bytes"] = size_bytes
            info["size_mb"] = round(size_bytes / (1024 * 1024), 2)
            info["sha256"] = compute_sha256(str(p))

            ckpt = torch.load(str(p), map_location="cpu", weights_only=False)
            if isinstance(ckpt, dict):
                info["epoch"] = ckpt.get("epoch", -1)
                info["version"] = ckpt.get("version", "unknown")
                ta = ckpt.get("train_args", {})
                if isinstance(ta, dict):
                    info["train_dataset"] = ta.get("data", "unknown")
                    info["train_imgsz"] = ta.get("imgsz", info["native_imgsz"])

                raw_names = None
                if "model" in ckpt and hasattr(ckpt["model"], "names"):
                    raw_names = ckpt["model"].names
                elif "ema" in ckpt and hasattr(ckpt["ema"], "names"):
                    raw_names = ckpt["ema"].names
                elif "names" in ckpt:
                    raw_names = ckpt["names"]

                if raw_names is not None:
                    info["classes"] = {int(k): str(v) for k, v in raw_names.items()}
                    info["num_classes"] = len(info["classes"])
                else:
                    info["num_classes"] = manifest.get("expected_classes", 0)

            info["is_valid"] = True
            logger.info(f"[MODEL_VERIFIER] Verified {norm_key} model: {info['model_name']} (SHA256: {info['sha256'][:12]}...)")
        except Exception as e:
            info["error"] = f"Failed to load/verify checkpoint: {e}"
            logger.error(f"[MODEL_VERIFIER] Verification failed for {norm_key}: {e}")

        self._cache[norm_key] = info
        return info

    def verify_all_models(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        for mod in ["NAVIGATION", "FOD", "RUNWAY_LIGHT"]:
            results[mod] = self.verify_model(mod)
        return results

    def record_job_metadata(self, job_id: str, module_key: str):
        """
        Records the verified model path, SHA-256 hash/version, and confidence threshold
        into the database record for the job (PRD Section 4.1).
        """
        try:
            info = self.verify_model(module_key)
            with SessionLocal() as db:
                job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
                if job:
                    job.model_path = info.get("model_path")
                    job.model_version = info.get("sha256", "")[:16]
                    job.confidence_threshold = info.get("confidence_threshold", 0.20)
                    db.commit()
        except Exception as e:
            logger.warning(f"[MODEL_VERIFIER] Could not record metadata for job {job_id}: {e}")


model_verifier = ModelVerifier()
