"use client";

import React, { useEffect } from "react";
import { useAnalysisStore } from "../../stores/analysisStore";
import { useAnalysis } from "../../hooks/useAnalysis";
import { AnalysisJob } from "../../types/detection";

export const AnalysisHistory: React.FC<{ filterType?: string }> = ({ filterType }) => {
  const jobHistory = useAnalysisStore((s) => s.jobHistory);
  const activeAnalysisType = useAnalysisStore((s) => s.analysisType);
  const targetType = filterType || activeAnalysisType;

  const setActiveJob = useAnalysisStore((s) => s.setActiveJob);
  const { fetchHistory, fetchResults } = useAnalysis();

  useEffect(() => {
    fetchHistory(targetType);
  }, [fetchHistory, targetType]);

  const handleSelectJob = async (job: AnalysisJob) => {
    setActiveJob(job);
    const jid = job.job_id || job.id;
    if (job.status === "COMPLETED" && jid) {
      await fetchResults(jid);
    }
  };

  const filteredJobs = targetType
    ? jobHistory.filter((j) => (j.analysis_type || "NAVIGATION").toUpperCase() === targetType.toUpperCase())
    : jobHistory;

  if (!filteredJobs || filteredJobs.length === 0) return null;

  return (
    <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-4 font-mono shadow-sm flex flex-col space-y-3">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2">
        <div className="flex items-center space-x-2">
          <svg className="w-4 h-4 text-[#0066FF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs font-bold text-[#111827] uppercase tracking-wider">
            {targetType.replace("_", " ")} ANALYSIS HISTORY ({filteredJobs.length})
          </span>
        </div>

        <button
          onClick={() => fetchHistory(targetType)}
          className="text-[11px] text-[#5B6472] hover:text-[#0066FF] transition-colors"
        >
          Refresh List
        </button>
      </div>

      <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
        {filteredJobs.map((job) => {
          const jid = job.job_id || job.id || "";
          const jtype = (job.analysis_type || "NAVIGATION").toUpperCase();
          return (
            <div
              key={jid}
              onClick={() => handleSelectJob(job)}
              className="flex items-center justify-between p-2.5 rounded-lg bg-[#F5F7FA] hover:bg-[#F0F6FF] border border-[#D9DEE7] cursor-pointer transition-colors group"
            >
              <div className="flex items-center space-x-3">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                    job.media_type === "VIDEO"
                      ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30"
                      : "bg-[#FFFFFF] text-[#111827] border-[#D9DEE7]"
                  }`}
                >
                  {job.media_type}
                </span>

                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-[#111827] group-hover:text-[#0066FF] transition-colors truncate max-w-xs">
                    {job.filename || job.video_name}
                  </span>
                  <span className="text-[10px] text-[#5B6472]">
                    {job.processed_frames} / {job.total_frames} frames • ID: {jid.slice(0, 8)}...
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                {/* Isolated Detections Summary */}
                <div className="hidden sm:flex items-center space-x-2 text-[10px]">
                  {jtype === "NAVIGATION" && (
                    <span className="text-[#0066FF] font-semibold">Nav: {job.nav_count}</span>
                  )}
                  {jtype === "FOD" && (
                    <span className="text-[#111827] font-semibold">FOD: {job.fod_count}</span>
                  )}
                  {jtype === "RUNWAY_LIGHT" && (
                    <>
                      <span className="text-[#0066FF] font-semibold">ON: {job.light_on_count}</span>
                      <span className="text-[#5B6472]">OFF: {job.light_off_count}</span>
                      {job.confirmed_faults > 0 && (
                        <span className="text-rose-600 font-bold">Faults: {job.confirmed_faults}</span>
                      )}
                    </>
                  )}
                </div>

                {/* Status Badge */}
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                    job.status === "COMPLETED"
                      ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30"
                      : job.status === "ANALYZING"
                      ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30 animate-pulse"
                      : job.status === "PAUSED"
                      ? "bg-amber-50 text-amber-700 border-amber-300"
                      : "bg-[#FFFFFF] text-[#5B6472] border-[#D9DEE7]"
                  }`}
                >
                  {job.status}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
