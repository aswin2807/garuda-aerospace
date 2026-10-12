"use client";

import React, { useState } from "react";
import { TopBar } from "./TopBar";
import { Sidebar, SidebarFocusMode } from "./Sidebar";
import { DroneStatus } from "./DroneStatus";
import { DetectionPanel } from "./DetectionPanel";
import { TelemetryPanel } from "./TelemetryPanel";
import { LiveCamera } from "../camera/LiveCamera";
import { VideoPlayer } from "../camera/VideoPlayer";
import { DetectionCards } from "../detection/DetectionCards";
import { DetectionStats } from "../detection/DetectionStats";
import { ClassificationBreakdown } from "../detection/ClassificationBreakdown";
import { RunwayAlerts } from "../runway/RunwayAlerts";
import { RunwayLightStatus } from "../runway/RunwayLightStatus";
import { NavigationObjects } from "../navigation/NavigationObjects";
import { AnalysisWorkspace } from "../analysis/AnalysisWorkspace";
import { useDroneStore } from "../../stores/droneStore";
import { useAnalysisStore } from "../../stores/analysisStore";

/**
 * NavigationHUD — Main unified HUD component per PRD Section 4 & 29
 * Integrates:
 * 1. 📡 LIVE CAMERA (Real-time RTSP/drone streaming & live tri-model inference)
 * 2. 🎥 VIDEO ANALYSIS (Frame-by-frame offline analysis with dynamic ETA & strict pause on upload)
 * 3. 📷 IMAGE ANALYSIS (Static photo tri-model YOLO inspection)
 * 4. 🧭 TACTICAL SIDEBAR (Black/White/Blue aviation command panel)
 */
export const NavigationHUD: React.FC = () => {
  const [hudViewMode, setHudViewMode] = useState<"standard" | "analytics">("standard");
  const [useDedicatedVideoPlayer, setUseDedicatedVideoPlayer] = useState(false);
  const [sidebarFocus, setSidebarFocus] = useState<SidebarFocusMode>("all");
  const activeSessionId = useDroneStore((s) => s.activeSessionId);

  const analysisMode = useAnalysisStore((s) => s.mode);
  const setAnalysisMode = useAnalysisStore((s) => s.setMode);

  const handleSidebarSelect = (mode: SidebarFocusMode) => {
    setSidebarFocus(mode);
    if (mode === "runway") {
      setHudViewMode("analytics");
    } else if (mode === "all") {
      setHudViewMode("standard");
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      {/* Top Bar with Live Model Indicators and System Status */}
      <TopBar />

      {/* Mode & View Mode Toolbar */}
      <div className="bg-[#FFFFFF] border-b border-[#D9DEE7] px-4 py-1.5 flex items-center justify-between text-xs font-mono">
        {/* Three Primary Analysis Modes */}
        <div className="flex items-center space-x-3">
          <span className="text-[#5B6472] font-bold uppercase tracking-wider text-[11px]">
            MODE:
          </span>
          <div className="flex items-center space-x-1 bg-[#F5F7FA] border border-[#D9DEE7] rounded p-0.5">
            <button
              onClick={() => setAnalysisMode("LIVE_CAMERA")}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-[11px] font-bold transition-all ${
                analysisMode === "LIVE_CAMERA"
                  ? "bg-[#0066FF] text-[#FFFFFF] shadow-sm shadow-[#0066FF]/20"
                  : "text-[#5B6472] hover:text-[#111827]"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
              <span>📡 LIVE CAMERA</span>
            </button>

            <button
              onClick={() => setAnalysisMode("VIDEO")}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-[11px] font-bold transition-all ${
                analysisMode === "VIDEO"
                  ? "bg-[#0066FF] text-[#FFFFFF] shadow-sm shadow-[#0066FF]/20"
                  : "text-[#5B6472] hover:text-[#111827]"
              }`}
            >
              <span>🎥 VIDEO ANALYSIS</span>
            </button>

            <button
              onClick={() => setAnalysisMode("IMAGE")}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-[11px] font-bold transition-all ${
                analysisMode === "IMAGE"
                  ? "bg-[#0066FF] text-[#FFFFFF] shadow-sm shadow-[#0066FF]/20"
                  : "text-[#5B6472] hover:text-[#111827]"
              }`}
            >
              <span>📷 IMAGE ANALYSIS</span>
            </button>
          </div>
        </div>

        {/* Live Camera Specific View Controls */}
        {analysisMode === "LIVE_CAMERA" ? (
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1 bg-[#F5F7FA] border border-[#D9DEE7] rounded p-0.5">
              <button
                onClick={() => setHudViewMode("standard")}
                className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  hudViewMode === "standard"
                    ? "bg-[#FFFFFF] text-[#0066FF] border border-[#0066FF]/30 font-bold"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                Standard HUD
              </button>
              <button
                onClick={() => setHudViewMode("analytics")}
                className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  hudViewMode === "analytics"
                    ? "bg-[#FFFFFF] text-[#0066FF] border border-[#0066FF]/30 font-bold"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                Runway Analytics
              </button>
            </div>

            {activeSessionId && (
              <span className="text-[#5B6472] text-[10px] bg-[#FFFFFF] px-2 py-0.5 rounded border border-[#D9DEE7]">
                SESSION: <span className="text-[#0066FF] font-bold">{activeSessionId.slice(0, 8)}...</span>
              </span>
            )}

            <label className="flex items-center space-x-1.5 cursor-pointer text-[#5B6472] hover:text-[#111827]">
              <input
                type="checkbox"
                checked={useDedicatedVideoPlayer}
                onChange={(e) => setUseDedicatedVideoPlayer(e.target.checked)}
                className="rounded bg-[#FFFFFF] border-[#D9DEE7] text-[#0066FF] focus:ring-0"
              />
              <span className="text-[11px]">Dedicated Video Panel</span>
            </label>
          </div>
        ) : (
          <div className="flex items-center space-x-2 text-[11px] text-[#5B6472]">
            <span>OFFLINE PROCESSING ENGINE</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]" />
          </div>
        )}
      </div>

      {/* Main Workspace Area with Aviation Sidebar */}
      <div className="flex-1 flex overflow-hidden">
        {/* Leftmost Tactical Command Sidebar */}
        <Sidebar currentFocus={sidebarFocus} onSelectFocus={handleSidebarSelect} />

        {/* Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#F5F7FA]">
          {analysisMode === "LIVE_CAMERA" ? (
            /* Live Camera Mission Control Grid */
            <div className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden bg-[#F5F7FA]">
              {/* Left Column: Drone Status, Flight Telemetry & Light Status */}
              <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pr-1">
                <DroneStatus />
                <RunwayLightStatus />
                <NavigationObjects />
              </div>

              {/* Center Column: Live Camera & Tri-Model Detections */}
              <div className="col-span-6 flex flex-col space-y-2 h-full overflow-hidden">
                {/* Top Detection Summary Cards */}
                <DetectionCards />

                {/* Main Visual Feed Container */}
                <div className="flex-1 min-h-0 relative rounded-lg overflow-hidden border border-[#D9DEE7] bg-[#000000]">
                  {useDedicatedVideoPlayer ? <VideoPlayer /> : <LiveCamera />}
                </div>
              </div>

              {/* Right Column: Real-time Detections & Runway Alerts / Analytics */}
              <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pr-1">
                {hudViewMode === "analytics" ? (
                  <>
                    <DetectionStats />
                    <RunwayAlerts />
                    <ClassificationBreakdown />
                  </>
                ) : (
                  <>
                    <DetectionPanel />
                    <RunwayAlerts />
                  </>
                )}
              </div>
            </div>
          ) : (
            /* Offline Video or Image Analysis Workspace */
            <AnalysisWorkspace />
          )}
        </div>
      </div>

      {/* Bottom Telemetry Ticker */}
      <TelemetryPanel />
    </div>
  );
};

export default NavigationHUD;
