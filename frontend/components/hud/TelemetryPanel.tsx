"use client";

import React from "react";
import { useDroneStore } from "../../stores/droneStore";

export const TelemetryPanel: React.FC = () => {
  const telemetry = useDroneStore((s) => s.telemetry);
  const fps = useDroneStore((s) => s.fps);
  const inferenceTimeMs = useDroneStore((s) => s.inferenceTimeMs);
  const connectionStatus = useDroneStore((s) => s.connectionStatus);

  const isConnected = connectionStatus === "CONNECTED" && telemetry !== null;

  return (
    <div className="flex items-center justify-between px-6 py-2.5 bg-[#FFFFFF] border-t border-[#D9DEE7] text-[#5B6472] font-mono text-xs select-none">
      <div className="flex items-center space-x-6">
        <div>
          LAT{" "}
          <span className="text-[#111827] font-semibold">
            {isConnected && telemetry?.latitude !== undefined
              ? `${telemetry.latitude.toFixed(4)}° N`
              : "N/A"}
          </span>
        </div>
        <span className="text-[#D9DEE7]">|</span>
        <div>
          LNG{" "}
          <span className="text-[#111827] font-semibold">
            {isConnected && telemetry?.longitude !== undefined
              ? `${telemetry.longitude.toFixed(4)}° E`
              : "N/A"}
          </span>
        </div>
        <span className="text-[#D9DEE7]">|</span>
        <div>
          ALT{" "}
          <span className="text-[#111827] font-semibold">
            {isConnected && telemetry?.altitude !== undefined
              ? `${telemetry.altitude.toFixed(0)}m`
              : "N/A"}
          </span>
        </div>
        <span className="text-[#D9DEE7]">|</span>
        <div>
          HDG{" "}
          <span className="text-[#111827] font-semibold">
            {isConnected && telemetry?.heading !== undefined
              ? `${telemetry.heading.toFixed(0)}°`
              : "N/A"}
          </span>
        </div>
        <span className="text-[#D9DEE7]">|</span>
        <div>
          SPD{" "}
          <span className="text-[#111827] font-semibold">
            {isConnected && telemetry?.speed !== undefined
              ? `${telemetry.speed.toFixed(0)} km/h`
              : "N/A"}
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <div>
          INFERENCE:{" "}
          <span className="text-[#0066FF] font-semibold">
            {inferenceTimeMs > 0 ? `${inferenceTimeMs.toFixed(1)}ms` : "--"}
          </span>
        </div>
        <span className="text-[#D9DEE7]">|</span>
        <div>
          RATE:{" "}
          <span className="text-[#0066FF] font-semibold">
            {fps > 0 ? `${fps} FPS` : "--"}
          </span>
        </div>
        <span className="text-[#D9DEE7]">|</span>
        <div className="flex items-center space-x-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-[#0066FF] animate-pulse" : "bg-[#5B6472]"
            }`}
          />
          <span
            className={`font-semibold ${
              isConnected ? "text-[#111827]" : "text-[#5B6472]"
            }`}
          >
            {isConnected ? "CONNECTED" : "DISCONNECTED"}
          </span>
        </div>
      </div>
    </div>
  );
};


export default TelemetryPanel;
