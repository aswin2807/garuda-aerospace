"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

/**
 * NavigationObjects — Displays live navigation object detections (PRD Section 5 & 36)
 * Lists objects identified by navigation_best.pt with confidence, track ID, and spatial coordinates.
 */
export const NavigationObjects: React.FC = () => {
  const detections = useDroneStore((s) => s.detections);
  const counts = useDroneStore((s) => s.counts);
  const navigationModel = useDroneStore((s) => s.navigationModel);
  const confidenceThreshold = useDroneStore((s) => s.confidenceThreshold);

  // Filter navigation model detections above threshold
  const navDetections = detections.filter(
    (d) =>
      (d.model === "navigation" || (!d.model && !d.class_name?.toUpperCase().includes("LIGHT") && !d.class_name?.toUpperCase().includes("FOD"))) &&
      d.confidence >= confidenceThreshold
  );

  const activeCount = counts.navigation ?? navDetections.length;

  return (
    <div className="p-3 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg space-y-2 font-mono text-xs select-none transition-all">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1.5">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-pulse" />
          <span className="text-[10px] text-[#111827] font-bold uppercase tracking-wider">
            Navigation Objects
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30 font-bold">
            NAV: {navigationModel?.loaded !== false ? "READY" : "OFF"}
          </span>
          <span className="text-[10px] font-bold text-[#0066FF]">
            {activeCount.toString().padStart(2, "0")}
          </span>
        </div>
      </div>

      {/* Detections List */}
      {navDetections.length === 0 ? (
        <div className="text-[11px] text-[#5B6472] py-3 text-center bg-[#F5F7FA] rounded border border-[#D9DEE7]">
          No navigation objects currently in view
        </div>
      ) : (
        <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          {navDetections.map((det, idx) => {
            const confPct = Math.round(det.confidence * 100);
            return (
              <div
                key={det.track_id !== undefined ? `nav-${det.track_id}-${idx}` : `nav-${idx}`}
                className="flex items-center justify-between p-2 rounded bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] transition-all text-[11px]"
              >
                <div className="flex items-center space-x-2 min-w-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF] flex-shrink-0" />
                  <span className="font-bold text-[#111827] truncate">
                    {det.class_name || "NAV_OBJECT"}
                  </span>
                  {det.track_id !== undefined && (
                    <span className="text-[9px] px-1 py-0.2 rounded bg-[#FFFFFF] text-[#5B6472] border border-[#D9DEE7] font-mono">
                      #{det.track_id}
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-2 font-mono flex-shrink-0">
                  {Array.isArray(det.bbox) && det.bbox.length >= 2 && (
                    <span className="text-[9px] text-[#5B6472] hidden sm:inline">
                      [{det.bbox[0]},{det.bbox[1]}]
                    </span>
                  )}
                  <span className="font-bold text-[#0066FF]">
                    {confPct}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default NavigationObjects;
