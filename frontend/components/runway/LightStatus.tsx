"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

export const LightStatus: React.FC = () => {
  const counts = useDroneStore((s) => s.counts);
  const runwayLightModel = useDroneStore((s) => s.runwayLightModel);

  const activeOn = counts.light_on ?? 0;
  const inactiveOff = counts.light_off ?? 0;
  const confirmedFaults = counts.confirmed_faults ?? 0;

  return (
    <div className="p-3 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-md rounded-lg space-y-2 font-mono text-xs select-none transition-all">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1.5">
        <span className="text-[10px] text-[#111827] font-bold uppercase tracking-wider flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF] animate-pulse" />
          Runway Light Monitoring
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30 font-bold">
          {runwayLightModel?.loaded !== false ? "ACTIVE" : "STANDBY"}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1.5 text-center pt-1">
        <div className="p-1.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[9px] text-[#5B6472] uppercase font-bold">Operational</div>
          <div className="text-base font-bold text-[#0066FF]">{activeOn}</div>
        </div>

        <div className="p-1.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[9px] text-[#5B6472] uppercase font-bold">Faulty (OFF)</div>
          <div className="text-base font-bold text-[#5B6472]">{inactiveOff}</div>
        </div>

        <div className="p-1.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[9px] text-[#5B6472] uppercase font-bold">Confirmed</div>
          <div className={`text-base font-bold ${confirmedFaults > 0 ? "text-rose-600" : "text-[#0066FF]"}`}>{confirmedFaults}</div>
        </div>
      </div>
    </div>
  );
};

export default LightStatus;
