import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
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
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

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

