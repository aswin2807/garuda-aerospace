"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

export const DetectionCards: React.FC = () => {
  const counts = useDroneStore((s) => s.counts);
  const detections = useDroneStore((s) => s.detections);

  // Fallback to active detections if counts not yet initialized
  const lightOnCount = counts.light_on ?? detections.filter((d) => (d.class_name || "").toUpperCase().includes("LIGHT ON")).length;
  const lightOffCount = counts.light_off ?? detections.filter((d) => (d.class_name || "").toUpperCase().includes("LIGHT OFF") || d.state === "OFF-GAP").length;
  const fodCount = counts.fod ?? detections.filter((d) => (d.class_name || "").toUpperCase().includes("FOD")).length;
  const navCount = counts.navigation ?? detections.filter((d) => d.model === "navigation").length;

  return (
    <div className="grid grid-cols-4 gap-2 font-mono select-none">
      {/* LIGHT ON Card */}
      <div className="p-2.5 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg text-center transition-all">
        <div className="text-[10px] text-[#5B6472] font-bold uppercase tracking-wider mb-1 flex items-center justify-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF] animate-pulse" />
          LIGHT ON
        </div>
        <div className="text-2xl font-black text-[#0066FF]">
          {lightOnCount.toString().padStart(2, "0")}
        </div>
      </div>

      {/* LIGHT OFF Card */}
      <div className="p-2.5 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg text-center transition-all">
        <div className="text-[10px] text-[#5B6472] font-bold uppercase tracking-wider mb-1 flex items-center justify-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#008CFF] animate-pulse" />
          LIGHT OFF
        </div>
        <div className="text-2xl font-black text-[#0066FF]">
          {lightOffCount.toString().padStart(2, "0")}
        </div>
      </div>

      {/* FOD Card */}
      <div className="p-2.5 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg text-center transition-all">
        <div className="text-[10px] text-[#5B6472] font-bold uppercase tracking-wider mb-1 flex items-center justify-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF] animate-ping" />
          FOD
        </div>
        <div className="text-2xl font-black text-[#0066FF]">
          {fodCount.toString().padStart(2, "0")}
        </div>
      </div>

      {/* NAV OBJ Card */}
      <div className="p-2.5 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg text-center transition-all">
        <div className="text-[10px] text-[#5B6472] font-bold uppercase tracking-wider mb-1 flex items-center justify-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
          NAV OBJ
        </div>
        <div className="text-2xl font-black text-[#0066FF]">
          {navCount.toString().padStart(2, "0")}
        </div>
      </div>
    </div>
  );
};

export default DetectionCards;
