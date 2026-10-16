import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_core_dir = Path(__file__).resolve().parent
_project_root = _core_dir.parent.parent.parent

def _get_default_model_path() -> str:
    # Prioritize FOD_Karhtikeyan.pt per PRD Component 3
    fod_candidate = _project_root / "ml_engine" / "models" / "FOD_Karhtikeyan.pt"
    if fod_candidate.exists():
        return str(fod_candidate)
    trained_candidate = _project_root / "ml_engine" / "models" / "trained" / "best.pt"
    if trained_candidate.exists():
        return str(trained_candidate)
    return "ml_engine/models/FOD_Karhtikeyan.pt"

def _get_default_db_url() -> str:
    db_file = _project_root / "drone_nav.db"
    return f"sqlite:///{db_file}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Drone Navigation AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL") or _get_default_db_url()

    # Security & Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-drone-navigation-ai-jwt-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "1"))
    MAX_PASSWORD_BYTES: int = 72
    PASSWORD_RESET_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "30"))
    EMAIL_VERIFY_EXPIRE_HOURS: int = int(os.getenv("EMAIL_VERIFY_EXPIRE_HOURS", "24"))

    # Email / SMTP Delivery Settings (credentials loaded strictly from environment)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "t")
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1", "t")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@garuda.aero")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Garuda Aerospace")
    EMAIL_DEV_OUTBOX_DIR: str = os.getenv(
        "EMAIL_DEV_OUTBOX_DIR", str(_project_root / "outputs" / "emails")
    )



    # Model & Inference configuration (PRD Section 5, 6, 7, 25, 26)
    MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH") or os.getenv("MODEL_PATH") or _get_default_model_path()
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH") or os.getenv("MODEL_PATH") or _get_default_model_path()
    NAVIGATION_MODEL_PATH: str = os.getenv("NAVIGATION_MODEL_PATH") or str(_project_root / "ml_engine" / "models" / "navigation_best.pt")
    FOD_MODEL_PATH: str = os.getenv("FOD_MODEL_PATH") or str(_project_root / "ml_engine" / "models" / "FOD_Karhtikeyan.pt")
    RUNWAY_LIGHT_MODEL_PATH: str = os.getenv("RUNWAY_LIGHT_MODEL_PATH") or str(_project_root / "ml_engine" / "models" / "runway_light_best.pt")
    MODELS_CONFIG_PATH: str = os.getenv("MODELS_CONFIG_PATH") or str(_project_root / "ml_engine" / "configs" / "models.yaml")

    # Model Thresholds
    NAVIGATION_CONFIDENCE: float = float(os.getenv("NAVIGATION_CONFIDENCE", "0.25"))
    FOD_CONFIDENCE: float = float(os.getenv("FOD_CONFIDENCE", "0.15"))
    RUNWAY_LIGHT_CONFIDENCE: float = float(os.getenv("RUNWAY_LIGHT_CONFIDENCE", "0.20"))
    IOU_THRESHOLD: float = float(os.getenv("IOU_THRESHOLD", "0.45"))
    YOLO_CONFIDENCE: float = float(os.getenv("YOLO_CONFIDENCE", "0.18"))
    YOLO_IOU: float = float(os.getenv("YOLO_IOU", "0.45"))
    USE_TRACKING: bool = os.getenv("USE_TRACKING", "true").lower() in ("true", "1", "t")
    FOD_IMGSZ: int = int(os.getenv("FOD_IMGSZ", "1024"))

    # Pipeline & Tiling (PRD Section 11 & 26)
    USE_TILED_INFERENCE: bool = os.getenv("USE_TILED_INFERENCE", "true").lower() in ("true", "1", "t")
    FULL_FRAME_IMGSZ: int = int(os.getenv("FULL_FRAME_IMGSZ", "960"))
    TILE_SIZE: int = int(os.getenv("TILE_SIZE", "640"))
    TILE_OVERLAP: float = float(os.getenv("TILE_OVERLAP", "0.25"))
    USE_FULL_FRAME_PASS: bool = os.getenv("USE_FULL_FRAME_PASS", "true").lower() in ("true", "1", "t")
    USE_CLAHE: bool = os.getenv("USE_CLAHE", "false").lower() in ("true", "1", "t")
    USE_SHARPEN: bool = os.getenv("USE_SHARPEN", "false").lower() in ("true", "1", "t")
    YOLO_DEVICE: str = os.getenv("YOLO_DEVICE", "0")

    # Runway Light Scan Window Pipeline Settings (PRD Section 9, 10, 11, 16, 18, 20, 26)
    RUNWAY_SCAN_START: float = float(os.getenv("RUNWAY_SCAN_START", "0.52"))
    RUNWAY_SCAN_HEIGHT: float = float(os.getenv("RUNWAY_SCAN_HEIGHT", "0.20"))
    RUNWAY_TILE_SIZE: int = int(os.getenv("RUNWAY_TILE_SIZE", "640"))
    RUNWAY_TILE_STRIDE: int = int(os.getenv("RUNWAY_TILE_STRIDE", "480"))
    RUNWAY_DETECT_STRIDE: int = int(os.getenv("RUNWAY_DETECT_STRIDE", "10"))
    RUNWAY_PREPROCESS: str = os.getenv("RUNWAY_PREPROCESS", "auto")
    RUNWAY_TRACKING: bool = os.getenv("RUNWAY_TRACKING", "true").lower() in ("true", "1", "t")
    RUNWAY_REFINE_BOXES: bool = os.getenv("RUNWAY_REFINE_BOXES", "false").lower() in ("true", "1", "t")
    RUNWAY_INFER_MISSING_OFF: bool = os.getenv("RUNWAY_INFER_MISSING_OFF", "false").lower() in ("true", "1", "t")
    RUNWAY_IMGSZ: int = int(os.getenv("RUNWAY_IMGSZ", "640"))
    RUNWAY_FILTER_MODE: str = os.getenv("RUNWAY_FILTER_MODE", "sensitive")
    RUNWAY_ON_MIN_CONF: float = float(os.getenv("RUNWAY_ON_MIN_CONF", "0.20"))
    RUNWAY_OFF_MIN_CONF: float = float(os.getenv("RUNWAY_OFF_MIN_CONF", "0.20"))
    RUNWAY_MIN_BOX_SIDE: float = float(os.getenv("RUNWAY_MIN_BOX_SIDE", "2.5"))
    RUNWAY_MAX_BOX_SIDE: float = float(os.getenv("RUNWAY_MAX_BOX_SIDE", "150.0"))
    RUNWAY_MAX_BOX_AREA: float = float(os.getenv("RUNWAY_MAX_BOX_AREA", "15000.0"))
    RUNWAY_MIN_ASPECT: float = float(os.getenv("RUNWAY_MIN_ASPECT", "0.25"))
    RUNWAY_MAX_ASPECT: float = float(os.getenv("RUNWAY_MAX_ASPECT", "4.0"))
    RUNWAY_PAINT_REJECT: bool = os.getenv("RUNWAY_PAINT_REJECT", "true").lower() in ("true", "1", "t")
    RUNWAY_BOX_STYLE: str = os.getenv("RUNWAY_BOX_STYLE", "full")
    RUNWAY_BOX_THICKNESS: int = int(os.getenv("RUNWAY_BOX_THICKNESS", "2"))
    RUNWAY_CORNER_LENGTH: int = int(os.getenv("RUNWAY_CORNER_LENGTH", "14"))
    RUNWAY_SHOW_LABELS: bool = os.getenv("RUNWAY_SHOW_LABELS", "true").lower() in ("true", "1", "t")
    RUNWAY_SHOW_CONF: bool = os.getenv("RUNWAY_SHOW_CONF", "true").lower() in ("true", "1", "t")
    RUNWAY_SHOW_TRACK_IDS: bool = os.getenv("RUNWAY_SHOW_TRACK_IDS", "false").lower() in ("true", "1", "t")
    RUNWAY_SHOW_SCAN_WINDOW: bool = os.getenv("RUNWAY_SHOW_SCAN_WINDOW", "false").lower() in ("true", "1", "t")
    RUNWAY_SHOW_BANNER: bool = os.getenv("RUNWAY_SHOW_BANNER", "true").lower() in ("true", "1", "t")

    # Runway Pathway ROI Settings (PRD Section 2, 4, 11)
    RUNWAY_ROI_ENABLED: bool = os.getenv("RUNWAY_ROI_ENABLED", "true").lower() in ("true", "1", "t")
    RUNWAY_ROI_BOUNDARY_RULE: str = os.getenv("RUNWAY_ROI_BOUNDARY_RULE", "BOTTOM_CENTER")
    RUNWAY_ROI_MIN_OVERLAP: float = float(os.getenv("RUNWAY_ROI_MIN_OVERLAP", "0.50"))
    RUNWAY_ROI_STRICT_MODE: bool = os.getenv("RUNWAY_ROI_STRICT_MODE", "true").lower() in ("true", "1", "t")
    RUNWAY_ROI_DEFAULT_POLYGON: Optional[str] = os.getenv("RUNWAY_ROI_DEFAULT_POLYGON", None)

    # RTSP & Camera Defaults (PRD Section 9 & 26)
    RTSP_URL: str = os.getenv("RTSP_URL", "rtsp://192.168.144.108:554/stream=1")

    # Temporal Confirmation (PRD Section 33)
    LIGHT_FAULT_CONFIRM_FRAMES: int = int(os.getenv("LIGHT_FAULT_CONFIRM_FRAMES", "5"))

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
