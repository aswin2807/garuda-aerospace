from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator

class CameraConnectRequest(BaseModel):
    camera_id: Optional[str] = "camera_01"
    flight_id: Optional[str] = None
    rtsp_url: Optional[str] = None
    stream_url: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = 554
    protocol: Optional[str] = "RTSP"
    path: Optional[str] = "/stream"
    username: Optional[str] = None
    password: Optional[str] = None
    camera_name: Optional[str] = "Drone Optical Camera"
    is_simulated: Optional[bool] = False

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.upper()
            if v_upper not in ["RTSP", "HTTP", "HTTPS", "MJPEG", "WEBCAM"]:
                raise ValueError("Protocol must be RTSP, HTTP, HTTPS, MJPEG, or WEBCAM")
            return v_upper
        return "RTSP"

class CameraConnectResponse(BaseModel):
    success: bool
    camera_id: str
    flight_id: Optional[str] = None
    flight_status: Optional[str] = "FLYING"
    status: str
    message: Optional[str] = "Connected to camera"
    stream_url: Optional[str] = ""
    fps: Optional[float] = 0.0
    latency_ms: Optional[float] = 0.0

class CameraStatusResponse(BaseModel):
    camera_id: str
    camera_name: Optional[str] = "Drone Camera"
    flight_id: Optional[str] = None
    flight_status: Optional[str] = "FLYING"
    status: str
    width: Optional[int] = 1920
    height: Optional[int] = 1080
    fps: float = 0.0
    camera_fps: Optional[float] = 0.0
    inference_fps: Optional[float] = 0.0
    latency_ms: Optional[float] = 0.0
    brightness: Optional[float] = None
    sharpness: Optional[float] = None
    warnings: List[str] = []
    total_detections: int = 0
    detections: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    summary: Optional[Dict[str, Any]] = None
    latest_detected_object: Optional[str] = None
    latest_confidence: Optional[float] = None
    last_detection_time: Optional[str] = None
    frames_analyzed: Optional[int] = 0
    pre_landing_summary: Optional[Dict[str, Any]] = None
    model: Optional[str] = "runway_light_best.pt"
    stream_url: Optional[str] = ""
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CameraDisconnectResponse(BaseModel):
    success: bool
    camera_id: Optional[str] = None
    flight_id: Optional[str] = None
    flight_status: Optional[str] = "COMPLETED"
    status: str = "DISCONNECTED"
    message: Optional[str] = "Camera disconnected successfully"
    pre_landing_summary: Optional[Dict[str, Any]] = None

class FlightCompleteResponse(BaseModel):
    success: bool
    camera_id: str
    flight_id: str
    flight_status: str
    summary_status: str
    summary: Dict[str, Any]

class FlightSummaryResponse(BaseModel):
    flight_id: str
    camera_id: str
    flight_status: str
    camera_status: str
    summary_status: str
    total_unique_objects: int
    light_on_count: int
    light_off_count: int
    min_confidence: float
    avg_confidence: float
    max_confidence: float
    frames_analyzed: int
    flight_duration_sec: float
    first_detection_time: Optional[str] = None
    last_detection_time: Optional[str] = None
    latest_detected_object: Optional[str] = None
    latest_confidence: Optional[float] = None
    model: str = "runway_light_best.pt"

class CameraListItem(BaseModel):
    camera_id: str
    camera_name: str
    ip_address: Optional[str] = None
    port: int
    protocol: str
    stream_url: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
