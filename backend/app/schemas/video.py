from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class VideoStartRequest(BaseModel):
    source: str = Field(..., description="File path, RTSP stream URL, or 'demo' for synthetic test feed")
    loop: bool = Field(default=False, description="Whether to loop the video upon reaching EOF")
    session_id: Optional[str] = Field(default=None, description="Optional custom session identifier")

class VideoStartResponse(BaseModel):
    session_id: str
    status: str
    source: str
    message: str

class VideoStopResponse(BaseModel):
    session_id: str
    status: str
    statistics: Dict[str, Any]

class SessionStatsResponse(BaseModel):
    session_id: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_frames: int = 0
    processed_frames: int = 0
    total_detections: int = 0
    average_confidence: float = 0.0
    average_inference_ms: float = 0.0
    counts: Dict[str, int] = {}
    unique_tracks: Dict[str, int] = {}
