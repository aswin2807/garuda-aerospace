"use client";

import React from "react";
import { useAnalysisStore } from "../../stores/analysisStore";

export const AnalysisETA: React.FC = () => {
  const activeJob = useAnalysisStore((s) => s.activeJob);

  if (!activeJob) return null;

  const {
    processing_fps = 0,
    video_fps = 30,
    remaining_seconds = 0,
    estimated_finish_time,
    status,
  } = activeJob;

  const isRunning = status === "ANALYZING";

  const formatRemaining = (seconds: number) => {
    if (seconds <= 0) return "Calculating...";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    if (mins > 60) {
      const hrs = Math.floor(mins / 60);
      const remainingMins = mins % 60;
      return `${hrs}h ${remainingMins}m ${secs}s`;
    }
    return `${mins}m ${secs.toString().padStart(2, "0")}s`;
  };

  const speedRatio =
    video_fps > 0 && processing_fps > 0
      ? (processing_fps / video_fps).toFixed(2)
      : "--";

  return (
    <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-4 font-mono shadow-sm relative overflow-hidden">
      {/* Decorative ambient background glow */}
      {isRunning && (
        <div className="absolute top-0 right-0 -mr-12 -mt-12 w-40 h-40 bg-[#0066FF]/5 rounded-full blur-3xl pointer-events-none" />
      )}

      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2 mb-3">
        <div className="flex items-center space-x-2">
          <svg className="w-4 h-4 text-[#0066FF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs font-bold text-[#111827] tracking-wider uppercase">
            DYNAMIC ETA & PROCESSING SPEED
          </span>
        </div>
        <span className="text-[10px] text-[#5B6472] bg-[#F5F7FA] border border-[#D9DEE7] px-2 py-0.5 rounded">
          4 Hz DYNAMIC RECALCULATION
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Estimated Time Remaining */}
        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Time Remaining
          </span>
          <div className="text-base font-bold text-[#0066FF] mt-1">
            {isRunning ? formatRemaining(remaining_seconds) : status === "COMPLETED" ? "00:00 (Completed)" : "--"}
          </div>
          <span className="text-[9px] text-[#5B6472] mt-0.5">
            Dynamic inference ETA
          </span>
        </div>

        {/* Estimated Completion Time */}
        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Est. Finish Clock
          </span>
          <div className="text-base font-bold text-[#111827] mt-1 truncate">
            {estimated_finish_time || "--:--:--"}
          </div>
          <span className="text-[9px] text-[#5B6472] mt-0.5">
            Wall clock finish target
          </span>
        </div>

        {/* Real Processing FPS */}
        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Processing FPS
          </span>
          <div className="text-base font-bold text-[#0066FF] mt-1">
            {processing_fps > 0 ? `${processing_fps.toFixed(1)} FPS` : "-- FPS"}
          </div>
          <span className="text-[9px] text-[#5B6472] mt-0.5">
            Offline YOLO tri-model rate
          </span>
        </div>

        {/* Video FPS vs Processing Speed Ratio */}
        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 flex flex-col justify-between">
          <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
            Speed Ratio
          </span>
          <div className="text-base font-bold text-[#0066FF] mt-1">
            {speedRatio !== "--" ? `${speedRatio}x Realtime` : "--"}
          </div>
          <span className="text-[9px] text-[#5B6472] mt-0.5">
            Video rate: {video_fps.toFixed(1)} FPS
          </span>
        </div>
      </div>
    </div>
  );
};
