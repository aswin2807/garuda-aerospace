import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(150), nullable=False)
    role = Column(String(50), default="OPERATOR")  # ADMIN, OPERATOR, VIEWER
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=True)
    account_status = Column(String(50), default="ACTIVE")  # ACTIVE, DISABLED
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    session_invalidated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    password_resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")
    email_verifications = relationship("EmailVerification", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return self.name

    @full_name.setter
    def full_name(self, value: str) -> None:
        self.name = value


class EmailVerification(Base):
    """
    Email verification tokens for activating newly registered user accounts.
    """
    __tablename__ = "email_verifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 hex
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    user = relationship("User", back_populates="email_verifications")


class PasswordReset(Base):
    """
    Password reset tokens for secure authentication recovery.
    """
    __tablename__ = "password_resets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 hex
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    user = relationship("User", back_populates="password_resets")


class RevokedToken(Base):
    """
    Revoked JWT session tokens invalidated on logout.
    """
    __tablename__ = "revoked_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), default=get_utc_now)


class Drone(Base):
    __tablename__ = "drones"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False)
    serial_number = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(50), default="IDLE")  # OFFLINE, IDLE, ACTIVE, EMERGENCY
    battery_percentage = Column(Float, default=100.0)
    latitude = Column(Float, default=12.9012)
    longitude = Column(Float, default=80.2273)
    altitude = Column(Float, default=120.0)
    speed = Column(Float, default=32.0)
    heading = Column(Float, default=184.0)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    missions = relationship("Mission", back_populates="drone")
    telemetry_records = relationship("Telemetry", back_populates="drone")
    detections = relationship("Detection", back_populates="drone")
    alerts = relationship("Alert", back_populates="drone")

class Mission(Base):
    __tablename__ = "missions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    drone_id = Column(String(36), ForeignKey("drones.id"), nullable=True)
    status = Column(String(50), default="PLANNED")  # PLANNED, ACTIVE, PAUSED, COMPLETED, CANCELLED
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    drone = relationship("Drone", back_populates="missions")
    detections = relationship("Detection", back_populates="mission")

class Detection(Base):
    __tablename__ = "detections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(64), index=True, nullable=True)
    session_id = Column(String(100), index=True, nullable=True)
    camera_id = Column(String(100), nullable=True)
    mission_id = Column(String(36), ForeignKey("missions.id"), nullable=True)
    drone_id = Column(String(36), ForeignKey("drones.id"), nullable=True)
    analysis_type = Column(String(50), default="NAVIGATION", index=True, nullable=True)
    model_name = Column(String(100), nullable=True)
    class_name = Column(String(100), nullable=False)
    class_id = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False)
    x = Column(Float, nullable=False, default=0.0)
    y = Column(Float, nullable=False, default=0.0)
    width = Column(Float, nullable=False, default=0.0)
    height = Column(Float, nullable=False, default=0.0)
    x1 = Column(Float, nullable=True, default=0.0)
    y1 = Column(Float, nullable=True, default=0.0)
    x2 = Column(Float, nullable=True, default=0.0)
    y2 = Column(Float, nullable=True, default=0.0)
    track_id = Column(Integer, nullable=True)
    frame_number = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now)
    image_url = Column(String(512), nullable=True)
    # Debris Geographical Coordinates (FR-01, FR-06, FR-10)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    coordinate_uncertainty_m = Column(Float, nullable=True)
    coordinate_status = Column(String(50), nullable=True, default="unavailable")
    coordinate_method = Column(String(100), nullable=True)
    coordinate_crs = Column(String(50), nullable=True, default="WGS84")
    coordinate_formatted = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    drone = relationship("Drone", back_populates="detections")
    mission = relationship("Mission", back_populates="detections")

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True)
    source = Column(String(512), nullable=False)
    source_type = Column(String(50), default="VIDEO_FILE")  # VIDEO_FILE, CAMERA, WEBCAM
    status = Column(String(50), default="RUNNING")  # RUNNING, COMPLETED, STOPPED, ERROR
    start_time = Column(DateTime(timezone=True), default=get_utc_now)
    end_time = Column(DateTime(timezone=True), nullable=True)
    total_frames = Column(Integer, default=0)
    processed_frames = Column(Integer, default=0)
    nav_count = Column(Integer, default=0)
    fod_count = Column(Integer, default=0)
    light_on_count = Column(Integer, default=0)
    light_off_count = Column(Integer, default=0)
    confirmed_faults = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    avg_inference_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

class FrameRecord(Base):
    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=False)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now)
    stream_fps = Column(Float, default=30.0)
    inference_ms = Column(Float, default=0.0)
    nav_count = Column(Integer, default=0)
    fod_count = Column(Integer, default=0)
    light_on_count = Column(Integer, default=0)
    light_off_count = Column(Integer, default=0)

class TrackRecord(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=False)
    track_id = Column(Integer, nullable=False)
    model_name = Column(String(100), nullable=False)
    class_name = Column(String(100), nullable=False)
    first_seen_frame = Column(Integer, default=0)
    last_seen_frame = Column(Integer, default=0)
    total_frames = Column(Integer, default=1)
    avg_confidence = Column(Float, default=0.0)

class RunwayFaultRecord(Base):
    __tablename__ = "runway_faults"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(64), index=True, nullable=True)
    session_id = Column(String(100), index=True, nullable=True)
    track_id = Column(Integer, nullable=True)
    first_detected_frame = Column(Integer, default=0)
    last_detected_frame = Column(Integer, default=0)
    status = Column(String(50), default="POTENTIAL")  # POTENTIAL, CONFIRMED
    consecutive_frames = Column(Integer, default=1)
    confidence = Column(Float, default=0.0)
    first_detected = Column(DateTime(timezone=True), default=get_utc_now)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drone_id = Column(String(36), ForeignKey("drones.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=False)
    speed = Column(Float, nullable=False)
    heading = Column(Float, nullable=False)
    battery = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now)

    drone = relationship("Drone", back_populates="telemetry_records")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(100), nullable=True)
    camera_id = Column(String(100), nullable=True)
    drone_id = Column(String(36), ForeignKey("drones.id"), nullable=True)
    type = Column(String(100), nullable=False)  # LOW_BATTERY, HIGH_RISK, OBJECT_PROXIMITY, FOD_DETECTED, RUNWAY_LIGHT_FAULT
    severity = Column(String(50), default="WARNING")  # INFO, WARNING, CRITICAL
    message = Column(Text, nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now)

    drone = relationship("Drone", back_populates="alerts")

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    weights_path = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    camera_id = Column(String(100), unique=True, index=True, nullable=False)
    camera_name = Column(String(150), nullable=False, default="Drone Camera 01")
    ip_address = Column(String(100), nullable=True)
    port = Column(Integer, default=554)
    protocol = Column(String(50), default="RTSP")  # RTSP, HTTP, MJPEG, WEBCAM
    stream_path = Column(String(255), default="/stream")
    stream_url = Column(String(512), nullable=False)
    username = Column(String(100), nullable=True)
    encrypted_password = Column(String(255), nullable=True)
    status = Column(String(50), default="DISCONNECTED")  # DISCONNECTED, CONNECTING, LIVE, CONNECTION_LOST, RECONNECTING
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String(64), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    media_type = Column(String(20), default="VIDEO")  # VIDEO, IMAGE, BATCH_IMAGE, BATCH_VIDEO
    analysis_type = Column(String(50), default="NAVIGATION", index=True, nullable=False)  # NAVIGATION, FOD, RUNWAY_LIGHT
    status = Column(String(50), default="UPLOADED")   # UPLOADED, QUEUED, ANALYZING, PAUSED, COMPLETED, CANCELLED, FAILED
    total_frames = Column(Integer, default=0)
    processed_frames = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    processing_fps = Column(Float, default=0.0)
    video_fps = Column(Float, default=30.0)
    duration_seconds = Column(Float, default=0.0)
    elapsed_seconds = Column(Float, default=0.0)
    estimated_remaining_seconds = Column(Float, default=0.0)
    estimated_finish_time = Column(String(50), nullable=True)
    nav_count = Column(Integer, default=0)
    fod_count = Column(Integer, default=0)
    light_on_count = Column(Integer, default=0)
    light_off_count = Column(Integer, default=0)
    confirmed_faults = Column(Integer, default=0)
    unknown_light_count = Column(Integer, default=0)
    rows_detected = Column(Integer, default=0)
    row_results = Column(Text, nullable=True)  # JSON-serialized list of row breakdown dicts
    unique_nav_count = Column(Integer, default=0)
    unique_fod_count = Column(Integer, default=0)
    total_detections = Column(Integer, default=0)  # Cumulative total frame detections across all frames
    speed_ratio = Column(Float, default=0.0)       # Processing time / source video duration
    class_counts = Column(Text, nullable=True)     # JSON-serialized counts per detected class category
    unique_light_on = Column(Integer, default=0)
    unique_light_off = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    avg_inference_ms = Column(Float, default=0.0)
    annotated_media_path = Column(String(512), nullable=True)
    report_csv_path = Column(String(512), nullable=True)
    report_json_path = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    model_path = Column(String(512), nullable=True)
    model_version = Column(String(64), nullable=True)
    confidence_threshold = Column(Float, default=0.20)
    outcome_status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

class AnalysisFrame(Base):
    __tablename__ = "analysis_frames"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), index=True, nullable=False)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(Float, default=0.0)
    processed_at = Column(DateTime(timezone=True), default=get_utc_now)
    processing_time_ms = Column(Float, default=0.0)
    nav_count = Column(Integer, default=0)
    fod_count = Column(Integer, default=0)
    light_on_count = Column(Integer, default=0)
    light_off_count = Column(Integer, default=0)


class RunwayLightResult(Base):
    __tablename__ = "runway_light_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), index=True, nullable=False)
    light_id = Column(String(32), index=True, nullable=False)  # e.g., "R1-C1"
    row_id = Column(Integer, nullable=False)
    column_id = Column(Integer, nullable=False)
    frame_id = Column(Integer, nullable=False)
    timestamp = Column(Float, default=0.0)
    class_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # "ON", "OFF", "UNKNOWN"
    confidence = Column(Float, nullable=False, default=0.0)
    x1 = Column(Float, nullable=False, default=0.0)
    y1 = Column(Float, nullable=False, default=0.0)
    x2 = Column(Float, nullable=False, default=0.0)
    y2 = Column(Float, nullable=False, default=0.0)
    track_id = Column(Integer, nullable=True)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)


class RunwayLightSummary(Base):
    __tablename__ = "runway_light_summary"

    job_id = Column(String(64), primary_key=True)
    total_lights = Column(Integer, default=0)
    lights_on = Column(Integer, default=0)
    lights_off = Column(Integer, default=0)
    lights_unknown = Column(Integer, default=0)
    confirmed_faults = Column(Integer, default=0)
    total_rows = Column(Integer, default=0)
    total_columns = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.0)
    processed_frames = Column(Integer, default=0)
    analysis_duration = Column(Float, default=0.0)
    matrix_json = Column(Text, nullable=True)  # JSON-serialized list of persistent light slots
    faults_json = Column(Text, nullable=True)  # JSON-serialized list of confirmed fault records
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)


# ==============================================================================
# CENTRALIZED DATABASE MODELS (PRD: Centralized Results Management System)
# ==============================================================================

def generate_result_id():
    return f"res_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

def generate_event_id():
    return f"evt_{uuid.uuid4().hex[:12]}"

def generate_media_id():
    return f"med_{uuid.uuid4().hex[:12]}"

def generate_surveillance_session_id():
    return f"SES-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

def generate_audit_id():
    return f"aud_{uuid.uuid4().hex[:12]}"


class AnalysisResult(Base):
    """
    Centralized analysis result table for all modules (PRD Section 5 Table 1).
    Stores results from: navigation, rod_debris / fod_debris, runway_lights,
    live_surveillance, and offline_surveillance.
    """
    __tablename__ = "analysis_results"

    id = Column(String(64), primary_key=True, default=generate_result_id)
    module_type = Column(String(50), nullable=False, index=True)  # navigation, rod_debris, runway_lights, live_surveillance, offline_surveillance
    session_id = Column(String(100), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default="queued", index=True, nullable=False)  # queued, processing, completed, failed
    summary = Column(Text, nullable=True)
    result_data = Column(JSON, nullable=True)  # Structured module-specific metrics, counts, etc.
    started_at = Column(DateTime(timezone=True), default=get_utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)
    media_reference = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)

    events = relationship("DetectionEvent", back_populates="result", cascade="all, delete-orphan")
    media_assets = relationship("MediaAsset", back_populates="result", cascade="all, delete-orphan")


class DetectionEvent(Base):
    """
    Granular detection events associated with an analysis result (PRD Section 5 Table 2).
    """
    __tablename__ = "detection_events"

    id = Column(String(64), primary_key=True, default=generate_event_id)
    analysis_result_id = Column(String(64), ForeignKey("analysis_results.id"), index=True, nullable=False)
    event_type = Column(String(100), nullable=False, index=True)  # OBSTACLE, FOD_DETECTED, LIGHT_ON, LIGHT_OFF, FAULT, MOTION, etc.
    class_name = Column(String(100), nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, index=True)
    video_timestamp = Column(Float, nullable=True)  # Timestamp offset in seconds within video
    location_data = Column(JSON, nullable=True)     # Bounding box [x1, y1, x2, y2] or coordinates
    event_data = Column(JSON, nullable=True)        # Additional event metadata

    result = relationship("AnalysisResult", back_populates="events")


class MediaAsset(Base):
    """
    Associated media assets (images, videos, reports) for an analysis result (PRD Section 5 Table 3).
    """
    __tablename__ = "media_assets"

    id = Column(String(64), primary_key=True, default=generate_media_id)
    analysis_result_id = Column(String(64), ForeignKey("analysis_results.id"), index=True, nullable=False)
    media_type = Column(String(50), nullable=False)  # image, video, report
    storage_key = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    result = relationship("AnalysisResult", back_populates="media_assets")


class SurveillanceSessionRecord(Base):
    """
    Surveillance sessions tracking live or offline surveillance operations (PRD Section 5 Table 4).
    """
    __tablename__ = "surveillance_sessions"

    id = Column(String(100), primary_key=True, default=generate_surveillance_session_id)
    mode = Column(String(50), nullable=False, index=True)  # live, offline
    camera_id = Column(String(100), nullable=True, index=True)
    source_reference = Column(String(512), nullable=True)
    started_at = Column(DateTime(timezone=True), default=get_utc_now)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="active", index=True)  # active, completed, stopped, error
    metadata_json = Column(JSON, nullable=True)


class AuditLog(Base):
    """
    Audit log records for tracking critical system and data operations (PRD Section 5 Table 5).
    """
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, default=generate_audit_id)
    user_id = Column(String(64), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, index=True)


# ==============================================================================
# NAVIGATION MODULE & ROUTE PLANNING MODELS (PRD FR-10)
# ==============================================================================

def generate_route_id():
    return f"route_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


class NavigationRoute(Base):
    """
    Persistent drone navigation routes with waypoints (PRD FR-10).
    """
    __tablename__ = "navigation_routes"

    id = Column(String(64), primary_key=True, default=generate_route_id)
    name = Column(String(200), nullable=False)
    drone_id = Column(String(36), ForeignKey("drones.id"), nullable=True)
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    target_latitude = Column(Float, nullable=False)
    target_longitude = Column(Float, nullable=False)
    target_name = Column(String(200), nullable=True)
    total_distance_m = Column(Float, default=0.0)
    estimated_time_s = Column(Float, default=0.0)
    waypoints_json = Column(JSON, nullable=False, default=list)  # list of {order, latitude, longitude, altitude_agl_m, notes}
    status = Column(String(50), default="PLANNED", index=True)  # PLANNED, ACTIVE, COMPLETED, ARCHIVED
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)
