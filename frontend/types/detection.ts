export interface DebrisCoordinates {
  latitude?: number | null;
  longitude?: number | null;
  crs?: string;
  uncertainty_m?: number | null;
  status: "estimated" | "verified" | "unavailable" | string;
  method?: string;
  formatted?: string;
  source_note?: string;
  ground_point_pixels?: [number, number];
}

export interface DetectionItem {
  model?: "navigation" | "fod" | "runway_light" | string;
  class_id: number;
  class_name: string;
  state?: "ON" | "OFF" | "OFF-GAP" | string;
  track_id?: number;
  inferred?: boolean;
  confidence: number;
  bbox: [number, number, number, number] | { x1: number; y1: number; x2: number; y2: number };
  bbox_xywh?: [number, number, number, number];
  bbox_dict?: { x1: number; y1: number; x2: number; y2: number };
  debris_coordinates?: DebrisCoordinates | null;
  latitude?: number | null;
  longitude?: number | null;
  coordinate_uncertainty_m?: number | null;
  coordinate_status?: string;
  coordinate_formatted?: string;
}

export interface ImageQuality {
  brightness?: number;
  sharpness?: number;
  warnings: string[];
}

export interface DroneTelemetry {
  drone_id?: string;
  latitude: number;
  longitude: number;
  altitude: number;
  speed: number;
  heading: number;
  battery: number;
  status?: string;
  timestamp?: string | number;
}

export interface DroneInfo {
  id: string;
  name: string;
  serial_number: string;
  status: string;
  battery_percentage: number;
  latitude: number;
  longitude: number;
  altitude: number;
  speed: number;
  heading: number;
}

export interface MissionInfo {
  id: string;
  name: string;
  description?: string;
  status: string;
  start_time?: string;
  end_time?: string;
}

export interface AlertItem {
  id?: string;
  event_type?: "RUNWAY_LIGHT_FAULT" | "FOD_DETECTED" | string;
  type?: string;
  severity: "CRITICAL" | "HIGH" | "WARNING" | "MEDIUM" | "INFO" | string;
  class_name?: "LIGHT OFF" | "FOD" | string;
  confidence?: number;
  status?: "POTENTIAL" | "CONFIRMED" | string;
  consecutive_frames?: number;
  message?: string;
  timestamp: string;
  bbox?: any;
}

export interface DetectionSummary {
  nav_count?: number;
  fod_count: number;
  light_on_count: number;
  light_off_count: number;
  light_off_gap_count?: number;
  total_detections: number;
}

export type CameraStatus =
  | "DISCONNECTED"
  | "CONNECTING"
  | "CONNECTED"
  | "LIVE"
  | "CONNECTION LOST"
  | "RECONNECTING"
  | "ERROR";

export interface PreLandingSummary {
  flight_id: string;
  camera_id?: string;
  flight_status: "FLYING" | "ANALYSIS_ACTIVE" | "COMPLETED" | "ERROR" | string;
  camera_status: CameraStatus | string;
  summary_status: "READY" | "PENDING" | string;
  total_unique_objects: number;
  light_on_count: number;
  light_off_count: number;
  min_confidence: number;
  avg_confidence: number;
  max_confidence: number;
  frames_analyzed: number;
  flight_duration_sec: number;
  first_detection_time?: string | null;
  last_detection_time?: string | null;
  latest_detected_object?: string | null;
  latest_confidence?: number | null;
  model?: string;
}

export interface CameraConnectParams {
  rtsp_url?: string;
  flight_id?: string;
  ip?: string;
  port?: number;
  protocol?: "RTSP" | "HTTP" | "HTTPS" | "MJPEG" | "WEBCAM";
  path?: string;
  username?: string;
  password?: string;
  stream_url?: string;
  camera_name?: string;
  camera_id?: string;
  is_simulated?: boolean;
}

export interface CameraConnectResponse {
  success: boolean;
  camera_id: string;
  flight_id?: string;
  flight_status?: string;
  status: CameraStatus | string;
  message?: string;
  stream_url?: string;
  fps?: number;
  latency_ms?: number;
}

export interface CameraStatusResponse {
  camera_id: string;
  camera_name?: string;
  flight_id?: string | null;
  flight_status?: string | null;
  status: CameraStatus | string;
  width?: number;
  height?: number;
  fps: number;
  camera_fps?: number;
  inference_fps?: number;
  latency_ms?: number;
  brightness?: number;
  sharpness?: number;
  warnings?: string[];
  total_detections: number;
  detections: DetectionItem[];
  alerts?: AlertItem[];
  summary?: DetectionSummary;
  latest_detected_object?: string | null;
  latest_confidence?: number | null;
  last_detection_time?: string | null;
  frames_analyzed?: number;
  pre_landing_summary?: PreLandingSummary | null;
  model?: string;
  stream_url?: string;
  error?: string | null;
}

export interface FlightCompleteResponse {
  success: boolean;
  camera_id: string;
  flight_id: string;
  flight_status: string;
  summary_status: string;
  summary: PreLandingSummary;
}

export type FlightSummaryResponse = PreLandingSummary;

export interface CameraDisconnectResponse {
  success: boolean;
  camera_id: string;
  flight_id?: string | null;
  flight_status?: string | null;
  status: string;
  message: string;
  pre_landing_summary?: PreLandingSummary | null;
}

export interface ModelItem {
  model_name: string;
  path: string;
  is_active: boolean;
  size_mb: number;
}

export interface SubModelStatus {
  loaded: boolean;
  model: string;
  status?: string;
  classes?: Record<string, string>;
  confidence?: number;
  error?: string | null;
}

export interface ModelStatusResponse {
  navigation?: SubModelStatus;
  fod?: SubModelStatus;
  runway_light?: SubModelStatus;
  model_name: string;
  model_path: string;
  status: "LOADING" | "READY" | "RUNNING" | "ERROR" | "STOPPED" | string;
  classes: Record<string, string>;
  device: string;
  is_valid: boolean;
  last_inference_time_ms: number;
  error?: string | null;
}

export interface ModelSelectResponse {
  success: boolean;
  model: string;
  status: string;
  message: string;
  classes?: Record<string, string>;
}

export interface CameraListItem {
  camera_id: string;
  camera_name: string;
  ip_address?: string;
  port: number;
  protocol: string;
  stream_url: string;
  status: string;
  created_at: string;
}

export interface DetectionCounts {
  navigation: number;
  fod: number;
  light_on: number;
  light_off: number;
  confirmed_faults: number;
}

export interface SessionTotals {
  navigation: number;
  fod: number;
  light_on: number;
  light_off: number;
  confirmed_faults: number;
  total_unique?: number;
}

export interface PerformanceMetrics {
  stream_fps: number;
  inference_fps: number;
  inference_ms: number;
  latency_ms?: number;
}

export interface PipelineHealth {
  video: string;
  frame_reader: string;
  navigation: string;
  fod: string;
  runway_light: string;
  database: string;
  websocket: string;
}

export type AnalysisMode = "IMAGE" | "VIDEO" | "LIVE_CAMERA";

export type AnalysisType = "NAVIGATION" | "FOD" | "RUNWAY_LIGHT";

export interface RunwayRowResult {
  row: string;
  total: number;
  on: number;
  off: number;
  unknown: number;
  faults: number;
}

export interface RunwayLightSlot {
  light_id: string; // e.g. "R1-C1"
  row_id: number;
  column_id: number;
  status: "ON" | "OFF" | "UNKNOWN" | string;
  confidence: number;
  is_confirmed: boolean;
  track_id?: number;
  consecutive_off?: number;
  total_observations?: number;
  bbox?: [number, number, number, number];
}

export interface RunwayFaultItem {
  light_id: string;
  row_id: number;
  column_id: number;
  status: string;
  confidence: number;
  consecutive_off?: number;
  total_observations?: number;
  bbox?: [number, number, number, number];
}

export interface RunwayLightSummaryData {
  job_id: string;
  status?: string;
  total_lights: number;
  lights_on: number;
  lights_off: number;
  lights_unknown: number;
  confirmed_faults: number;
  total_rows: number;
  total_columns: number;
  average_confidence: number;
  processed_frames: number;
  analysis_duration: number;
  matrix: RunwayLightSlot[];
  row_results?: RunwayRowResult[];
  faults: RunwayFaultItem[];
}

export type AnalysisStatus =
  | "IDLE"
  | "QUEUED"
  | "ANALYZING"
  | "PAUSED"
  | "COMPLETED"
  | "FAILED"
  | "UPLOADED"
  | "CANCELLED";

export type AnalysisJobStatus = AnalysisStatus;

export interface AnalysisJob {
  id?: string;
  job_id: string;
  filename: string;
  video_name?: string;
  media_type: "VIDEO" | "IMAGE";
  analysis_type?: AnalysisType | string;
  status: AnalysisJobStatus;
  total_frames: number;
  frames_total?: number;
  processed_frames: number;
  frames_processed?: number;
  progress: number;
  processing_fps: number;
  fps?: number;
  video_fps: number;
  duration_seconds: number;
  elapsed_seconds: number;
  elapsed_time?: number;
  remaining_seconds: number;
  eta_seconds?: number;
  estimated_finish_time?: string;
  nav_count: number;
  navigation_count?: number;
  fod_count: number;
  light_on_count: number;
  light_off_count: number;
  confirmed_faults: number;
  total_lights?: number;
  unknown_light_count?: number;
  rows_detected?: number;
  row_results?: RunwayRowResult[];
  matrix?: RunwayLightSlot[];
  faults?: RunwayFaultItem[];
  unique_nav_count?: number;
  unique_fod_count?: number;
  total_detections?: number;
  total_frame_detections?: number;
  speed_ratio?: number;
  class_counts?: Record<string, number>;
  unique_light_on?: number;
  unique_light_off?: number;
  avg_confidence?: number;
  average_confidence?: number;
  avg_inference_ms?: number;
  inference_ms?: number;
  annotated_media_path?: string;
  report_csv_path?: string;
  report_json_path?: string;
  sample_detections?: DetectionItem[];
  error_message?: string;
  createdAt?: string;
  statistics?: Record<string, any>;
  counts?: Record<string, number>;
  performance?: Record<string, number>;
}
