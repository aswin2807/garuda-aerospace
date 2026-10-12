"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

export const DetectionStats: React.FC = () => {
  const counts = useDroneStore((s) => s.counts);
  const sessionTotals = useDroneStore((s) => s.sessionTotals);
  const summary = useDroneStore((s) => s.summary);
  const alerts = useDroneStore((s) => s.alerts);

  const confirmedFaultsCount = counts.confirmed_faults ?? alerts.filter(
    (a) => a.status === "CONFIRMED" && (a.class_name === "LIGHT OFF" || a.event_type === "RUNWAY_LIGHT_FAULT")
  ).length;

  const navCount = counts.navigation ?? summary?.nav_count ?? 0;
  const fodCount = counts.fod ?? summary?.fod_count ?? 0;
  const lightOnCount = counts.light_on ?? summary?.light_on_count ?? 0;
  const lightOffCount = counts.light_off ?? summary?.light_off_count ?? 0;

  return (
    <div className="p-3 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg space-y-1.5 font-mono text-xs select-none transition-all">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1.5">
        <span className="text-[10px] text-[#111827] font-bold uppercase tracking-wider">
          Detailed Detection Statistics
        </span>
        {sessionTotals?.total_unique ? (
          <span className="text-[10px] text-[#5B6472] font-mono">
            {sessionTotals.total_unique} Unique Tracks
          </span>
        ) : null}
      </div>

      <div className="flex justify-between items-center py-0.5">
        <span className="text-[#5B6472]">Navigation Objects:</span>
        <span className="font-bold text-[#0066FF]">{navCount}</span>
      </div>

      <div className="flex justify-between items-center py-0.5">
        <span className="text-[#5B6472]">FOD Debris Detected:</span>
        <span className="font-bold text-[#0066FF]">{fodCount}</span>
      </div>

      <div className="flex justify-between items-center py-0.5">
        <span className="text-[#5B6472]">Runway Lights Active (ON):</span>
        <span className="font-bold text-[#0066FF]">{lightOnCount}</span>
      </div>

      <div className="flex justify-between items-center py-0.5">
        <span className="text-[#5B6472]">Runway Lights Inactive (OFF):</span>
        <span className="font-bold text-[#0066FF]">{lightOffCount}</span>
      </div>

      <div className="flex justify-between items-center py-1 border-t border-[#D9DEE7] pt-1.5">
        <span className="text-[#111827] font-semibold flex items-center gap-1.5">
          {confirmedFaultsCount > 0 && <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF] animate-ping" />}
          Confirmed Faults:
        </span>
        <span className={`font-black text-sm ${confirmedFaultsCount > 0 ? "text-red-500" : "text-[#0066FF]"}`}>
          {confirmedFaultsCount}
        </span>
      </div>
    </div>
  );
};

export default DetectionStats;
