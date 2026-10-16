from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class DebrisCoordinates(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    crs: str = "WGS84"
    uncertainty_m: Optional[float] = None
    status: str = "unavailable"  # "estimated", "verified", "unavailable"
    method: Optional[str] = "none"
    formatted: Optional[str] = None
    source_note: Optional[str] = None
    ground_point_pixels: Optional[List[float]] = None


class AnalysisJobCreateResponse(BaseModel):
    id: Optional[str] = None
    job_id: str
    analysis_type: str = "NAVIGATION"
    video_name: Optional[str] = None
    filename: str
    file_path: Optional[str] = None
    media_type: str = "VIDEO"
    status: str = "QUEUED"
    progress: float = 0.0
    total_frames: int = 0
    frames_total: Optional[int] = None
    duration_seconds: float = 0.0
    video_fps: float = 30.0
    message: str = "Media uploaded and queued"

class AnalysisJobStatusResponse(BaseModel):
    id: Optional[str] = None
    job_id: str
    analysis_type: str = "NAVIGATION"
    video_name: Optional[str] = None
    filename: str
    media_type: str = "VIDEO"
    status: str
    total_frames: int
    frames_total: Optional[int] = None
    processed_frames: int
    frames_processed: Optional[int] = None
    progress: float
    processing_fps: float
    fps: Optional[float] = None
    video_fps: float = 30.0
    inference_ms: Optional[float] = None
    elapsed_seconds: float = 0.0
    remaining_seconds: float = 0.0
    eta_seconds: Optional[float] = None
    estimated_finish_time: Optional[str] = None
    nav_count: int = 0
    navigation_count: Optional[int] = None
    fod_count: int = 0
    light_on_count: int = 0
    light_off_count: int = 0
    confirmed_faults: int = 0
    unknown_light_count: int = 0
    rows_detected: int = 0
    row_results: Optional[List[Dict[str, Any]]] = None
    total_detections: int = 0
    speed_ratio: float = 0.0
    class_counts: Optional[Dict[str, int]] = None
    counts: Optional[Dict[str, int]] = None
    performance: Optional[Dict[str, float]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    model_path: Optional[str] = None
    model_version: Optional[str] = None
    confidence_threshold: Optional[float] = None
    outcome_status: Optional[str] = None

class AnalysisJobResultsResponse(BaseModel):
    id: Optional[str] = None
    job_id: str
    analysis_type: str = "NAVIGATION"
    video_name: Optional[str] = None
    filename: str
    media_type: str = "VIDEO"
    status: str
    total_frames: int
    frames_total: Optional[int] = None
    processed_frames: int
    frames_processed: Optional[int] = None
    duration_seconds: float = 0.0
    processing_time_formatted: str = "00:00"
    nav_count: int = 0
    navigation_count: Optional[int] = None
    fod_count: int = 0
    total_lights: Optional[int] = None
    light_on_count: int = 0
    light_off_count: int = 0
    confirmed_faults: int = 0
    unknown_light_count: int = 0
    rows_detected: int = 0
    row_results: Optional[List[Dict[str, Any]]] = None
    matrix: Optional[List[Dict[str, Any]]] = None
    faults: Optional[List[Dict[str, Any]]] = None
    unique_nav_count: int = 0
    unique_fod_count: int = 0
    unique_light_on: int = 0
    unique_light_off: int = 0
    total_detections: int = 0
    speed_ratio: float = 0.0
    class_counts: Optional[Dict[str, int]] = None
    avg_confidence: float = 0.0
    average_confidence: Optional[float] = None
    avg_inference_ms: float = 0.0
    inference_ms: Optional[float] = None
    annotated_media_path: Optional[str] = None
    file_path: Optional[str] = None
    video_fps: Optional[float] = 30.0
    report_csv_path: Optional[str] = None
    report_json_path: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    error_message: Optional[str] = None
    model_path: Optional[str] = None
    model_version: Optional[str] = None
    confidence_threshold: Optional[float] = None
    outcome_status: Optional[str] = None
    sample_detections: List[Dict[str, Any]] = []

class RunwayLightSummaryResponse(BaseModel):
    job_id: str
    status: Optional[str] = "COMPLETED"
    total_lights: int = 0
    lights_on: int = 0
    lights_off: int = 0
    lights_unknown: int = 0
    confirmed_faults: int = 0
    total_rows: int = 0
    total_columns: int = 0
    average_confidence: float = 0.0
    processed_frames: int = 0
    analysis_duration: float = 0.0
    matrix: List[Dict[str, Any]] = []
    row_results: Optional[List[Dict[str, Any]]] = None
    faults: List[Dict[str, Any]] = []

class ImageAnalysisResponse(BaseModel):
    id: Optional[str] = None
    job_id: str
    analysis_type: str = "NAVIGATION"
    filename: str
    detections: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    annotated_image_url: Optional[str] = None
    processing_time_ms: float = 0.0
