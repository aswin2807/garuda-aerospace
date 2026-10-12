const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function detectImageFile(file: File, confidence?: number, droneId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (confidence !== undefined) formData.append("confidence", confidence.toString());
  if (droneId) formData.append("drone_id", droneId);

  const res = await fetch(`${API_BASE}/api/v1/detection/image`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Inference failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getDrones() {
  const res = await fetch(`${API_BASE}/api/v1/drones`);
  if (!res.ok) throw new Error("Failed to fetch drones");
  return res.json();
}

export async function getMissions() {
  const res = await fetch(`${API_BASE}/api/v1/missions`);
  if (!res.ok) throw new Error("Failed to fetch missions");
  return res.json();
}

export async function getTelemetry(droneId: string) {
  const res = await fetch(`${API_BASE}/api/v1/drones/${droneId}/telemetry`);
  if (!res.ok) throw new Error("Failed to fetch telemetry");
  return res.json();
}

export async function getDetectionHistory(params?: { droneId?: string; minConfidence?: number }) {
  const url = new URL(`${API_BASE}/api/v1/detection/history`);
  if (params?.droneId) url.searchParams.append("drone_id", params.droneId);
  if (params?.minConfidence) url.searchParams.append("min_confidence", params.minConfidence.toString());

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch detection history");
  return res.json();
}

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
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
  ModelItem,
  ModelStatusResponse,
  ModelSelectResponse,
} from "../types/detection";

export async function connectCamera(params: CameraConnectParams): Promise<CameraConnectResponse> {
  const res = await fetch(`${API_BASE}/api/v1/camera/connect`, {
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
  const res = await fetch(`${API_BASE}/api/v1/camera/${encodeURIComponent(cameraId)}/disconnect`, {
    method: "POST",
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to disconnect camera (${res.status})`);
  }
  return data;
}

export async function getCameraStatus(cameraId: string): Promise<CameraStatusResponse> {
  const res = await fetch(`${API_BASE}/api/v1/camera/${encodeURIComponent(cameraId)}/status`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to get camera status (${res.status})`);
  }
  return data;
}

export async function getCameras(): Promise<CameraListItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/camera/list`);
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
  const res = await fetch(`${API_BASE}/api/v1/models/status`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to fetch model status (${res.status})`);
  }
  return data;
}

export async function getModels(): Promise<ModelItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/models/list`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to list models (${res.status})`);
  }
  return data;
}

export async function selectModel(modelName: string): Promise<ModelSelectResponse> {
  const res = await fetch(`${API_BASE}/api/v1/models/select`, {
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
  const res = await fetch(`${API_BASE}/api/v1/models/navigation/classes`);
  if (!res.ok) {
    throw new Error(`Failed to fetch navigation classes (${res.status})`);
  }
  return res.json();
}

// ==========================================
// Video Analysis & Session Endpoints (PRD Section 30)
// ==========================================

export async function startVideoAnalysis(source: string, loop: boolean = false) {
  const res = await fetch(`${API_BASE}/api/v1/video/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, loop }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to start video analysis");
  return data;
}

export async function stopVideoAnalysis(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/v1/video/${encodeURIComponent(sessionId)}/stop`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to stop video analysis");
  return data;
}

export async function getVideoSessionStatus(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/v1/video/${encodeURIComponent(sessionId)}/status`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to get video status");
  return data;
}

export async function getSessionStatistics(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/v1/session/${encodeURIComponent(sessionId)}/statistics`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to get session statistics");
  return data;
}

export async function resetSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/v1/session/${encodeURIComponent(sessionId)}/reset`, {
    method: "POST",
  });
  return res.json();
}

export async function getPipelineDebug() {
  const res = await fetch(`${API_BASE}/api/v1/debug/pipeline`);
  if (!res.ok) throw new Error("Failed to fetch debug pipeline");
  return res.json();
}

export async function getPipelineHealth() {
  const res = await fetch(`${API_BASE}/api/v1/debug/pipeline/health`);
  if (!res.ok) throw new Error("Failed to fetch pipeline health");
  return res.json();
}

// Analysis API Endpoints (PRD Section 38 & Isolated Modules)
export async function uploadAnalysisMedia(file: File, analysisType: string = "NAVIGATION") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analysis_type", analysisType);
  const res = await fetch(`${API_BASE}/api/v1/analysis/upload`, {
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
  const res = await fetch(`${API_BASE}/api/v1/analysis/videos`, {
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
  const res = await fetch(`${API_BASE}/api/v1/analysis/images`, {
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
  const res = await fetch(`${API_BASE}/api/v1/navigation/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload navigation media");
  return data;
}

export async function getNavigationHistory() {
  const res = await fetch(`${API_BASE}/api/v1/navigation/history`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch navigation history");
  return data;
}

export async function uploadFodMedia(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/fod/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload FOD media");
  return data;
}

export async function getFodHistory() {
  const res = await fetch(`${API_BASE}/api/v1/fod/history`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch FOD history");
  return data;
}

export async function uploadRunwayLightMedia(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/runway-light/upload`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to upload runway light media");
  return data;
}

export async function getRunwayLightHistory() {
  const res = await fetch(`${API_BASE}/api/v1/runway-light/history`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch runway light history");
  return data;
}

export async function startAnalysis(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/start`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to start analysis");
  return data;
}

export async function pauseAnalysis(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/pause`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to pause analysis");
  return data;
}

export async function resumeAnalysis(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/resume`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to resume analysis");
  return data;
}

export async function cancelAnalysis(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to cancel analysis");
  return data;
}

export async function getAnalysisStatus(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch analysis status");
  return data;
}

export async function getAnalysisResults(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/results`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch analysis results");
  return data;
}

export async function getAnalysisJobs(analysisType?: string) {
  const url = new URL(`${API_BASE}/api/v1/analysis/jobs/all`);
  if (analysisType) {
    url.searchParams.append("analysis_type", analysisType);
  }
  const res = await fetch(url.toString());
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch analysis jobs");
  return data;
}

// ==========================================
// Garuda Aerospace Command Centre API Endpoints
// ==========================================

export async function getCommandCentreStatus() {
  const res = await fetch(`${API_BASE}/api/v1/command-centre/status`);
  if (!res.ok) throw new Error("Failed to fetch Command Centre status");
  return res.json();
}

export async function getCommandCentreTelemetry() {
  const res = await fetch(`${API_BASE}/api/v1/command-centre/telemetry`);
  if (!res.ok) throw new Error("Failed to fetch Command Centre telemetry");
  return res.json();
}

export async function getCommandCentreRecentMissions(limit: number = 100) {
  const res = await fetch(`${API_BASE}/api/v1/command-centre/recent-missions?limit=${limit}`);
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
  const res = await fetch(url.toString(), { method: "POST" });
  if (!res.ok) throw new Error("Failed to connect drone");
  return res.json();
}

export async function disconnectDrone() {
  const res = await fetch(`${API_BASE}/api/v1/command-centre/drone/disconnect`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to disconnect drone");
  return res.json();
}

export async function getMissionReport(missionId: string) {
  const res = await fetch(`${API_BASE}/api/v1/missions/${encodeURIComponent(missionId)}/report`);
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
  const res = await fetch(`${API_BASE}/api/v1/surveillance/live/start`, {
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
  const res = await fetch(`${API_BASE}/api/v1/surveillance/live/stop`, {
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
  const res = await fetch(`${API_BASE}/api/v1/surveillance/live/${encodeURIComponent(sessionId)}/status`);
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
  const res = await fetch(`${API_BASE}/api/v1/surveillance/live/sessions`);
  if (!res.ok) throw new Error("Failed to list live surveillance sessions");
  return res.json();
}

export async function uploadOfflineSurveillanceMedia(file: File, analysisType: string = "NAVIGATION") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analysis_type", analysisType);

  const res = await fetch(`${API_BASE}/api/v1/surveillance/offline/upload`, {
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
  const res = await fetch(`${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/start`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to start analysis (${res.status})`);
  }
  return data;
}

export async function getOfflineSurveillanceStatus(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/status`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Failed to get job status (${res.status})`);
  }
  return data;
}

export async function getOfflineSurveillanceResults(jobId: string) {
  const res = await fetch(`${API_BASE}/api/v1/surveillance/offline/${encodeURIComponent(jobId)}/results`);
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





