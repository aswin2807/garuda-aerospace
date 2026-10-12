"use client";

import React from "react";
import { useAnalysisStore } from "../../stores/analysisStore";

export const AnalysisProgress: React.FC = () => {
  const activeJob = useAnalysisStore((s) => s.activeJob);

  if (!activeJob) return null;

  const {
    progress = 0,
    processed_frames = 0,
    total_frames = 0,
    elapsed_seconds = 0,
    status,
    nav_count = 0,
    fod_count = 0,
    light_on_count = 0,
    light_off_count = 0,
    confirmed_faults = 0,
  } = activeJob;

  const atype = (activeJob.analysis_type || "NAVIGATION").toUpperCase();
  const isAnalyzing = status === "ANALYZING";
  const percentage = Math.min(100, Math.max(0, Math.round(progress * 10) / 10));

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-4 font-mono shadow-sm flex flex-col space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {isAnalyzing ? (
            <div className="w-2.5 h-2.5 rounded-full bg-[#0066FF] animate-ping" />
          ) : (
            <div className="w-2.5 h-2.5 rounded-full bg-[#D9DEE7]" />
          )}
          <span className="text-xs font-bold text-[#111827] tracking-wider uppercase">
            FRAME-BY-FRAME ANALYSIS PROGRESS
          </span>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <span className="text-[#5B6472]">
            ELAPSED: <span className="text-[#111827] font-bold">{formatElapsed(elapsed_seconds)}</span>
          </span>
          <span className="text-[#0066FF] font-extrabold text-sm">
            {percentage.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Progress Bar Container */}
      <div className="relative w-full h-3.5 bg-[#E5E7EB] rounded-full overflow-hidden border border-[#D9DEE7]">
        <div
          className={`h-full transition-all duration-300 ease-out rounded-full ${
            status === "PAUSED"
              ? "bg-amber-500"
              : "bg-[#0066FF]"
          }`}
          style={{ width: `${percentage}%` }}
        />
        {isAnalyzing && (
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse pointer-events-none" />
        )}
      </div>

      {/* Frame Details Counter */}
      <div className="flex items-center justify-between text-xs text-[#5B6472] border-b border-[#D9DEE7] pb-3">
        <span>
          Processed Frames:{" "}
          <span className="text-[#111827] font-bold">
            {processed_frames.toLocaleString()}
          </span>{" "}
          / {total_frames.toLocaleString()}
        </span>
        <span className="text-[11px] text-[#5B6472]">
          Coverage:{" "}
          <span className="text-[#0066FF] font-bold">
            {total_frames > 0 ? ((processed_frames / total_frames) * 100).toFixed(1) : 0}% Every Frame
          </span>
        </span>
      </div>

      {/* Real-time Detection Counters Ticker - Isolated by analysis_type */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[#5B6472] mb-2 font-bold">
          {atype === "NAVIGATION" && "Navigation Model Detections (navigation_best.pt)"}
          {atype === "FOD" && "FOD Debris Model Detections (FOD_Karhtikeyan.pt)"}
          {atype === "RUNWAY_LIGHT" && "Runway Light Fault Detection (runway_light_best.pt)"}
        </div>

        {atype === "NAVIGATION" && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Nav Objects</div>
              <div className="text-base font-bold text-[#0066FF] mt-0.5">
                {nav_count.toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Unique Tracked</div>
              <div className="text-base font-bold text-[#111827] mt-0.5">
                {(activeJob.unique_nav_count ?? nav_count).toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Processing FPS</div>
              <div className="text-base font-bold text-[#0066FF] mt-0.5">
                {activeJob.processing_fps?.toFixed(1) || "0.0"}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Inference Time</div>
              <div className="text-base font-bold text-[#5B6472] mt-0.5">
                {activeJob.avg_inference_ms ? `${activeJob.avg_inference_ms.toFixed(1)}ms` : "--"}
              </div>
            </div>
          </div>
        )}

        {atype === "FOD" && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Unique FOD Tracked</div>
              <div className="text-base font-bold text-red-600 mt-0.5">
                {(activeJob.unique_fod_count ?? fod_count).toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Total Frame Hits</div>
              <div className="text-base font-bold text-[#0066FF] mt-0.5">
                {(activeJob.total_detections ?? activeJob.total_frame_detections ?? 0).toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Processing Speed</div>
              <div className="text-base font-bold text-[#111827] mt-0.5">
                {activeJob.processing_fps?.toFixed(1) || "0.0"} FPS
              </div>
              <div className="text-[8px] text-[#0066FF] font-semibold">
                {activeJob.speed_ratio ? `${activeJob.speed_ratio.toFixed(2)}x` : ""}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Avg Latency</div>
              <div className="text-base font-bold text-[#5B6472] mt-0.5">
                {activeJob.avg_inference_ms ? `${activeJob.avg_inference_ms.toFixed(1)}ms` : "--"}
              </div>
            </div>
          </div>
        )}

        {atype === "RUNWAY_LIGHT" && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Total Lights</div>
              <div className="text-base font-bold text-[#111827] mt-0.5">
                {(activeJob.total_lights ?? (light_on_count + light_off_count + (activeJob.unknown_light_count ?? 0))).toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Lights Active</div>
              <div className="text-base font-bold text-[#0066FF] mt-0.5">
                {light_on_count.toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Lights Inactive</div>
              <div className="text-base font-bold text-[#5B6472] mt-0.5">
                {light_off_count.toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Unknown / Gaps</div>
              <div className="text-base font-bold text-amber-500 mt-0.5">
                {(activeJob.unknown_light_count ?? 0).toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Confirmed Faults</div>
              <div className="text-base font-bold text-red-500 mt-0.5">
                {confirmed_faults.toLocaleString()}
              </div>
            </div>
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
              <div className="text-[9px] text-[#5B6472] uppercase">Rows Detected</div>
              <div className="text-base font-bold text-[#111827] mt-0.5">
                {(activeJob.rows_detected ?? 0).toLocaleString()}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
