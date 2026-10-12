"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

export const RunwayAlerts: React.FC = () => {
  const alerts = useDroneStore((s) => s.alerts);

  return (
    <div className="space-y-2 p-3 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg font-mono text-xs select-none transition-all">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1.5">
        <span className="text-[10px] text-[#111827] font-bold uppercase tracking-wider flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              alerts.length > 0 ? "bg-[#0066FF] animate-ping" : "bg-[#0066FF]"
            }`}
          />
          Active Runway Alerts
        </span>
        <span className="text-[10px] text-[#5B6472] font-mono">
          {alerts.length} {alerts.length === 1 ? "alert" : "alerts"}
        </span>
      </div>

      {alerts.length === 0 ? (
        <div className="text-[11px] text-[#0066FF] py-2.5 px-2 text-center bg-[#EAF3FF] rounded border border-[#0066FF]/30 font-medium">
          ✓ Runway clear • No active hazards
        </div>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {alerts.map((alert, idx) => {
            const isCritical =
              alert.severity === "CRITICAL" ||
              alert.event_type === "FOD_DETECTED" ||
              alert.class_name === "FOD";
            const isConfirmed = alert.status === "CONFIRMED";

            return (
              <div
                key={alert.id || idx}
                className={`p-2.5 rounded-lg border text-[11px] font-mono ${
                  isCritical
                    ? "border-red-400 bg-red-50 text-red-900 animate-pulse"
                    : "border-[#D9DEE7] bg-[#F5F7FA] text-[#111827]"
                }`}
              >
                <div className="flex items-center justify-between font-bold">
                  <span className="flex items-center space-x-1.5">
                    <span>⚠️</span>
                    <span className="tracking-wide uppercase">
                      {alert.event_type === "RUNWAY_LIGHT_FAULT"
                        ? "RUNWAY LIGHT FAULT"
                        : alert.event_type ||
                          (alert.class_name === "FOD" ? "FOD DETECTED" : "RUNWAY HAZARD")}
                    </span>
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#EAF3FF] border border-[#0066FF]/30 text-[#0066FF] font-bold uppercase">
                    {alert.status || (isConfirmed ? "CONFIRMED" : "POTENTIAL")}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-1 mt-1.5 text-[10px] text-[#5B6472]">
                  {alert.consecutive_frames !== undefined && (
                    <div>
                      <span className="text-[#5B6472]">Duration: </span>
                      <strong className="text-[#111827]">
                        {(alert.consecutive_frames * 0.1).toFixed(1)}s ({alert.consecutive_frames} frames)
                      </strong>
                    </div>
                  )}
                  {alert.confidence !== undefined && (
                    <div>
                      <span className="text-[#5B6472]">Confidence: </span>
                      <strong className="text-[#0066FF]">
                        {Math.round(alert.confidence * 100)}%
                      </strong>
                    </div>
                  )}
                </div>

                {alert.message && (
                  <div className="text-[10px] text-[#5B6472] mt-1 pt-1 border-t border-[#D9DEE7] truncate">
                    {alert.message}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default RunwayAlerts;
