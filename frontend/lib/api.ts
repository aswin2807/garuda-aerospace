const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let _inMemoryToken: string | null = null;

export function setApiSessionToken(token: string | null) {
  _inMemoryToken = token;
}

export function getApiSessionToken(): string | null {
  return _inMemoryToken;
}

async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  if (_inMemoryToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${_inMemoryToken}`);
  }
  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "include",
  });
  if (
    res.status === 401 &&
    typeof window !== "undefined" &&
    !url.includes("/auth/login") &&
    !url.includes("/auth/me")
  ) {
    window.dispatchEvent(new CustomEvent("garuda:session-expired"));
  }
  return res;
}

export async function detectImageFile(file: File, confidence?: number, droneId?: string) {

  const formData = new FormData();
  formData.append("file", file);
  if (confidence !== undefined) formData.append("confidence", confidence.toString());
  if (droneId) formData.append("drone_id", droneId);

  const res = await apiFetch(`${API_BASE}/api/v1/detection/image`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Inference failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getDrones() {
  const res = await apiFetch(`${API_BASE}/api/v1/drones`);
  if (!res.ok) throw new Error("Failed to fetch drones");
  return res.json();
}

export async function getMissions() {
  const res = await apiFetch(`${API_BASE}/api/v1/missions`);
  if (!res.ok) throw new Error("Failed to fetch missions");
  return res.json();
}

export async function getTelemetry(droneId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/drones/${droneId}/telemetry`);
  if (!res.ok) throw new Error("Failed to fetch telemetry");
  return res.json();
}

export async function getDetectionHistory(params?: { droneId?: string; minConfidence?: number }) {
  const url = new URL(`${API_BASE}/api/v1/detection/history`);
  if (params?.droneId) url.searchParams.append("drone_id", params.droneId);
  if (params?.minConfidence) url.searchParams.append("min_confidence", params.minConfidence.toString());

  const res = await apiFetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch detection history");
  return res.json();
}

export async function checkBackendHealth() {
  try {
    const res = await apiFetch(`${API_BASE}/health`);
    return await res.json();
  } catch {
    return { api: "offline", database: "offline", model: "offline" };
  }
}

// ==========================================
// IP Camera / Live Stream Management Endpoints
// ==========================================

import type {
  CameraConnectParams,
  CameraConnectResponse,
  CameraStatusResponse,
  CameraDisconnectResponse,
  CameraListItem,
  FlightCompleteResponse,
  FlightSummaryResponse,
  ModelItem,
  ModelStatusResponse,
  ModelSelectResponse,
} from "../types/detection";

export async function connectCamera(params: CameraConnectParams): Promise<CameraConnectResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/camera/connect`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to connect camera (${res.status})`);
  }
  return data;
}

export async function disconnectCamera(cameraId: string): Promise<CameraDisconnectResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/camera/${encodeURIComponent(cameraId)}/disconnect`, {
    method: "POST",
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to disconnect camera (${res.status})`);
  }
  return data;
}

export async function completeFlight(cameraId: string): Promise<FlightCompleteResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/camera/${encodeURIComponent(cameraId)}/complete-flight`, {
    method: "POST",
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to complete flight (${res.status})`);
  }
  return data;
}

export async function getFlightSummary(cameraId: string): Promise<FlightSummaryResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/camera/${encodeURIComponent(cameraId)}/flight-summary`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to get flight summary (${res.status})`);
  }
  return data;
}

export async function getCameraStatus(cameraId: string): Promise<CameraStatusResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/camera/${encodeURIComponent(cameraId)}/status`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to get camera status (${res.status})`);
  }
  return data;
}

export async function getCameras(): Promise<CameraListItem[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/camera/list`);
  if (!res.ok) throw new Error("Failed to list cameras");
  return res.json();
}

export function getCameraFeedUrl(cameraId: string): string {
  return `${API_BASE}/api/v1/camera/${encodeURIComponent(cameraId)}/feed`;
}

export function getCameraWsUrl(cameraId: string): string {
  const wsBase = process.env.NEXT_PUBLIC_WS_URL || API_BASE.replace(/^http/, "ws");
  return `${wsBase}/ws/v1/camera/${encodeURIComponent(cameraId)}/stream`;
}

// ==========================================
// YOLO / FOD Model Management Endpoints
// ==========================================

export async function getModelStatus(): Promise<ModelStatusResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/models/status`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to fetch model status (${res.status})`);
  }
  return data;
}

export async function getModels(): Promise<ModelItem[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/models/list`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to list models (${res.status})`);
  }
  return data;
}

export async function selectModel(modelName: string): Promise<ModelSelectResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/models/select`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ model: modelName }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to switch model to ${modelName} (${res.status})`);
  }
  return data;
}

export async function getNavigationClasses(): Promise<{ classes: string[]; class_map?: Record<string, string> }> {
  const res = await apiFetch(`${API_BASE}/api/v1/models/navigation/classes`);
  if (!res.ok) {
    throw new Error(`Failed to fetch navigation classes (${res.status})`);
  }
  return res.json();
}

// ==========================================
// Video Analysis & Session Endpoints (PRD Section 30)
// ==========================================

export async function startVideoAnalysis(source: string, loop: boolean = false) {
  const res = await apiFetch(`${API_BASE}/api/v1/video/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, loop }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to start video analysis");
  return data;
}

export async function stopVideoAnalysis(sessionId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/video/${encodeURIComponent(sessionId)}/stop`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to stop video analysis");
  return data;
}

export async function getVideoSessionStatus(sessionId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/video/${encodeURIComponent(sessionId)}/status`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to get video status");
  return data;
}

export async function getSessionStatistics(sessionId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/session/${encodeURIComponent(sessionId)}/statistics`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to get session statistics");
  return data;
}

export async function resetSession(sessionId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/session/${encodeURIComponent(sessionId)}/reset`, {
    method: "POST",
  });
  return res.json();
}

export async function getPipelineDebug() {
  const res = await apiFetch(`${API_BASE}/api/v1/debug/pipeline`);
  if (!res.ok) throw new Error("Failed to fetch debug pipeline");
  return res.json();
}

export async function getPipelineHealth() {
  const res = await apiFetch(`${API_BASE}/api/v1/debug/pipeline/health`);
  if (!res.ok) throw new Error("Failed to fetch pipeline health");
  return res.json();
}

// Analysis API Endpoints (PRD Section 38 & Isolated Modules)
export async function uploadAnalysisMedia(file: File, analysisType: string = "NAVIGATION") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analysis_type", analysisType);
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload media");
  return data;
}

export async function uploadAnalysisVideo(file: File, analysisType: string = "NAVIGATION") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analysis_type", analysisType);
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/videos`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload video");
  return data;
}

export async function uploadAnalysisImage(file: File, analysisType: string = "NAVIGATION") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analysis_type", analysisType);
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/images`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload image");
  return data;
}

// Module-Specific API Endpoints
export async function uploadNavigationMedia(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload navigation media");
  return data;
}

export async function getNavigationHistory() {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/history`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch navigation history");
  return data;
}

export async function uploadFodMedia(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiFetch(`${API_BASE}/api/v1/fod/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload FOD media");
  return data;
}

export async function getFodHistory() {
  const res = await apiFetch(`${API_BASE}/api/v1/fod/history`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch FOD history");
  return data;
}

export async function uploadRunwayLightMedia(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiFetch(`${API_BASE}/api/v1/runway-light/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload runway light media");
  return data;
}

export async function getRunwayLightHistory() {
  const res = await apiFetch(`${API_BASE}/api/v1/runway-light/history`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch runway light history");
  return data;
}

export async function startAnalysis(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/start`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to start analysis");
  return data;
}

export async function pauseAnalysis(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/pause`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to pause analysis");
  return data;
}

export async function resumeAnalysis(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/resume`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to resume analysis");
  return data;
}

export async function cancelAnalysis(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to cancel analysis");
  return data;
}

export async function getAnalysisStatus(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch analysis status");
  return data;
}

export async function getAnalysisResults(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/results`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch analysis results");
  return data;
}

export async function getAnalysisJobs(analysisType?: string) {
  const url = new URL(`${API_BASE}/api/v1/analysis/jobs/all`);
  if (analysisType) {
    url.searchParams.append("analysis_type", analysisType);
  }
  const res = await apiFetch(url.toString());
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch analysis jobs");
  return data;
}

// ==========================================
// Garuda Aerospace Command Centre API Endpoints
// ==========================================

export async function getCommandCentreStatus() {
  const res = await apiFetch(`${API_BASE}/api/v1/command-centre/status`);
  if (!res.ok) throw new Error("Failed to fetch Command Centre status");
  return res.json();
}

export async function getCommandCentreTelemetry() {
  const res = await apiFetch(`${API_BASE}/api/v1/command-centre/telemetry`);
  if (!res.ok) throw new Error("Failed to fetch Command Centre telemetry");
  return res.json();
}

export async function getCommandCentreRecentMissions(limit: number = 100) {
  const res = await apiFetch(`${API_BASE}/api/v1/command-centre/recent-missions?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch recent missions");
  return res.json();
}

export function getAnalyzedMediaUrl(jobId: string): string {
  return `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/video`;
}

export function getOriginalMediaUrl(jobId: string): string {
  return `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/original`;
}

export async function connectDrone(droneId?: string) {
  const url = new URL(`${API_BASE}/api/v1/command-centre/drone/connect`);
  if (droneId) url.searchParams.append("drone_id", droneId);
  const res = await apiFetch(url.toString(), { method: "POST" });
  if (!res.ok) throw new Error("Failed to connect drone");
  return res.json();
}

export async function disconnectDrone() {
  const res = await apiFetch(`${API_BASE}/api/v1/command-centre/drone/disconnect`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to disconnect drone");
  return res.json();
}

export async function getMissionReport(missionId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/missions/${encodeURIComponent(missionId)}/report`);
  if (!res.ok) throw new Error("Failed to fetch mission report");
  return res.json();
}

// ==========================================
// Dedicated Surveillance Engine Endpoints
// ==========================================

export interface LiveSurveillanceStartParams {
  stream_url?: string;
  rtsp_url?: string;
  camera_id?: string;
  camera_name?: string;
  model_type?: string;
  is_simulated?: boolean;
}

export async function startLiveSurveillance(params: LiveSurveillanceStartParams) {
  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/live/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to start live surveillance (${res.status})`);
  }
  return data;
}

export async function stopLiveSurveillance(sessionId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/live/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to stop live surveillance (${res.status})`);
  }
  return data;
}

export async function getLiveSurveillanceStatus(sessionId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/live/${encodeURIComponent(sessionId)}/status`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to get surveillance status (${res.status})`);
  }
  return data;
}

export function getLiveSurveillanceFeedUrl(sessionId: string, annotated: boolean = true): string {
  return `${API_BASE}/api/v1/surveillance/live/${encodeURIComponent(sessionId)}/feed?annotated=${annotated}`;
}

export async function listLiveSurveillanceSessions() {
  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/live/sessions`);
  if (!res.ok) throw new Error("Failed to list live surveillance sessions");
  return res.json();
}

export async function uploadOfflineSurveillanceMedia(file: File, analysisType: string = "NAVIGATION") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analysis_type", analysisType);

  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/offline/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to upload media (${res.status})`);
  }
  return data;
}

export async function startOfflineSurveillanceAnalysis(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/start`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to start analysis (${res.status})`);
  }
  return data;
}

export async function getOfflineSurveillanceStatus(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/status`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to get job status (${res.status})`);
  }
  return data;
}

export async function getOfflineSurveillanceResults(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/results`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to get job results (${res.status})`);
  }
  return data;
}

export function getOfflineAnalyzedVideoUrl(jobId: string): string {
  return `${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/video`;
}

export function getOfflineOriginalMediaUrl(jobId: string): string {
  return `${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/original`;
}

// ==========================================
// Centralized Database Results API (PRD)
// ==========================================

export interface CentralResultItem {
  id: string;
  module_type: "navigation" | "rod_debris" | "runway_lights" | "live_surveillance" | "offline_surveillance" | string;
  session_id?: string | null;
  title: string;
  status: "queued" | "processing" | "completed" | "failed" | string;
  summary?: string | null;
  result_data?: Record<string, any>;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  media_reference?: string | null;
  error_message?: string | null;
  events_count?: number;
  media_count?: number;
}

export interface CentralResultsFilter {
  module_type?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
  detection_class?: string;
  camera_id?: string;
  page?: number;
  page_size?: number;
}

export async function getCentralResults(filters: CentralResultsFilter = {}) {
  const url = new URL(`${API_BASE}/api/results`);
  if (filters.module_type && filters.module_type !== "all") url.searchParams.append("module_type", filters.module_type);
  if (filters.status && filters.status !== "all") url.searchParams.append("status", filters.status);
  if (filters.start_date) url.searchParams.append("start_date", filters.start_date);
  if (filters.end_date) url.searchParams.append("end_date", filters.end_date);
  if (filters.search) url.searchParams.append("search", filters.search);
  if (filters.detection_class) url.searchParams.append("detection_class", filters.detection_class);
  if (filters.camera_id) url.searchParams.append("camera_id", filters.camera_id);
  if (filters.page) url.searchParams.append("page", filters.page.toString());
  if (filters.page_size) url.searchParams.append("page_size", filters.page_size.toString());

  const res = await apiFetch(url.toString());
  if (!res.ok) throw new Error(`Failed to fetch results: ${res.statusText}`);
  return res.json();
}

export async function getCentralResultsSummary() {
  const res = await apiFetch(`${API_BASE}/api/results/summary`);
  if (!res.ok) throw new Error(`Failed to fetch results summary: ${res.statusText}`);
  return res.json();
}

export async function getCentralResultDetails(id: string) {
  const res = await apiFetch(`${API_BASE}/api/results/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`Failed to fetch result ${id}: ${res.statusText}`);
  return res.json();
}

export async function updateCentralResult(id: string, data: Partial<CentralResultItem>) {
  const res = await apiFetch(`${API_BASE}/api/results/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update result ${id}: ${res.statusText}`);
  return res.json();
}

export async function getCentralResultEvents(id: string, page = 1, pageSize = 50) {
  const res = await apiFetch(`${API_BASE}/api/results/${encodeURIComponent(id)}/events?page=${page}&page_size=${pageSize}`);
  if (!res.ok) throw new Error(`Failed to fetch events for ${id}: ${res.statusText}`);
  return res.json();
}

export async function getCentralResultMedia(id: string) {
  const res = await apiFetch(`${API_BASE}/api/results/${encodeURIComponent(id)}/media`);
  if (!res.ok) throw new Error(`Failed to fetch media for ${id}: ${res.statusText}`);
  return res.json();
}

export async function triggerCentralBackfill() {
  const res = await apiFetch(`${API_BASE}/api/results/sync/backfill`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to trigger backfill: ${res.statusText}`);
  return res.json();
}

// ==========================================
// Authentication & Password Management Endpoints
// ==========================================

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface ForgotPasswordResult {
  message: string;
  reset_url?: string | null;
}

export interface VerifyTokenResult {
  valid: boolean;
  email?: string | null;
  message?: string | null;
}

export interface ResetPasswordResult {
  success: boolean;
  message: string;
}

export async function loginUser(
  email: string,
  password: string,
  rememberMe = true
): Promise<LoginResult> {
  let res: Response;
  try {
    res = await apiFetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    });
  } catch {
    throw new Error(
      "Unable to reach the authentication server. Please check your network connection or server status."
    );
  }

  if (!res.ok) {
    let errorDetail = "Invalid email or password. Please try again.";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") {
        errorDetail = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorDetail = "Please enter a valid email address and password.";
      }
    } catch {
      // fallback to default
    }
    throw new Error(errorDetail);
  }

  const data: LoginResult = await res.json();
  setApiSessionToken(data.access_token);
  return data;
}

export async function forgotPassword(email: string): Promise<ForgotPasswordResult> {
  let res: Response;
  try {
    res = await apiFetch(`${API_BASE}/api/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  } catch {
    throw new Error(
      "Unable to reach the server. Please check your network connection and try again."
    );
  }

  if (!res.ok) {
    let errorDetail = "Failed to process password recovery request.";
    if (res.status === 429) {
      errorDetail = "Too many recovery requests. Please wait a minute before trying again.";
    }
    try {
      const data = await res.json();
      if (typeof data.detail === "string") {
        errorDetail = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorDetail = "Please enter a valid email address.";
      }
    } catch {}
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function verifyResetToken(token: string): Promise<VerifyTokenResult> {
  try {
    const res = await apiFetch(
      `${API_BASE}/api/auth/verify-reset-token?token=${encodeURIComponent(token)}`
    );
    if (!res.ok) {
      return { valid: false, message: "Could not verify reset token" };
    }
    return res.json();
  } catch {
    return {
      valid: false,
      message: "Unable to connect to the server to verify this reset link.",
    };
  }
}

export async function resetPassword(
  token: string,
  newPassword: string,
  confirmPassword: string
): Promise<ResetPasswordResult> {
  let res: Response;
  try {
    res = await apiFetch(`${API_BASE}/api/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
  } catch {
    throw new Error(
      "Unable to reach the server. Please check your network connection and try again."
    );
  }

  if (!res.ok) {
    let errorDetail = "Failed to reset password.";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") {
        errorDetail = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorDetail = data.detail[0]?.msg || "Please enter a valid password.";
      }
    } catch {}
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function logoutUser(): Promise<{ success: boolean; message: string }> {
  try {
    const res = await apiFetch(`${API_BASE}/api/auth/logout`, { method: "POST" });
    setApiSessionToken(null);
    if (res.ok) return await res.json();
  } catch {
    setApiSessionToken(null);
  }
  return { success: true, message: "Logged out" };
}

export async function getCurrentUser(token?: string): Promise<UserProfile> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await apiFetch(`${API_BASE}/api/auth/me`, { headers });
  if (!res.ok) throw new Error("Session expired or unauthorized");
  return res.json();
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface RegisterResult {
  success: boolean;
  message: string;
  requires_verification: boolean;
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export async function registerUser(payload: RegisterPayload): Promise<RegisterResult> {
  let res: Response;
  try {
    res = await apiFetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(
      "Unable to reach the server. Please check your network connection and try again."
    );
  }

  if (!res.ok) {
    let errorDetail = "Failed to create account. Please check your details and try again.";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") {
        errorDetail = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorDetail = data.detail[0]?.msg || errorDetail;
      }
    } catch {}
    throw new Error(errorDetail);
  }

  const data: RegisterResult = await res.json();
  if (data.access_token) {
    setApiSessionToken(data.access_token);
  }
  return data;
}

// ==========================================
// Tactical Navigation & Route Guidance (ROD)
// ==========================================

export interface NavigationWaypoint {
  id?: string;
  order: number;
  latitude: number;
  longitude: number;
  altitude_agl_m?: number;
  notes?: string;
  validation_status?: string;
}

export interface RouteCalculateRequest {
  start_latitude: number;
  start_longitude: number;
  target_latitude: number;
  target_longitude: number;
  target_name?: string;
  waypoints?: NavigationWaypoint[];
  speed_mps?: number;
  speed_source?: string;
  max_range_limit_m?: number;
}

export interface RouteSegment {
  from_name: string;
  to_name: string;
  from_lat: number;
  from_lon: number;
  to_lat: number;
  to_lon: number;
  distance_m: number;
  initial_bearing_deg: number;
  compass_direction: string;
}

export interface RouteCalculateResponse {
  valid: boolean;
  status: string;
  start_coordinates: { latitude: number; longitude: number };
  target_coordinates: { latitude: number; longitude: number };
  target_name?: string;
  waypoints_count: number;
  total_distance_m: number;
  straight_line_distance_m: number;
  detour_percentage: number;
  estimated_time_seconds?: number;
  estimated_time_formatted: string;
  speed_used_mps: number;
  speed_source: string;
  calculation_method: string;
  assumptions: string[];
  segments: RouteSegment[];
  all_points: Array<{
    id?: string;
    name: string;
    lat: number;
    lon: number;
    alt: number;
    type: string;
    order: number;
    notes?: string;
  }>;
  warnings: string[];
}

export interface RouteSaveRequest {
  name: string;
  drone_id?: string;
  start_latitude: number;
  start_longitude: number;
  target_latitude: number;
  target_longitude: number;
  target_name?: string;
  waypoints?: NavigationWaypoint[];
  speed_mps?: number;
  status?: string;
}

export interface RouteResponse {
  id: string;
  name: string;
  drone_id?: string;
  start_latitude: number;
  start_longitude: number;
  target_latitude: number;
  target_longitude: number;
  target_name?: string;
  total_distance_m: number;
  estimated_time_s: number;
  waypoints: Array<{
    id?: string;
    order: number;
    latitude: number;
    longitude: number;
    altitude_agl_m?: number;
    notes?: string;
  }>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface GuidanceCalculationRequest {
  drone_latitude: number;
  drone_longitude: number;
  drone_heading?: number;
  drone_speed?: number;
  target_latitude: number;
  target_longitude: number;
  waypoint_order?: number;
}

export interface GuidanceCalculationResponse {
  distance_to_target_m: number;
  bearing_to_target_deg: number;
  compass_direction: string;
  relative_bearing_deg?: number;
  steering_instruction: string;
  arrival_status: string;
  is_arrived: boolean;
}

export interface LiveNavigationTelemetry {
  connected: boolean;
  drone_id?: string | null;
  drone_name?: string | null;
  telemetry_source: string;
  latitude?: number | null;
  longitude?: number | null;
  altitude?: number | null;
  speed?: number | null;
  heading?: number | null;
  battery?: number | null;
  is_stale: boolean;
  has_gps_fix: boolean;
  status: string;
  message: string;
  last_heartbeat?: string | null;
  age_seconds?: number | null;
  stale_threshold_seconds: number;
  estimated_uncertainty_m?: number | null;
}

export interface DebrisTargetItem {
  id: string;
  class_name: string;
  confidence?: number;
  latitude?: number | null;
  longitude?: number | null;
  uncertainty_m?: number | null;
  status: string;
  formatted?: string;
  source_module: string;
  timestamp?: string;
  is_navigable: boolean;
  navigable_reason?: string | null;
}

export async function calculateRoute(req: RouteCalculateRequest): Promise<RouteCalculateResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/route/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to calculate navigation route");
  }
  return res.json();
}

export async function calculateGuidance(
  req: GuidanceCalculationRequest
): Promise<GuidanceCalculationResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/route/guidance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to compute navigation guidance");
  }
  return res.json();
}

export async function savePlannedRoute(req: RouteSaveRequest): Promise<RouteResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/routes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to save navigation route");
  }
  return res.json();
}

export async function listPlannedRoutes(skip = 0, limit = 50): Promise<RouteResponse[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/routes?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error("Failed to list saved navigation routes");
  return res.json();
}

export async function getPlannedRoute(routeId: string): Promise<RouteResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/routes/${routeId}`);
  if (!res.ok) throw new Error("Failed to fetch navigation route");
  return res.json();
}

export async function deletePlannedRoute(
  routeId: string
): Promise<{ deleted: boolean; id: string }> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/routes/${routeId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete navigation route");
  return res.json();
}

export async function getLiveNavigationTelemetry(): Promise<LiveNavigationTelemetry> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/telemetry/live`);
  if (!res.ok) throw new Error("Failed to retrieve live navigation telemetry");
  return res.json();
}

export async function connectNavigationDrone(
  droneId?: string
): Promise<{ connected: boolean; drone_id: string; name: string; status: string }> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/drone/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drone_id: droneId }),
  });
  if (!res.ok) throw new Error("Failed to connect drone");
  return res.json();
}

export async function disconnectNavigationDrone(): Promise<{ connected: boolean; status: string }> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/drone/disconnect`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to disconnect drone");
  return res.json();
}

export async function pushDroneHeartbeat(
  data: Partial<LiveNavigationTelemetry>
): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/drone/heartbeat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to push drone heartbeat");
  return res.json();
}

export async function getDebrisNavigationTargets(limit = 40): Promise<DebrisTargetItem[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/debris-targets?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch debris navigation targets");
  return res.json();
}

export async function setTelemetryStaleThreshold(seconds: number): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/v1/navigation/telemetry/threshold`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stale_threshold_seconds: seconds }),
  });
  if (!res.ok) throw new Error("Failed to configure telemetry threshold");
  return res.json();
}
