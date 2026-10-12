"use client";

import React, { useRef, useState, useEffect } from "react";
import { useAnalysisStore } from "../../stores/analysisStore";
import { Play, Pause, AlertCircle, CheckCircle2, Film } from "lucide-react";

interface VideoPreviewProps {
  onStartAnalysis?: () => void;
  onClear?: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const VideoPreview: React.FC<VideoPreviewProps> = ({
  onStartAnalysis,
  onClear,
}) => {
  const activeJob = useAnalysisStore((s) => s.activeJob);
  const filePreviewUrl = useAnalysisStore((s) => s.filePreviewUrl);
  const selectedFile = useAnalysisStore((s) => s.selectedFile);

  const [activeMediaSource, setActiveMediaSource] = useState<"ORIGINAL" | "ANNOTATED">("ORIGINAL");
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  const jobId = activeJob?.job_id || activeJob?.id || "";
  const isCompleted = activeJob?.status === "COMPLETED";
  const isAwaitingStart = activeJob?.status === "UPLOADED" || activeJob?.status === "QUEUED";
  const isAnalyzing = activeJob?.status === "ANALYZING";

  // Derive usable video stream URLs
  const originalStreamUrl = filePreviewUrl || (jobId ? `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/original` : null);
  const annotatedStreamUrl = jobId ? `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/video` : null;

  // Auto-switch to annotated video once analysis completes
  useEffect(() => {
    if (isCompleted && annotatedStreamUrl) {
      setActiveMediaSource("ANNOTATED");
    } else {
      setActiveMediaSource("ORIGINAL");
    }
  }, [isCompleted, annotatedStreamUrl]);

  // Reset playback errors on URL change
  useEffect(() => {
    setPlaybackError(null);
  }, [activeMediaSource, originalStreamUrl, annotatedStreamUrl]);

  if (!activeJob && !selectedFile) return null;

  const currentVideoUrl = activeMediaSource === "ANNOTATED" ? annotatedStreamUrl : originalStreamUrl;

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "00:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl overflow-hidden shadow-sm">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-[#FFFFFF] border-b border-[#D9DEE7] gap-2">
        <div className="flex items-center space-x-2">
          <Film className="w-4 h-4 text-[#0066FF]" />
          <span className="font-mono text-xs font-bold text-[#111827] tracking-wider uppercase">
            {activeMediaSource === "ANNOTATED" ? "AI ANNOTATED OUTPUT" : "ORIGINAL INPUT VIDEO"}
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#F5F7FA] text-[#5B6472] border border-[#D9DEE7] truncate max-w-[200px]">
            {activeJob?.filename || selectedFile?.name}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Toggle between Original and Annotated Output once available */}
          {isCompleted && (
            <div className="flex items-center bg-[#F5F7FA] p-0.5 rounded-lg border border-[#D9DEE7] text-[11px] font-mono">
              <button
                onClick={() => setActiveMediaSource("ORIGINAL")}
                className={`px-2.5 py-1 rounded font-semibold transition ${
                  activeMediaSource === "ORIGINAL"
                    ? "bg-[#0066FF] text-white"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                Original
              </button>
              <button
                onClick={() => setActiveMediaSource("ANNOTATED")}
                className={`px-2.5 py-1 rounded font-semibold transition ${
                  activeMediaSource === "ANNOTATED"
                    ? "bg-[#0066FF] text-white"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                Annotated AI Output
              </button>
            </div>
          )}

          {onClear && isAwaitingStart && (
            <button
              onClick={onClear}
              className="text-[11px] font-mono text-[#5B6472] hover:text-rose-600 transition-colors px-2 py-1 rounded hover:bg-[#F0F6FF]"
            >
              Clear / Change Video
            </button>
          )}
        </div>
      </div>

      {/* Main Video View Container */}
      <div className="relative aspect-video bg-[#000000] flex items-center justify-center overflow-hidden">
        {currentVideoUrl ? (
          <video
            ref={videoRef}
            key={currentVideoUrl}
            src={currentVideoUrl}
            controls
            autoPlay={false}
            playsInline
            preload="metadata"
            onError={() => {
              setPlaybackError("Browser could not decode video stream. Check codec compatibility.");
            }}
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="text-[#5B6472] font-mono text-xs flex flex-col items-center">
            <AlertCircle className="w-6 h-6 mb-1 text-amber-500" />
            <span>Video source unavailable for preview</span>
          </div>
        )}

        {/* Playback Error Toast */}
        {playbackError && (
          <div className="absolute bottom-4 left-4 right-4 p-2.5 bg-red-900/90 border border-red-500 text-white rounded font-mono text-xs flex items-center justify-between">
            <span>{playbackError}</span>
            <button
              onClick={() => setPlaybackError(null)}
              className="text-white hover:underline text-[10px] ml-2"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Pre-Analysis Start Action Bar if waiting to start */}
      {isAwaitingStart && (
        <div className="flex flex-wrap items-center justify-between p-3.5 bg-[#EAF3FF] border-t border-[#0066FF]/30 font-mono text-xs">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-pulse" />
            <span className="font-bold text-[#111827]">
              Video loaded & verified. Ready for sequential frame-by-frame AI analysis.
            </span>
          </div>
          {onStartAnalysis && (
            <button
              onClick={onStartAnalysis}
              className="flex items-center space-x-2 px-4 py-2 bg-[#0066FF] hover:bg-[#008CFF] text-[#FFFFFF] font-bold rounded-lg shadow-sm transition-all transform hover:scale-105 active:scale-95"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>START AI VIDEO ANALYSIS</span>
            </button>
          )}
        </div>
      )}

      {/* Video Metadata Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 bg-[#FFFFFF] border-t border-[#D9DEE7] font-mono text-xs">
        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2">
          <div className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Total Frames
          </div>
          <div className="text-[#111827] font-bold mt-0.5 text-sm">
            {activeJob?.total_frames ? activeJob.total_frames.toLocaleString() : "--"}
          </div>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2">
          <div className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Video Stream FPS
          </div>
          <div className="text-[#0066FF] font-bold mt-0.5 text-sm">
            {activeJob?.video_fps ? `${activeJob.video_fps.toFixed(1)} FPS` : "--"}
          </div>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2">
          <div className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Duration
          </div>
          <div className="text-[#111827] font-bold mt-0.5 text-sm">
            {formatDuration(activeJob?.duration_seconds)}
          </div>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2">
          <div className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Analysis Coverage
          </div>
          <div className="text-[#0066FF] font-bold mt-0.5 text-sm">
            100% Every Frame
          </div>
        </div>
      </div>
    </div>
  );
};
