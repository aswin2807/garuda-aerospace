import { create } from "zustand";
import { AnalysisMode, AnalysisType, AnalysisJob, AnalysisJobStatus } from "../types/detection";

export interface ModuleAnalysisState {
  activeJob: AnalysisJob | null;
  selectedFile: File | null;
  filePreviewUrl: string | null;
  isVideoPlaybackPaused: boolean;
  isUploading: boolean;
  jobResults: any | null;
}

const createInitialModuleState = (): ModuleAnalysisState => ({
  activeJob: null,
  selectedFile: null,
  filePreviewUrl: null,
  isVideoPlaybackPaused: true,
  isUploading: false,
  jobResults: null,
});

export function normalizeAnalysisType(typeStr?: string): AnalysisType {
  if (!typeStr) return "NAVIGATION";
  const upper = typeStr.toUpperCase();
  if (upper.includes("RUNWAY")) return "RUNWAY_LIGHT";
  if (upper.includes("FOD")) return "FOD";
  return "NAVIGATION";
}

export interface AnalysisStoreState {
  mode: AnalysisMode;
  setMode: (mode: AnalysisMode) => void;

  analysisType: AnalysisType;
  setAnalysisType: (type: AnalysisType) => void;

  // Fully isolated state per module (NAVIGATION, FOD, RUNWAY_LIGHT)
  modules: Record<AnalysisType, ModuleAnalysisState>;
  getModuleState: (type: AnalysisType) => ModuleAnalysisState;

  // Active module accessors (reflecting current analysisType)
  activeJob: AnalysisJob | null;
  setActiveJob: (job: AnalysisJob | null, type?: AnalysisType) => void;

  selectedFile: File | null;
  setSelectedFile: (file: File | null, type?: AnalysisType) => void;

  filePreviewUrl: string | null;
  setFilePreviewUrl: (url: string | null, type?: AnalysisType) => void;

  isVideoPlaybackPaused: boolean;
  setIsVideoPlaybackPaused: (paused: boolean, type?: AnalysisType) => void;

  isUploading: boolean;
  setIsUploading: (uploading: boolean, type?: AnalysisType) => void;

  jobResults: any | null;
  setJobResults: (results: any | null, type?: AnalysisType) => void;

  jobHistory: AnalysisJob[];
  setJobHistory: (jobs: AnalysisJob[]) => void;

  // Real-time progress update from WebSocket or polling with safe mapping & module routing
  updateProgress: (data: Partial<AnalysisJob> | Record<string, any>) => void;
  resetAnalysis: (type?: AnalysisType | any) => void;
}

export const useAnalysisStore = create<AnalysisStoreState>((set, get) => ({
  mode: "VIDEO",
  setMode: (mode) => set({ mode }),

  analysisType: "NAVIGATION",
  setAnalysisType: (analysisType) =>
    set((state) => {
      const targetMod = state.modules[analysisType] || createInitialModuleState();
      return {
        analysisType,
        activeJob: targetMod.activeJob,
        selectedFile: targetMod.selectedFile,
        filePreviewUrl: targetMod.filePreviewUrl,
        isVideoPlaybackPaused: targetMod.isVideoPlaybackPaused,
        isUploading: targetMod.isUploading,
        jobResults: targetMod.jobResults,
      };
    }),

  modules: {
    NAVIGATION: createInitialModuleState(),
    FOD: createInitialModuleState(),
    RUNWAY_LIGHT: createInitialModuleState(),
  },

  getModuleState: (type: AnalysisType) => {
    return get().modules[type] || createInitialModuleState();
  },

  activeJob: null,
  setActiveJob: (activeJob, type) =>
    set((state) => {
      const targetType = type || (activeJob?.analysis_type ? normalizeAnalysisType(activeJob.analysis_type) : state.analysisType);
      const mod = state.modules[targetType] || createInitialModuleState();
      const updatedMod: ModuleAnalysisState = { ...mod, activeJob };
      const isCurrent = targetType === state.analysisType;
      return {
        modules: { ...state.modules, [targetType]: updatedMod },
        ...(isCurrent ? { activeJob } : {}),
      };
    }),

  selectedFile: null,
  setSelectedFile: (selectedFile, type) =>
    set((state) => {
      const targetType = type || state.analysisType;
      const mod = state.modules[targetType] || createInitialModuleState();
      const updatedMod: ModuleAnalysisState = { ...mod, selectedFile };
      const isCurrent = targetType === state.analysisType;
      return {
        modules: { ...state.modules, [targetType]: updatedMod },
        ...(isCurrent ? { selectedFile } : {}),
      };
    }),

  filePreviewUrl: null,
  setFilePreviewUrl: (filePreviewUrl, type) =>
    set((state) => {
      const targetType = type || state.analysisType;
      const mod = state.modules[targetType] || createInitialModuleState();
      const updatedMod: ModuleAnalysisState = { ...mod, filePreviewUrl };
      const isCurrent = targetType === state.analysisType;
      return {
        modules: { ...state.modules, [targetType]: updatedMod },
        ...(isCurrent ? { filePreviewUrl } : {}),
      };
    }),

  isVideoPlaybackPaused: true,
  setIsVideoPlaybackPaused: (isVideoPlaybackPaused, type) =>
    set((state) => {
      const targetType = type || state.analysisType;
      const mod = state.modules[targetType] || createInitialModuleState();
      const updatedMod: ModuleAnalysisState = { ...mod, isVideoPlaybackPaused };
      const isCurrent = targetType === state.analysisType;
      return {
        modules: { ...state.modules, [targetType]: updatedMod },
        ...(isCurrent ? { isVideoPlaybackPaused } : {}),
      };
    }),

  isUploading: false,
  setIsUploading: (isUploading, type) =>
    set((state) => {
      const targetType = type || state.analysisType;
      const mod = state.modules[targetType] || createInitialModuleState();
      const updatedMod: ModuleAnalysisState = { ...mod, isUploading };
      const isCurrent = targetType === state.analysisType;
      return {
        modules: { ...state.modules, [targetType]: updatedMod },
        ...(isCurrent ? { isUploading } : {}),
      };
    }),

  jobResults: null,
  setJobResults: (jobResults, type) =>
    set((state) => {
      const targetType = type || (jobResults?.analysis_type ? normalizeAnalysisType(jobResults.analysis_type) : state.analysisType);
      const mod = state.modules[targetType] || createInitialModuleState();
      const updatedMod: ModuleAnalysisState = { ...mod, jobResults };
      const isCurrent = targetType === state.analysisType;
      return {
        modules: { ...state.modules, [targetType]: updatedMod },
        ...(isCurrent ? { jobResults } : {}),
      };
    }),

  jobHistory: [],
  setJobHistory: (jobHistory) => set({ jobHistory }),

  updateProgress: (data: any) =>
    set((state) => {
      const rawJobId = data.id || data.job_id;
      let targetType: AnalysisType = state.analysisType;

      if (data.analysis_type) {
        targetType = normalizeAnalysisType(data.analysis_type);
      } else if (rawJobId) {
        // Find which module owns this job ID
        for (const [k, mod] of Object.entries(state.modules) as [AnalysisType, ModuleAnalysisState][]) {
          if (mod.activeJob && (mod.activeJob.id === rawJobId || mod.activeJob.job_id === rawJobId)) {
            targetType = k;
            break;
          }
        }
      }

      const currentMod = state.modules[targetType] || createInitialModuleState();
      const currentActiveJob = currentMod.activeJob;

      const counts = data.counts || {};
      const perf = data.performance || {};
      const updatedData: Partial<AnalysisJob> = {
        ...data,
        id: rawJobId || currentActiveJob?.id || currentActiveJob?.job_id,
        job_id: rawJobId || currentActiveJob?.job_id || currentActiveJob?.id,
        analysis_type: targetType,
        filename: data.filename || data.video_name || currentActiveJob?.filename || "video.mp4",
        video_name: data.video_name || data.filename || currentActiveJob?.video_name || currentActiveJob?.filename,
        status: (data.status || currentActiveJob?.status || "QUEUED") as AnalysisJobStatus,
        total_frames: data.total_frames ?? data.frames_total ?? currentActiveJob?.total_frames ?? 0,
        processed_frames: data.processed_frames ?? data.frames_processed ?? currentActiveJob?.processed_frames ?? 0,
        progress: data.progress ?? currentActiveJob?.progress ?? 0,
        processing_fps: perf.fps ?? data.processing_fps ?? data.fps ?? currentActiveJob?.processing_fps ?? 0,
        elapsed_seconds: data.elapsed_seconds ?? data.elapsed_time ?? currentActiveJob?.elapsed_seconds ?? 0,
        remaining_seconds: data.remaining_seconds ?? data.eta_seconds ?? currentActiveJob?.remaining_seconds ?? 0,
        estimated_finish_time: data.estimated_finish_time || currentActiveJob?.estimated_finish_time || "",
        nav_count: counts.navigation ?? data.nav_count ?? data.navigation_count ?? currentActiveJob?.nav_count ?? 0,
        fod_count: counts.fod ?? data.fod_count ?? currentActiveJob?.fod_count ?? 0,
        total_lights: counts.total_lights ?? data.total_lights ?? currentActiveJob?.total_lights,
        light_on_count: counts.light_on ?? data.light_on_count ?? currentActiveJob?.light_on_count ?? 0,
        light_off_count: counts.light_off ?? data.light_off_count ?? currentActiveJob?.light_off_count ?? 0,
        confirmed_faults: counts.confirmed_faults ?? data.confirmed_faults ?? currentActiveJob?.confirmed_faults ?? 0,
        unknown_light_count: counts.unknown ?? counts.unknown_lights ?? data.unknown_light_count ?? currentActiveJob?.unknown_light_count ?? 0,
        rows_detected: counts.rows ?? counts.rows_detected ?? data.rows_detected ?? currentActiveJob?.rows_detected ?? 0,
        row_results: data.row_results ?? currentActiveJob?.row_results ?? [],
        matrix: data.matrix ?? currentActiveJob?.matrix,
        faults: data.faults ?? currentActiveJob?.faults,
        unique_nav_count: data.unique_nav_count ?? currentActiveJob?.unique_nav_count,
        unique_fod_count: data.unique_fod_count ?? currentActiveJob?.unique_fod_count,
        total_detections: data.total_detections ?? data.total_frame_detections ?? currentActiveJob?.total_detections ?? 0,
        total_frame_detections: data.total_frame_detections ?? data.total_detections ?? currentActiveJob?.total_frame_detections ?? 0,
        speed_ratio: perf.speed_ratio ?? data.speed_ratio ?? currentActiveJob?.speed_ratio ?? 0,
        class_counts: data.class_counts ?? currentActiveJob?.class_counts,
        unique_light_on: data.unique_light_on ?? currentActiveJob?.unique_light_on,
        unique_light_off: data.unique_light_off ?? currentActiveJob?.unique_light_off,
        avg_confidence: data.avg_confidence ?? currentActiveJob?.avg_confidence,
        avg_inference_ms: perf.inference_ms ?? data.avg_inference_ms ?? data.inference_ms ?? currentActiveJob?.avg_inference_ms,
      };

      const newJob: AnalysisJob = currentActiveJob
        ? ({ ...currentActiveJob, ...updatedData } as AnalysisJob)
        : (updatedData as AnalysisJob);

      const updatedMod: ModuleAnalysisState = {
        ...currentMod,
        activeJob: newJob,
      };

      const isCurrent = targetType === state.analysisType;
      return {
        modules: {
          ...state.modules,
          [targetType]: updatedMod,
        },
        ...(isCurrent ? { activeJob: newJob } : {}),
      };
    }),

  resetAnalysis: (type) =>
    set((state) => {
      const targetType = (typeof type === "string" ? normalizeAnalysisType(type) : null) || state.analysisType;
      const resetMod = createInitialModuleState();
      const isCurrent = targetType === state.analysisType;
      return {
        modules: {
          ...state.modules,
          [targetType]: resetMod,
        },
        ...(isCurrent
          ? {
              activeJob: null,
              selectedFile: null,
              filePreviewUrl: null,
              isVideoPlaybackPaused: true,
              isUploading: false,
              jobResults: null,
            }
          : {}),
      };
    }),
}));
