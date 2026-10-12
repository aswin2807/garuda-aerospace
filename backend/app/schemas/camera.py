from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator

class CameraConnectRequest(BaseModel):
    camera_id: Optional[str] = "camera_01"
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
    status: str
    message: Optional[str] = "Connected to camera"
    stream_url: Optional[str] = ""
    fps: Optional[float] = 0.0
    latency_ms: Optional[float] = 0.0

class CameraStatusResponse(BaseModel):
    camera_id: str
    camera_name: Optional[str] = "Drone Camera"
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
    model: Optional[str] = "FOD_Karhtikeyan.pt"
    stream_url: Optional[str] = ""
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CameraDisconnectResponse(BaseModel):
    success: bool
    camera_id: Optional[str] = None
    status: str = "DISCONNECTED"
    message: Optional[str] = "Camera disconnected successfully"

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
