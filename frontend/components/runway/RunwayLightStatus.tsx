"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

/**
 * RunwayLightStatus — Monitors runway lighting health and ON/OFF status (PRD Section 7, 8, 18 & 36)
 * Integrates results from runway_light_best.pt with scan-window metrics and fault confirmation.
 */
export const RunwayLightStatus: React.FC = () => {
  const counts = useDroneStore((s) => s.counts);
  const runwayLightModel = useDroneStore((s) => s.runwayLightModel);
  const detections = useDroneStore((s) => s.detections);

  const activeOn = counts.light_on ?? 0;
  const inactiveOff = counts.light_off ?? 0;
  const confirmedFaults = counts.confirmed_faults ?? 0;

  const totalVisible = activeOn + inactiveOff;
  const healthPercent = totalVisible > 0 ? Math.round((activeOn / totalVisible) * 100) : 100;

  // Check if any detected lights have OFF-GAP state
  const hasOffGaps = detections.some((d) => d.state === "OFF-GAP" || d.inferred);

  return (
    <div className="p-3 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg space-y-2 font-mono text-xs select-none transition-all">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1.5">
        <span className="text-[10px] text-[#111827] font-bold uppercase tracking-wider flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF] animate-pulse" />
          Runway Light Monitoring
        </span>
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
            runwayLightModel?.loaded !== false
              ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30"
              : "bg-[#F5F7FA] text-[#5B6472] border border-[#D9DEE7]"
          }`}
        >
          {runwayLightModel?.loaded !== false ? "READY" : "OFF"}
        </span>
      </div>

      {/* Grid of Key Light Metrics */}
      <div className="grid grid-cols-3 gap-1.5 text-center pt-0.5">
        <div className="p-1.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[9px] text-[#5B6472] uppercase">Operational (ON)</div>
          <div className="text-base font-bold text-[#0066FF]">{activeOn}</div>
        </div>

        <div className="p-1.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[9px] text-[#5B6472] uppercase">Faulty (OFF)</div>
          <div className="text-base font-bold text-[#0066FF]">{inactiveOff}</div>
        </div>

        <div className="p-1.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[9px] text-[#5B6472] uppercase">Confirmed Faults</div>
          <div className={`text-base font-bold ${confirmedFaults > 0 ? "text-red-500" : "text-[#0066FF]"}`}>
            {confirmedFaults}
          </div>
        </div>
      </div>

      {/* Health Bar */}
      <div className="space-y-1 pt-1">
        <div className="flex justify-between items-center text-[10px] text-[#5B6472]">
          <span>Runway Optical Health</span>
          <span className="font-bold text-[#0066FF]">
            {healthPercent}%
          </span>
        </div>
        <div className="w-full bg-[#E5E7EB] border border-[#D9DEE7] rounded-full h-1.5 overflow-hidden">
          <div
            className="h-full transition-all duration-300 rounded-full bg-[#0066FF]"
            style={{ width: `${healthPercent}%` }}
          />
        </div>
      </div>

      {/* Contextual Warnings */}
      {hasOffGaps && (
        <div className="px-2 py-1 rounded bg-amber-50 border border-amber-200 text-[10px] text-amber-700 flex items-center gap-1.5">
          <span>⚠️</span>
          <span>Missing beacon detected via runway light row spacing</span>
        </div>
      )}
    </div>
  );
};

export default RunwayLightStatus;
