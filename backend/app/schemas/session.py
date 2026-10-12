from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SessionCreateRequest(BaseModel):
    source: str = Field(..., description="Camera RTSP stream or video file path")
    source_type: str = Field(default="VIDEO_FILE", description="'RTSP', 'WEBCAM', or 'VIDEO_FILE'")
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    source: str
    source_type: str
    status: str
    created_at: Optional[str] = None
    finished_at: Optional[str] = None
    total_frames: int = 0
    processed_frames: int = 0

class SessionStatsResponse(BaseModel):
    session_id: str
    duration_seconds: float = 0.0
    duration_formatted: str = "00:00"
    total_frames: int = 0
    processed_frames: int = 0
    nav_count: int = 0
    fod_count: int = 0
    light_on_count: int = 0
    light_off_count: int = 0
    confirmed_faults: int = 0
    avg_confidence: float = 0.0
    avg_inference_ms: float = 0.0

class SessionDetectionsResponse(BaseModel):
    session_id: str
    count: int
    detections: List[Dict[str, Any]]
