from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DetectionEventBase(BaseModel):
    event_type: str
    class_name: str
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    video_timestamp: Optional[float] = None
    location_data: Optional[Dict[str, Any]] = None
    event_data: Optional[Dict[str, Any]] = None


class DetectionEventCreate(DetectionEventBase):
    pass


class DetectionEventResponse(DetectionEventBase):
    id: str
    analysis_result_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaAssetBase(BaseModel):
    media_type: str  # image, video, report
    storage_key: str
    file_name: str
    file_size: Optional[int] = 0


class MediaAssetCreate(MediaAssetBase):
    pass


class MediaAssetResponse(MediaAssetBase):
    id: str
    analysis_result_id: str
    created_at: datetime
    access_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisResultBase(BaseModel):
    module_type: str  # navigation, rod_debris / fod_debris, runway_lights, live_surveillance, offline_surveillance
    session_id: Optional[str] = None
    title: str
    status: Optional[str] = "queued"
    summary: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    media_reference: Optional[str] = None
    error_message: Optional[str] = None


class AnalysisResultCreate(AnalysisResultBase):
    id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    events: Optional[List[DetectionEventCreate]] = None
    media_assets: Optional[List[MediaAssetCreate]] = None


class AnalysisResultUpdate(BaseModel):
    status: Optional[str] = None
    summary: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    media_reference: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class AnalysisResultResponse(AnalysisResultBase):
    id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    events_count: Optional[int] = 0
    media_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class AnalysisResultDetailResponse(AnalysisResultResponse):
    events: List[DetectionEventResponse] = []
    media_assets: List[MediaAssetResponse] = []


class PaginatedResultsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[AnalysisResultResponse]


class ResultsSummaryResponse(BaseModel):
    total_results: int
    by_module: Dict[str, int]
    by_status: Dict[str, int]
    total_events: int
    total_media: int
    recent_results: List[AnalysisResultResponse]


class SurveillanceSessionBase(BaseModel):
    mode: str  # live, offline
    camera_id: Optional[str] = None
    source_reference: Optional[str] = None
    status: Optional[str] = "active"
    metadata_json: Optional[Dict[str, Any]] = None


class SurveillanceSessionCreate(SurveillanceSessionBase):
    id: Optional[str] = None


class SurveillanceSessionResponse(SurveillanceSessionBase):
    id: str
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
