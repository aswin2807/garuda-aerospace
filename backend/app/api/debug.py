from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel

from backend.app.services.frame_processor import frame_processor
from backend.app.services.database_service import database_service
from backend.app.websocket.detection_ws import manager

router = APIRouter(prefix="/debug", tags=["Pipeline Debugging"])

class SchedulingUpdateRequest(BaseModel):
    navigation_every_n_frames: Optional[int] = None
    fod_every_n_frames: Optional[int] = None
    runway_every_n_frames: Optional[int] = None
    navigation_enabled: Optional[bool] = None
    fod_enabled: Optional[bool] = None
    runway_enabled: Optional[bool] = None

@router.get("/pipeline")
def get_debug_pipeline():
    """
    Critical Debug Endpoint per PRD Section 36:
    Exposes frame, inference, detection, database, and client counters
    """
    total_clients = manager.get_total_clients()
    return frame_processor.get_debug_pipeline(active_ws_clients=total_clients)

@router.get("/pipeline/health")
def get_pipeline_health():
    """
    Pipeline Health Indicators per PRD Section 37:
    VIDEO, FRAME READER, NAVIGATION, FOD, RUNWAY LIGHT, DATABASE, WEBSOCKET
    """
    db_stats = database_service.get_db_stats()
    total_clients = manager.get_total_clients()

    return {
        "video": "CONNECTED" if frame_processor.video_connected else "STANDBY",
        "frame_reader": "RUNNING" if frame_processor.frames_received > 0 else "IDLE",
        "navigation": "RUNNING" if frame_processor.nav_enabled else "OFF",
        "fod": "RUNNING" if frame_processor.fod_enabled else "OFF",
        "runway_light": "RUNNING" if frame_processor.runway_enabled else "OFF",
        "database": "CONNECTED",
        "websocket": "CONNECTED" if total_clients > 0 else "READY",
        "details": {
            "total_clients": total_clients,
            "total_sessions": db_stats.get("total_sessions", 0),
            "total_detections_logged": db_stats.get("total_detections", 0)
        }
    }

@router.post("/scheduling")
def update_scheduling(req: SchedulingUpdateRequest):
    """
    Updates model inference scheduling strides per PRD Section 8
    """
    frame_processor.update_scheduling(
        nav_every_n=req.navigation_every_n_frames,
        fod_every_n=req.fod_every_n_frames,
        runway_every_n=req.runway_every_n_frames,
        nav_enabled=req.navigation_enabled,
        fod_enabled=req.fod_enabled,
        runway_enabled=req.runway_enabled
    )
    return {
        "success": True,
        "scheduling": {
            "navigation_every_n_frames": frame_processor.nav_every_n,
            "fod_every_n_frames": frame_processor.fod_every_n,
            "runway_every_n_frames": frame_processor.runway_every_n
        }
    }
