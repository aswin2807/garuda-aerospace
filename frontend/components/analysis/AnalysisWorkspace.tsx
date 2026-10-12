"use client";

import React, { useEffect } from "react";
import { useAnalysisStore } from "../../stores/analysisStore";
import { useAnalysisWebSocket } from "../../hooks/useAnalysisWebSocket";
import { useAnalysis } from "../../hooks/useAnalysis";
import { AnalysisType } from "../../types/detection";
import { UploadMedia } from "./UploadMedia";
import { VideoPreview } from "./VideoPreview";
import { AnalysisControls } from "./AnalysisControls";
import { AnalysisProgress } from "./AnalysisProgress";
import { AnalysisETA } from "./AnalysisETA";
import { AnalysisResults } from "./AnalysisResults";
import { ImageAnalysisView } from "./ImageAnalysisView";
import { AnalysisHistory } from "./AnalysisHistory";

interface AnalysisWorkspaceProps {
  initialType?: AnalysisType;
  fixedType?: boolean;
}

export const AnalysisWorkspace: React.FC<AnalysisWorkspaceProps> = ({ initialType, fixedType = false }) => {
  const mode = useAnalysisStore((s) => s.mode);
  const setMode = useAnalysisStore((s) => s.setMode);
  const analysisType = useAnalysisStore((s) => s.analysisType);
  const setAnalysisType = useAnalysisStore((s) => s.setAnalysisType);
  const activeJob = useAnalysisStore((s) => s.activeJob);
  const selectedFile = useAnalysisStore((s) => s.selectedFile);
  const isUploading = useAnalysisStore((s) => s.isUploading);
  const resetAnalysis = useAnalysisStore((s) => s.resetAnalysis);

  const { start } = useAnalysis();

  useEffect(() => {
    if (initialType) {
      setAnalysisType(initialType);
    }
  }, [initialType, setAnalysisType]);

  // Attach WebSocket to receive live frame progress, dynamic ETA, and detections
  const activeJobId = activeJob?.job_id || activeJob?.id || null;
  useAnalysisWebSocket(activeJobId);

  const isVideoMode = mode === "VIDEO";
  const isImageMode = mode === "IMAGE";

  const handleStartAnalysis = async () => {
    if (activeJobId) {
      await start(activeJobId);
    }
  };

  // Safe status message determination per PRD requirements (Section 9.2)
  const getStatusBanner = () => {
    if (!activeJob) return { text: "No analysis selected", color: "text-[#5B6472]", bg: "bg-[#F5F7FA] border-[#D9DEE7]" };
    const outcome = (activeJob as any)?.outcome_status;
    if (outcome === "COMPLETED_WITH_DETECTIONS") {
      return { text: "Analysis completed (Detections Found)", color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" };
    }
    if (outcome === "COMPLETED_NO_DETECTIONS") {
      return { text: "Analysis completed (Clean / No Detections)", color: "text-[#0066FF]", bg: "bg-[#EAF3FF] border-[#0066FF]/30" };
    }
    if (outcome === "INCONCLUSIVE") {
      return { text: "Inconclusive Analysis", color: "text-amber-700", bg: "bg-amber-50 border-amber-200" };
    }
    switch (activeJob?.status) {
      case "QUEUED":
      case "UPLOADED":
        return { text: "Waiting for analysis...", color: "text-amber-700", bg: "bg-amber-50 border-amber-200" };
      case "ANALYZING":
        return { text: "Analyzing video...", color: "text-[#0066FF] animate-pulse", bg: "bg-[#EAF3FF] border-[#0066FF]/30" };
      case "PAUSED":
        return { text: "Analysis paused", color: "text-amber-700", bg: "bg-amber-50 border-amber-200" };
      case "COMPLETED":
        return { text: "Analysis completed", color: "text-[#0066FF]", bg: "bg-[#EAF3FF] border-[#0066FF]/30" };
      case "FAILED":
        return { text: "Analysis failed", color: "text-red-600", bg: "bg-red-50 border-red-200" };
      case "CANCELLED":
        return { text: "Analysis cancelled", color: "text-[#5B6472]", bg: "bg-[#F5F7FA] border-[#D9DEE7]" };
      default:
        return { text: "IDLE", color: "text-[#5B6472]", bg: "bg-[#F5F7FA] border-[#D9DEE7]" };
    }
  };

  const statusBanner = getStatusBanner();

  const modelLabels: Record<AnalysisType, { name: string; model: string }> = {
    NAVIGATION: { name: "NAVIGATION MODULE", model: "navigation_best.pt ONLY" },
    FOD: { name: "FOD DEBRIS MODULE", model: "FOD_Karhtikeyan.pt ONLY" },
    RUNWAY_LIGHT: { name: "RUNWAY LIGHT MODULE", model: "runway_light_best.pt ONLY" },
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col space-y-4 max-w-7xl mx-auto w-full select-none bg-[#F5F7FA]">
      {/* Workspace Header / Module Switcher Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#FFFFFF] border border-[#D9DEE7] px-4 py-3 rounded-xl font-mono text-xs shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {!fixedType && (
            <div className="flex items-center bg-[#F5F7FA] p-1 rounded-lg border border-[#D9DEE7] mr-2">
              <button
                onClick={() => setAnalysisType("NAVIGATION")}
                className={`px-3 py-1 rounded font-bold text-xs transition-colors ${
                  analysisType === "NAVIGATION"
                    ? "bg-[#0066FF] text-white shadow-sm"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                NAVIGATION
              </button>
              <button
                onClick={() => setAnalysisType("FOD")}
                className={`px-3 py-1 rounded font-bold text-xs transition-colors ${
                  analysisType === "FOD"
                    ? "bg-[#0066FF] text-white shadow-sm"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                FOD DEBRIS
              </button>
              <button
                onClick={() => setAnalysisType("RUNWAY_LIGHT")}
                className={`px-3 py-1 rounded font-bold text-xs transition-colors ${
                  analysisType === "RUNWAY_LIGHT"
                    ? "bg-[#0066FF] text-white shadow-sm"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                RUNWAY LIGHT
              </button>
            </div>
          )}

          <div className="flex items-center space-x-2">
            <span className="text-[#0066FF] font-bold uppercase tracking-wider">
              {modelLabels[analysisType]?.name}
            </span>
            <span className="text-[10px] text-[#0066FF] border border-[#0066FF]/30 bg-[#EAF3FF] px-2 py-0.5 rounded font-semibold">
              {modelLabels[analysisType]?.model}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <div className={`px-2.5 py-0.5 rounded border text-[11px] font-bold ${statusBanner.bg} ${statusBanner.color}`}>
            {statusBanner.text}
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
        </div>
      </div>

      {/* Main Mode View */}
      {isImageMode ? (
        <div className="flex flex-col space-y-4">
          <ImageAnalysisView />
          <AnalysisHistory />
        </div>
      ) : (
        <div className="flex flex-col space-y-4">
          {/* Uploading Spinner */}
          {isUploading && (
            <div className="flex items-center justify-center p-6 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl font-mono text-xs text-[#5B6472] shadow-sm">
              <div className="w-4 h-4 border-2 border-[#0066FF] border-t-transparent rounded-full animate-spin mr-3" />
              <span>Uploading video and extracting frame headers...</span>
            </div>
          )}

          {/* Render Upload if no active job and not uploading */}
          {!activeJob && !isUploading ? (
            <UploadMedia />
          ) : activeJob ? (
            <>
              {/* Video Preview: Strictly PAUSED on Upload */}
              <VideoPreview
                onStartAnalysis={handleStartAnalysis}
                onClear={resetAnalysis}
              />

              {/* Lifecycle Controls */}
              <AnalysisControls />

              {/* Real-time Dynamic ETA & Speed */}
              {(activeJob?.status === "ANALYZING" || activeJob?.status === "PAUSED") && (
                <AnalysisETA />
              )}

              {/* Frame-by-Frame Progress & Counters */}
              {(activeJob?.status === "ANALYZING" ||
                activeJob?.status === "PAUSED" ||
                activeJob?.status === "QUEUED" ||
                activeJob?.status === "UPLOADED") && (
                <AnalysisProgress />
              )}

              {/* Post-Analysis Summary Report & Analyzed Video */}
              {activeJob?.status === "COMPLETED" && <AnalysisResults />}
            </>
          ) : null}

          {/* Job History */}
          <AnalysisHistory />
        </div>
      )}
    </div>
  );
};
