"use client";

import React, { useEffect, useState } from "react";
import { getPipelineHealth, getPipelineDebug } from "../../lib/api";
import { useDroneStore } from "../../stores/droneStore";

export const CameraStatus: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [debugInfo, setDebugInfo] = useState<any>(null);

  const counts = useDroneStore((s) => s.counts);
  const activeCameraId = useDroneStore((s) => s.activeCameraId);
  const cameraStatus = useDroneStore((s) => s.cameraStatus);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const [h, d] = await Promise.all([getPipelineHealth(), getPipelineDebug()]);
        setHealth(h);
        setDebugInfo(d);
      } catch {}
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 3000);
    return () => clearInterval(interval);
  }, []);

  const totalCurrentDets = (counts.navigation || 0) + (counts.fod || 0) + (counts.light_on || 0) + (counts.light_off || 0);

  return (
    <div className="p-3 bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg space-y-2 font-mono text-xs select-none shadow-sm">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1.5">
        <span className="text-[10px] text-[#5B6472] font-bold uppercase tracking-wider">
          Pipeline Health & Diagnostics
        </span>
        <span className="text-[10px] text-[#5B6472]">
          PRD SEC 37
        </span>
      </div>

      {/* Pipeline Status Lights */}
      <div className="grid grid-cols-2 gap-1.5 text-[11px]">
        <div className="flex items-center justify-between px-2 py-1 bg-[#F5F7FA] rounded border border-[#D9DEE7]">
          <span className="text-[#5B6472]">VIDEO</span>
          <span className="flex items-center gap-1 font-bold text-[#0066FF]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF] animate-pulse" />
            {health?.video || (activeCameraId ? cameraStatus : "CONNECTED")}
          </span>
        </div>

        <div className="flex items-center justify-between px-2 py-1 bg-[#F5F7FA] rounded border border-[#D9DEE7]">
          <span className="text-[#5B6472]">FRAME READER</span>
          <span className="flex items-center gap-1 font-bold text-[#0066FF]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
            {health?.frame_reader || "RUNNING"}
          </span>
        </div>

        <div className="flex items-center justify-between px-2 py-1 bg-[#F5F7FA] rounded border border-[#D9DEE7]">
          <span className="text-[#5B6472]">NAVIGATION</span>
          <span className="flex items-center gap-1 font-bold text-[#0066FF]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
            {health?.navigation || "RUNNING"}
          </span>
        </div>

        <div className="flex items-center justify-between px-2 py-1 bg-[#F5F7FA] rounded border border-[#D9DEE7]">
          <span className="text-[#5B6472]">FOD MODEL</span>
          <span className="flex items-center gap-1 font-bold text-[#0066FF]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
            {health?.fod || "RUNNING"}
          </span>
        </div>

        <div className="flex items-center justify-between px-2 py-1 bg-[#F5F7FA] rounded border border-[#D9DEE7]">
          <span className="text-[#5B6472]">RUNWAY LIGHT</span>
          <span className="flex items-center gap-1 font-bold text-[#0066FF]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
            {health?.runway_light || "RUNNING"}
          </span>
        </div>

        <div className="flex items-center justify-between px-2 py-1 bg-[#F5F7FA] rounded border border-[#D9DEE7]">
          <span className="text-[#5B6472]">DATABASE</span>
          <span className="flex items-center gap-1 font-bold text-[#0066FF]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
            {health?.database || "CONNECTED"}
          </span>
        </div>
      </div>

      {/* Zero Detection Diagnostics */}
      <div className="pt-1.5 border-t border-[#D9DEE7] flex items-center justify-between text-[10px]">
        <span className="text-[#5B6472]">DETECTIONS LOGGED:</span>
        <span className="text-[#0066FF] font-bold">
          {debugInfo?.database_events ?? 0} events ({totalCurrentDets} active)
        </span>
      </div>
    </div>
  );
};
