"use client";

import React from "react";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { DroneStatus } from "./DroneStatus";
import { DetectionPanel } from "./DetectionPanel";
import { TelemetryPanel } from "./TelemetryPanel";
import { LiveCamera } from "../camera/LiveCamera";

export const HudLayout: React.FC = () => {
  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans">
      {/* Top Bar */}
      <TopBar />

      {/* Main Workspace with Sidebar */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />

        {/* Center Mission Control Grid */}
        <div className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden bg-[#F5F7FA]">
          {/* Left Column: Drone Status & Telemetry */}
          <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto">
            <DroneStatus />
          </div>

          {/* Center Column: Live Camera & Detection Canvas */}
          <div className="col-span-6 flex flex-col h-full overflow-hidden">
            <LiveCamera />
          </div>

          {/* Right Column: Real-time Detections & Class Summary */}
          <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto">
            <DetectionPanel />
          </div>
        </div>
      </div>

      {/* Bottom Telemetry Ticker */}
      <TelemetryPanel />
    </div>
  );
};
