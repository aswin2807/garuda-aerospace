import { create } from "zustand";
import {
  DetectionItem,
  DroneTelemetry,
  DroneInfo,
  MissionInfo,
  AlertItem,
  CameraStatus,
  ModelItem,
  ModelStatusResponse,
  SubModelStatus,
  DetectionSummary,
  DetectionCounts,
  SessionTotals,
  PerformanceMetrics,
  PipelineHealth,
} from "../types/detection";
import {
  getModelStatus,
  getModels,
  selectModel,
  getCommandCentreStatus,
  getCommandCentreTelemetry,
  connectDrone,
  disconnectDrone,
} from "../lib/api";


export interface DroneStoreState {
  drone: DroneInfo | null;
  telemetry: DroneTelemetry | null;
  detections: DetectionItem[];
  mission: MissionInfo | null;
  alerts: AlertItem[];
  connectionStatus: "CONNECTED" | "CONNECTING" | "DISCONNECTED";
  confidenceThreshold: number;
  fps: number;
  inferenceTimeMs: number;


  // IP Camera Connection State
  activeCameraId: string | null;
  cameraStatus: CameraStatus;
  cameraInfo: {
    ip?: string;
    stream_url?: string;
    fps?: number;
    latency_ms?: number;
    camera_name?: string;
  } | null;
  cameraResolution: { width: number; height: number };
  cameraFps: number;
  inferenceFps: number;
  imageQuality: {
    brightness?: number;
    sharpness?: number;
    warnings: string[];
  };

  // Actions
  setDrone: (drone: DroneInfo | null) => void;
  setTelemetry: (telemetry: Partial<DroneTelemetry>) => void;
  setDetections: (detections: DetectionItem[], inferenceMs?: number) => void;
  setMission: (mission: MissionInfo | null) => void;
  addAlert: (alert: AlertItem) => void;
  setConnectionStatus: (status: "CONNECTED" | "CONNECTING" | "DISCONNECTED") => void;
  setConfidenceThreshold: (threshold: number) => void;
  setFps: (fps: number) => void;

  // Camera Actions
  setActiveCameraId: (id: string | null) => void;
  setCameraStatus: (status: CameraStatus) => void;
  setCameraInfo: (info: DroneStoreState["cameraInfo"]) => void;
  setCameraResolution: (res: { width: number; height: number }) => void;
  setCameraFps: (fps: number) => void;
  setInferenceFps: (fps: number) => void;
  setImageQuality: (q: { brightness?: number; sharpness?: number; warnings: string[] }) => void;

  // Model Management State & Actions
  activeModel: string;
  modelStatus: string;
  availableModels: ModelItem[];
  modelClasses: Record<string, string>;
  modelDevice: string;
  modelError: string | null;

  // Multi-Model & Alert State (PRD Section 4, 5, 29)
  summary: DetectionSummary;
  counts: DetectionCounts;
  sessionTotals: SessionTotals;
  performance: PerformanceMetrics;
  videoFrame: string | null;
  activeSessionId: string | null;
  pipelineHealth: PipelineHealth | null;

  navigationModel: SubModelStatus | null;
  fodModel: SubModelStatus | null;
  runwayLightModel: SubModelStatus | null;

  setAlerts: (alerts: AlertItem[]) => void;
  setSummary: (summary: DetectionSummary) => void;
  setCounts: (counts: DetectionCounts) => void;
  setSessionTotals: (totals: SessionTotals) => void;
  setPerformance: (perf: PerformanceMetrics) => void;
  setVideoFrame: (frame: string | null) => void;
  setActiveSessionId: (id: string | null) => void;
  setPipelineHealth: (h: PipelineHealth | null) => void;
  applyDetectionUpdate: (data: any) => void;

  setNavigationModel: (m: SubModelStatus | null) => void;
  setFodModel: (m: SubModelStatus | null) => void;
  setRunwayLightModel: (m: SubModelStatus | null) => void;

  setActiveModel: (model: string) => void;
  setModelStatus: (status: string) => void;
  setAvailableModels: (models: ModelItem[]) => void;
  setModelClasses: (classes: Record<string, string>) => void;
  setModelDevice: (device: string) => void;
  fetchModelStatus: () => Promise<void>;
  fetchAvailableModels: () => Promise<void>;
  switchModel: (modelName: string) => Promise<boolean>;
  fetchCommandCentreStatus: () => Promise<void>;
  fetchCommandCentreTelemetry: () => Promise<void>;
  connectDroneAction: (droneId?: string) => Promise<boolean>;
  disconnectDroneAction: () => Promise<boolean>;
}

export const useDroneStore = create<DroneStoreState>((set) => ({
  drone: null,
  telemetry: null,
  detections: [],
  mission: null,
  alerts: [],
  connectionStatus: "DISCONNECTED",
  confidenceThreshold: 0.20,
  fps: 0,
  inferenceTimeMs: 0,


  // Camera initial state
  activeCameraId: null,
  cameraStatus: "DISCONNECTED",
  cameraInfo: null,
  cameraResolution: { width: 1920, height: 1080 },
  cameraFps: 30,
  inferenceFps: 3.1,
  imageQuality: {
    brightness: 126,
    sharpness: 452,
    warnings: [],
  },

  counts: { navigation: 0, fod: 0, light_on: 0, light_off: 0, confirmed_faults: 0 },
  sessionTotals: { navigation: 0, fod: 0, light_on: 0, light_off: 0, confirmed_faults: 0, total_unique: 0 },
  performance: { stream_fps: 30, inference_fps: 3.1, inference_ms: 327.3, latency_ms: 327.3 },
  videoFrame: null,
  activeSessionId: null,
  pipelineHealth: null,

  setDrone: (drone) => set({ drone }),
  setTelemetry: (telemetry) =>
    set((state) => ({
      telemetry: telemetry
        ? state.telemetry
          ? { ...state.telemetry, ...telemetry }
          : {
              latitude: 0,
              longitude: 0,
              altitude: 0,
              speed: 0,
              heading: 0,
              battery: 0,
              ...telemetry,
            }
        : null,
    })),

  setDetections: (detections, inferenceMs) =>
    set((state) => ({
      detections,
      inferenceTimeMs: inferenceMs !== undefined ? inferenceMs : state.inferenceTimeMs,
    })),
  setMission: (mission) => set({ mission }),
  addAlert: (alert) =>
    set((state) => ({ alerts: [alert, ...state.alerts.slice(0, 9)] })),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  setConfidenceThreshold: (confidenceThreshold) => set({ confidenceThreshold }),
  setFps: (fps) => set({ fps }),

  // Camera Actions
  setActiveCameraId: (activeCameraId) => set({ activeCameraId }),
  setCameraStatus: (cameraStatus) => set({ cameraStatus }),
  setCameraInfo: (cameraInfo) => set({ cameraInfo }),
  setCameraResolution: (cameraResolution) => set({ cameraResolution }),
  setCameraFps: (cameraFps) => set({ cameraFps }),
  setInferenceFps: (inferenceFps) => set({ inferenceFps, fps: inferenceFps }),
  setImageQuality: (imageQuality) => set({ imageQuality }),

  // Counts & Performance Actions
  setCounts: (counts) => set({ counts }),
  setSessionTotals: (sessionTotals) => set({ sessionTotals }),
  setPerformance: (performance) => set({
    performance,
    inferenceFps: performance.inference_fps,
    cameraFps: performance.stream_fps,
    inferenceTimeMs: performance.inference_ms
  }),
  setVideoFrame: (videoFrame) => set({ videoFrame }),
  setActiveSessionId: (activeSessionId) => set({ activeSessionId }),
  setPipelineHealth: (pipelineHealth) => set({ pipelineHealth }),

  applyDetectionUpdate: (data: any) =>
    set((state) => {
      const counts = data.counts || state.counts;
      const sessionTotals = data.session_totals || state.sessionTotals;
      const perf = data.performance || {
        stream_fps: data.stream_fps || data.fps || state.performance.stream_fps,
        inference_fps: data.inference_fps || state.performance.inference_fps,
        inference_ms: data.inference_ms || data.inference_time_ms || data.latency_ms || state.performance.inference_ms,
        latency_ms: data.latency_ms || data.inference_ms || state.performance.latency_ms
      };

      const detections = Array.isArray(data.detections) ? data.detections : state.detections;
      const alerts = Array.isArray(data.alerts) ? data.alerts : state.alerts;
      const videoFrame = data.image_base64 || state.videoFrame;
      const summary = data.summary || {
        nav_count: counts.navigation ?? 0,
        fod_count: counts.fod ?? 0,
        light_on_count: counts.light_on ?? 0,
        light_off_count: counts.light_off ?? 0,
        total_detections: detections.length
      };

      return {
        counts,
        sessionTotals,
        performance: perf,
        detections,
        alerts,
        videoFrame,
        summary,
        fps: Math.round(perf.stream_fps || state.fps),
        cameraFps: perf.stream_fps,
        inferenceFps: perf.inference_fps,
        inferenceTimeMs: perf.inference_ms,
        cameraStatus: data.status && data.status !== "DISCONNECTED" ? data.status : state.cameraStatus
      };
    }),


  // Model initial state
  activeModel: "navigation_best.pt",
  modelStatus: "READY",
  availableModels: [],
  modelClasses: { "0": "NAVIGATION", "1": "FOD", "2": "LIGHT OFF", "3": "LIGHT ON" },
  modelDevice: "CPU",
  modelError: null,

  // Multi-Model & Alert state (PRD Section 4, 5, 29)
  summary: { nav_count: 0, fod_count: 0, light_on_count: 0, light_off_count: 0, light_off_gap_count: 0, total_detections: 0 },
  navigationModel: null,
  fodModel: null,
  runwayLightModel: null,

  setAlerts: (alerts) => set({ alerts }),
  setSummary: (summary) => set({ summary }),
  setNavigationModel: (navigationModel) => set({ navigationModel }),
  setFodModel: (fodModel) => set({ fodModel }),
  setRunwayLightModel: (runwayLightModel) => set({ runwayLightModel }),

  // Model actions
  setActiveModel: (activeModel) => set({ activeModel }),
  setModelStatus: (modelStatus) => set({ modelStatus }),
  setAvailableModels: (availableModels) => set({ availableModels }),
  setModelClasses: (modelClasses) => set({ modelClasses }),
  setModelDevice: (modelDevice) => set({ modelDevice }),

  fetchModelStatus: async () => {
    try {
      const res = await getModelStatus();
      set({
        activeModel: res.model_name,
        modelStatus: res.status,
        modelClasses: res.classes || {},
        modelDevice: res.device,
        modelError: res.error || null,
        navigationModel: res.navigation || null,
        fodModel: res.fod || null,
        runwayLightModel: res.runway_light || null,
      });
    } catch (err: any) {
      console.warn("Error fetching model status:", err);
    }
  },

  fetchAvailableModels: async () => {
    try {
      const list = await getModels();
      set({ availableModels: list });
    } catch (err: any) {
      console.warn("Error fetching available models:", err);
    }
  },

  switchModel: async (modelName: string) => {
    try {
      set({ modelStatus: "LOADING" });
      const res = await selectModel(modelName);
      if (res.success) {
        set({
          activeModel: res.model,
          modelStatus: res.status,
          modelClasses: res.classes || {},
          modelError: null,
        });
        return true;
      }
      return false;
    } catch (err: any) {
      set({
        modelStatus: "ERROR",
        modelError: err?.message || `Failed to switch model to ${modelName}`,
      });
      return false;
    }
  },

  fetchCommandCentreStatus: async () => {
    try {
      const res = await getCommandCentreStatus();
      if (res.drone_connected && res.drone) {
        set({
          drone: res.drone,
          connectionStatus: "CONNECTED",
        });
      } else {
        set({
          drone: null,
          telemetry: null,
          connectionStatus: "DISCONNECTED",
        });
      }

      if (res.models) {
        if (res.models.navigation) set({ navigationModel: res.models.navigation });
        if (res.models.fod) set({ fodModel: res.models.fod });
        if (res.models.runway_light) set({ runwayLightModel: res.models.runway_light });
      }
    } catch {
      set({
        drone: null,
        telemetry: null,
        connectionStatus: "DISCONNECTED",
      });
    }
  },

  fetchCommandCentreTelemetry: async () => {
    try {
      const res = await getCommandCentreTelemetry();
      if (res.connected && res.telemetry) {
        set({
          telemetry: res.telemetry,
          connectionStatus: "CONNECTED",
        });
      } else {
        set({
          telemetry: null,
          connectionStatus: "DISCONNECTED",
        });
      }
    } catch {
      set({
        telemetry: null,
        connectionStatus: "DISCONNECTED",
      });
    }
  },

  connectDroneAction: async (droneId?: string) => {
    try {
      const res = await connectDrone(droneId);
      if (res.success && res.drone) {
        set({
          drone: res.drone,
          connectionStatus: "CONNECTED",
        });
        return true;
      }
      return false;
    } catch (err) {
      console.warn("Failed to connect drone:", err);
      return false;
    }
  },

  disconnectDroneAction: async () => {
    try {
      await disconnectDrone();
      set({
        drone: null,
        telemetry: null,
        connectionStatus: "DISCONNECTED",
      });
      return true;
    } catch (err) {
      console.warn("Failed to disconnect drone:", err);
      return false;
    }
  },
}));

