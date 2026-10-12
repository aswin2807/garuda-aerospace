"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

export const ClassificationBreakdown: React.FC = () => {
  const detections = useDroneStore((s) => s.detections);
  const counts = useDroneStore((s) => s.counts);
  const modelClasses = useDroneStore((s) => s.modelClasses);

  // Dynamic class counts from active detections
  const activeClassCounts = detections.reduce((acc, d) => {
    const name = (d.class_name || "UNKNOWN").toUpperCase();
    acc[name] = (acc[name] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Ensure standard classes show at least backend counts
  if (counts.fod > 0 && !activeClassCounts["FOD"]) activeClassCounts["FOD"] = counts.fod;
  if (counts.light_on > 0 && !activeClassCounts["LIGHT ON"]) activeClassCounts["LIGHT ON"] = counts.light_on;
  if (counts.light_off > 0 && !activeClassCounts["LIGHT OFF"]) activeClassCounts["LIGHT OFF"] = counts.light_off;

  const uniqueClasses = Array.from(new Set([
    ...Object.keys(activeClassCounts),
    ...Object.values(modelClasses).map((c) => c.toUpperCase())
  ])).filter(Boolean);

  const displayList = uniqueClasses.length > 0 ? uniqueClasses : ["FOD", "LIGHT ON", "LIGHT OFF", "NAVIGATION"];

  return (
    <div className="p-3 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg space-y-2 font-mono text-xs select-none transition-all">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1.5">
        <span className="text-[10px] text-[#111827] font-bold uppercase tracking-wider">
          Classification Breakdown
        </span>
        <span className="text-[10px] text-[#0066FF] font-mono">
          {detections.length} Total
        </span>
      </div>

      <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
        {displayList.map((clsName) => {
          const count = activeClassCounts[clsName] || 0;

          return (
            <div key={clsName} className="flex justify-between items-center py-0.5">
              <span className="flex items-center space-x-2 text-[#111827]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
                <span className="truncate max-w-[130px]">{clsName}</span>
              </span>
              <span className="font-bold text-[#0066FF]">
                {count.toString().padStart(2, "0")}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ClassificationBreakdown;
