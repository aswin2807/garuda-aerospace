from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict

class BBoxDict(BaseModel):
    x: Optional[float] = 0.0
    y: Optional[float] = 0.0
    width: Optional[float] = 0.0
    height: Optional[float] = 0.0
    x1: Optional[float] = 0.0
    y1: Optional[float] = 0.0
    x2: Optional[float] = 0.0
    y2: Optional[float] = 0.0

class DetectionItem(BaseModel):
    model: Optional[str] = "navigation"
    class_id: int
    class_name: str
    state: Optional[str] = None
    track_id: Optional[int] = None
    inferred: Optional[bool] = False
    confidence: float
    bbox: Union[List[float], BBoxDict, dict]
    bbox_xywh: Optional[List[float]] = None

class ImageDetectionResponse(BaseModel):
    success: bool = True
    processing_time_ms: float
    detections: List[DetectionItem]

class VideoDetectionResponse(BaseModel):
    success: bool = True
    task_id: str
    status: str
    message: str

class DetectionHistoryItem(BaseModel):
    id: str
    mission_id: Optional[str] = None
    drone_id: Optional[str] = None
    class_name: str
    class_id: int
    confidence: float
    x: float
    y: float
    width: float
    height: float
    frame_number: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
