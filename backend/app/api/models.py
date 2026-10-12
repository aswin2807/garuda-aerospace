from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.app.services.inference_service import inference_service

router = APIRouter()

class ModelSelectRequest(BaseModel):
    model: str

class ModelSelectResponse(BaseModel):
    success: bool
    model: str
    status: str
    message: str
    classes: Dict[int, str] = {}

class ModelStatusResponse(BaseModel):
    navigation: Optional[Dict[str, Any]] = None
    fod: Optional[Dict[str, Any]] = None
    runway_light: Optional[Dict[str, Any]] = None
    model_name: str
    model_path: str
    status: str
    classes: Dict[int, str]
    device: str
    is_valid: bool
    last_inference_time_ms: float
    error: Optional[str] = None

class ModelItem(BaseModel):
    model_name: str
    path: str
    is_active: bool
    size_mb: float

@router.get("/status", response_model=ModelStatusResponse)
def get_model_status():
    """
    Returns the current status of all 3 models: navigation, fod, runway_light (PRD Section 29)
    """
    return inference_service.get_model_status()

@router.get("/navigation/classes")
def get_navigation_classes():
    """
    Returns dynamic navigation classes read from model.names (PRD Section 30)
    """
    from backend.app.services.navigation_service import navigation_service
    classes = navigation_service.get_classes()
    return {
        "classes": list(classes.values()) if classes else [],
        "class_map": classes
    }

@router.get("/list", response_model=List[ModelItem])
def list_available_models():
    """
    Lists all available models in the project (e.g. FOD_Karhtikeyan.pt, best.pt)
    """
    return inference_service.list_available_models()

@router.post("/select", response_model=ModelSelectResponse)
def select_model(request: ModelSelectRequest):
    """
    Dynamically loads and switches the active YOLO model
    """
    success, msg = inference_service.switch_model(request.model)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    return {
        "success": True,
        "model": inference_service.model_name,
        "status": inference_service.status,
        "message": msg,
        "classes": inference_service.classes
    }
