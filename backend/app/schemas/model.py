from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class SubModelStatus(BaseModel):
    loaded: bool
    model: Optional[str] = None
    status: Optional[str] = None
    classes: Optional[Any] = None
    confidence: Optional[float] = None
    error: Optional[str] = None

class ModelStatusResponse(BaseModel):
    navigation: Optional[SubModelStatus] = None
    fod: Optional[SubModelStatus] = None
    runway_light: Optional[SubModelStatus] = None
    model_name: str
    model_path: str
    status: str
    classes: Dict[int, str]
    device: str
    is_valid: bool
    last_inference_time_ms: float
    error: Optional[str] = None

class ModelSelectRequest(BaseModel):
    model: str

class ModelSelectResponse(BaseModel):
    success: bool
    model: str
    status: str
    message: str
    classes: Dict[int, str] = {}

class ModelItem(BaseModel):
    model_name: str
    path: str
    is_active: bool
    size_mb: float
