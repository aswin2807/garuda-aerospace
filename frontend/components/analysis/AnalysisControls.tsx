"use client";

import React from "react";
import { useAnalysisStore } from "../../stores/analysisStore";
import { useAnalysis } from "../../hooks/useAnalysis";

export const AnalysisControls: React.FC = () => {
  const activeJob = useAnalysisStore((s) => s.activeJob);
  const resetAnalysis = useAnalysisStore((s) => s.resetAnalysis);
  const { start, pause, resume, cancel, loading } = useAnalysis();

  if (!activeJob) return null;

  const jobId = activeJob.job_id || activeJob.id || "";
  const status = activeJob.status || "QUEUED";
  const isAwaitingStart = status === "UPLOADED" || status === "QUEUED";
  const isAnalyzing = status === "ANALYZING";
  const isPaused = status === "PAUSED";
  const isDone = status === "COMPLETED" || status === "CANCELLED" || status === "FAILED";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl font-mono shadow-sm">
      <div className="flex items-center space-x-2">
        <span className="text-[11px] text-[#5B6472] uppercase tracking-wider">
          STATUS:
        </span>
        <span
          className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider border ${
            isAnalyzing
              ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30 animate-pulse"
              : isPaused
              ? "bg-amber-50 text-amber-700 border-amber-200"
              : status === "COMPLETED"
              ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30"
              : status === "CANCELLED"
              ? "bg-[#F5F7FA] text-[#5B6472] border-[#D9DEE7]"
              : "bg-[#F5F7FA] text-[#0066FF] border-[#D9DEE7]"
          }`}
        >
          {status}
        </span>
      </div>

      <div className="flex items-center space-x-2">
        {isAwaitingStart && (
          <button
            onClick={() => jobId && start(jobId)}
            disabled={loading || !jobId}
            className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] text-[#FFFFFF] text-xs font-bold shadow-sm shadow-[#0066FF]/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
          >
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
            <span>START ANALYSIS</span>
          </button>
        )}

        {isAnalyzing && (
          <>
            <button
              onClick={() => jobId && pause(jobId)}
              disabled={loading || !jobId}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
              </svg>
              <span>PAUSE</span>
            </button>

            <button
              onClick={() => jobId && cancel(jobId)}
              disabled={loading || !jobId}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 text-xs font-bold transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>CANCEL</span>
            </button>
          </>
        )}

        {isPaused && (
          <>
            <button
              onClick={() => jobId && resume(jobId)}
              disabled={loading || !jobId}
              className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] text-[#FFFFFF] text-xs font-bold shadow-sm shadow-[#0066FF]/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
              <span>RESUME ANALYSIS</span>
            </button>

            <button
              onClick={() => jobId && cancel(jobId)}
              disabled={loading || !jobId}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 text-xs font-bold transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>CANCEL</span>
            </button>
          </>
        )}

        {isDone && (
          <button
            onClick={() => resetAnalysis()}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#F0F6FF] text-[#111827] text-xs font-bold border border-[#D9DEE7] transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>NEW ANALYSIS</span>
          </button>
        )}
      </div>
    </div>
  );
};
