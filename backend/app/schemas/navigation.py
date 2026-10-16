import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class WaypointItem(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: f"wp_{uuid.uuid4().hex[:8]}")
    order: int
    latitude: float
    longitude: float
    altitude_agl_m: Optional[float] = 30.0
    notes: Optional[str] = None
    validation_status: Optional[str] = "VALID"

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if v is None or not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return round(float(v), 7)

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if v is None or not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return round(float(v), 7)

    @field_validator("altitude_agl_m")
    @classmethod
    def validate_alt(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0.0:
            raise ValueError("Altitude must be non-negative")
        return round(float(v), 1) if v is not None else 30.0


class RouteCalculateRequest(BaseModel):
    start_latitude: float
    start_longitude: float
    target_latitude: float
    target_longitude: float
    target_name: Optional[str] = "Target Destination"
    waypoints: Optional[List[WaypointItem]] = []
    speed_mps: Optional[float] = 10.0  # Cruise speed in m/s (default 10 m/s = 36 km/h)
    speed_source: Optional[str] = "USER_CONFIGURED"  # USER_CONFIGURED or MEASURED_TELEMETRY
    max_range_limit_m: Optional[float] = 3000.0  # Configurable operational planning limit (FR-08)

    @field_validator("start_latitude", "target_latitude")
    @classmethod
    def validate_lats(cls, v: float) -> float:
        if v is None or not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return round(float(v), 7)

    @field_validator("start_longitude", "target_longitude")
    @classmethod
    def validate_lons(cls, v: float) -> float:
        if v is None or not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return round(float(v), 7)

    @field_validator("speed_mps")
    @classmethod
    def validate_speed(cls, v: Optional[float]) -> float:
        if v is None or v <= 0.0:
            raise ValueError("Speed must be strictly greater than 0 m/s")
        if v > 60.0:
            raise ValueError("Speed exceeds maximum allowed drone flight speed (60 m/s = 216 km/h)")
        return round(float(v), 2)


class RouteSegment(BaseModel):
    from_name: str
    to_name: str
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_m: float
    initial_bearing_deg: float
    compass_direction: str


class RouteCalculateResponse(BaseModel):
    valid: bool
    status: str
    start_coordinates: Dict[str, float]
    target_coordinates: Dict[str, float]
    target_name: Optional[str] = None
    waypoints_count: int
    total_distance_m: float
    straight_line_distance_m: float
    detour_percentage: float = 0.0
    estimated_time_seconds: Optional[float] = None
    estimated_time_formatted: str
    speed_used_mps: float = 10.0
    speed_source: str = "USER_CONFIGURED"
    calculation_method: str = "WGS84_GEODESIC"
    assumptions: List[str] = []
    segments: List[RouteSegment]
    all_points: List[Dict[str, Any]]
    warnings: List[str] = []


class RouteSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    drone_id: Optional[str] = None
    start_latitude: float
    start_longitude: float
    target_latitude: float
    target_longitude: float
    target_name: Optional[str] = "Target Destination"
    waypoints: Optional[List[WaypointItem]] = []
    speed_mps: Optional[float] = 10.0
    status: Optional[str] = "PLANNED"

    @field_validator("start_latitude", "target_latitude")
    @classmethod
    def validate_lats(cls, v: float) -> float:
        if v is None or not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return round(float(v), 7)

    @field_validator("start_longitude", "target_longitude")
    @classmethod
    def validate_lons(cls, v: float) -> float:
        if v is None or not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return round(float(v), 7)


class RouteResponse(BaseModel):
    id: str
    name: str
    drone_id: Optional[str] = None
    start_latitude: float
    start_longitude: float
    target_latitude: float
    target_longitude: float
    target_name: Optional[str] = None
    total_distance_m: float
    estimated_time_s: float
    waypoints: List[Dict[str, Any]]
    status: str
    created_at: str
    updated_at: str


class DebrisTargetItem(BaseModel):
    id: str
    class_name: str
    confidence: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    uncertainty_m: Optional[float] = None
    status: str
    formatted: Optional[str] = None
    source_module: str
    timestamp: Optional[str] = None
    is_navigable: bool
    navigable_reason: Optional[str] = None


class GuidanceCalculationRequest(BaseModel):
    drone_latitude: float
    drone_longitude: float
    drone_heading: Optional[float] = None
    drone_speed: Optional[float] = None
    target_latitude: float
    target_longitude: float
    waypoint_order: Optional[int] = None

    @field_validator("drone_latitude", "target_latitude")
    @classmethod
    def validate_lats(cls, v: float) -> float:
        if v is None or not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return round(float(v), 7)

    @field_validator("drone_longitude", "target_longitude")
    @classmethod
    def validate_lons(cls, v: float) -> float:
        if v is None or not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return round(float(v), 7)


class GuidanceCalculationResponse(BaseModel):
    distance_to_target_m: float
    bearing_to_target_deg: float
    compass_direction: str
    relative_bearing_deg: Optional[float] = None
    steering_instruction: str
    arrival_status: str
    is_arrived: bool


class LiveTelemetryResponse(BaseModel):
    connected: bool
    drone_id: Optional[str] = None
    drone_name: Optional[str] = None
    telemetry_source: str = "OFFLINE"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    battery: Optional[float] = None
    is_stale: bool = True
    has_gps_fix: bool = False
    status: str = "OFFLINE"  # CONNECTED, STALE, OFFLINE, SIMULATED, INVALID_TELEMETRY
    message: str = ""
    last_heartbeat: Optional[str] = None
    age_seconds: Optional[float] = None
    stale_threshold_seconds: float = 15.0
    estimated_uncertainty_m: Optional[float] = None
