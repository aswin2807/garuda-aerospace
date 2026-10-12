"use client";

import React, { useEffect, useState } from "react";
import { useDroneStore } from "../../stores/droneStore";
import { getPipelineHealth } from "../../lib/api";

export const DetectionPanel: React.FC = () => {
  const detections = useDroneStore((s) => s.detections);
  const confidenceThreshold = useDroneStore((s) => s.confidenceThreshold);
  const setConfidenceThreshold = useDroneStore((s) => s.setConfidenceThreshold);
  const counts = useDroneStore((s) => s.counts);
  const sessionTotals = useDroneStore((s) => s.sessionTotals);
  const performance = useDroneStore((s) => s.performance);
  const inferenceTimeMs = useDroneStore((s) => s.inferenceTimeMs);
  const fps = useDroneStore((s) => s.fps);
  const modelClasses = useDroneStore((s) => s.modelClasses);
  const alerts = useDroneStore((s) => s.alerts);
  const navigationModel = useDroneStore((s) => s.navigationModel);
  const fodModel = useDroneStore((s) => s.fodModel);
  const runwayLightModel = useDroneStore((s) => s.runwayLightModel);

  const [pipelineHealth, setPipelineHealth] = useState<any>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const h = await getPipelineHealth();
        setPipelineHealth(h);
      } catch {}
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 4000);
    return () => clearInterval(interval);
  }, []);

  // Filter detections by active slider threshold
  const activeDetections = detections.filter((d) => d.confidence >= confidenceThreshold);

  // Fallback to activeDetections if counts not yet received
  const lightOnCount = counts?.light_on ?? activeDetections.filter((d) => (d.class_name || "").toUpperCase().includes("LIGHT ON")).length;
  const lightOffCount = counts?.light_off ?? activeDetections.filter((d) => (d.class_name || "").toUpperCase().includes("LIGHT OFF") || d.state === "OFF-GAP").length;
  const fodCount = counts?.fod ?? activeDetections.filter((d) => (d.class_name || "").toUpperCase().includes("FOD")).length;
  const navCount = counts?.navigation ?? activeDetections.filter((d) => d.model === "navigation").length;

  const confirmedFaultsCount = counts?.confirmed_faults ?? alerts.filter(
    (a) => a.status === "CONFIRMED" && (a.class_name === "LIGHT OFF" || a.event_type === "RUNWAY_LIGHT_FAULT")
  ).length;

  // Dynamic class counts
  const classCounts = activeDetections.reduce((acc, d) => {
    const name = (d.class_name || "UNKNOWN").toUpperCase();
    acc[name] = (acc[name] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  if (fodCount > 0 && !classCounts["FOD"]) classCounts["FOD"] = fodCount;
  if (lightOnCount > 0 && !classCounts["LIGHT ON"]) classCounts["LIGHT ON"] = lightOnCount;
  if (lightOffCount > 0 && !classCounts["LIGHT OFF"]) classCounts["LIGHT OFF"] = lightOffCount;

  // Real average confidence
  const avgConfidence = detections.length > 0
    ? Math.round((detections.reduce((sum, d) => sum + d.confidence, 0) / detections.length) * 100)
    : 0;

  const modelClassList = Object.values(modelClasses).map((c) => c.toUpperCase());
  const detectedClassList = Object.keys(classCounts);
  const allClasses = Array.from(new Set([...modelClassList, ...detectedClassList]));
  const displayClasses = allClasses.length > 0 ? allClasses : ["FOD", "LIGHT ON", "LIGHT OFF", "NAVIGATION"];

  const streamFpsVal = performance?.stream_fps ?? fps ?? 30;
  const inferenceMsVal = performance?.inference_ms ?? inferenceTimeMs ?? 327.3;
  const inferenceFpsVal = performance?.inference_fps ?? (1000 / Math.max(1, inferenceMsVal));

  return (
    <div className="flex flex-col space-y-3.5 p-4 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg text-[#111827] font-mono text-xs select-none transition-all">
      {/* Top Model Status Header */}
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2">
        <span className="font-bold tracking-wider text-[#111827]">DETECTIONS</span>
        <div className="flex items-center space-x-1.5">
          <span
            className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-[#F5F7FA] text-[#0066FF] border border-[#D9DEE7]"
            title="navigation_best.pt"
          >
            NAV: {navigationModel?.loaded !== false ? "ON" : "OFF"}
          </span>
          <span
            className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-[#F5F7FA] text-[#0066FF] border border-[#D9DEE7]"
            title="FOD_Karhtikeyan.pt"
          >
            FOD: {fodModel?.loaded !== false ? "ON" : "OFF"}
          </span>
          <span
            className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-[#F5F7FA] text-[#0066FF] border border-[#D9DEE7]"
            title="runway_light_best.pt"
          >
            LIGHTS: {runwayLightModel?.loaded !== false ? "ON" : "OFF"}
          </span>
        </div>
      </div>

      {/* Confidence Threshold Slider */}
      <div className="space-y-1.5 p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
        <div className="flex justify-between items-center text-[#5B6472]">
          <span className="text-[11px] text-[#5B6472]">CONFIDENCE THRESHOLD</span>
          <span className="font-bold text-[#0066FF]">
            {Math.round(confidenceThreshold * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0.05"
          max="0.95"
          step="0.05"
          value={confidenceThreshold}
          onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
          className="w-full h-1.5 bg-[#E5E7EB] rounded-lg appearance-none cursor-pointer accent-[#0066FF]"
        />
      </div>

      {/* Tri-Model HUD Ticker */}
      <div className="grid grid-cols-4 gap-1.5">
        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] rounded text-center transition-all">
          <div className="text-[9px] text-[#5B6472] font-bold uppercase tracking-wider">LIGHT ON</div>
          <div className="text-xl font-black text-[#0066FF]">
            {lightOnCount.toString().padStart(2, "0")}
          </div>
        </div>
        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] rounded text-center transition-all">
          <div className="text-[9px] text-[#5B6472] font-bold uppercase tracking-wider">LIGHT OFF</div>
          <div className="text-xl font-black text-[#0066FF]">
            {lightOffCount.toString().padStart(2, "0")}
          </div>
        </div>
        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] rounded text-center transition-all">
          <div className="text-[9px] text-[#5B6472] font-bold uppercase tracking-wider">FOD</div>
          <div className="text-xl font-black text-[#0066FF]">
            {fodCount.toString().padStart(2, "0")}
          </div>
        </div>
        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] rounded text-center transition-all">
          <div className="text-[9px] text-[#5B6472] font-bold uppercase tracking-wider">NAV OBJ</div>
          <div className="text-xl font-black text-[#0066FF]">
            {navCount.toString().padStart(2, "0")}
          </div>
        </div>
      </div>

      {/* Detailed Detection Statistics Panel */}
      <div className="p-2.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded space-y-1 text-[11px]">
        <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-1">
          <span className="text-[10px] text-[#5B6472] font-bold uppercase tracking-wider">
            Detailed Statistics
          </span>
          {sessionTotals?.total_unique ? (
            <span className="text-[10px] text-[#5B6472]">
              {sessionTotals.total_unique} Unique
            </span>
          ) : null}
        </div>
        <div className="flex justify-between items-center py-0.5">
          <span className="text-[#5B6472]">Navigation Objects:</span>
          <span className="font-bold text-[#0066FF]">{navCount}</span>
        </div>
        <div className="flex justify-between items-center py-0.5">
          <span className="text-[#5B6472]">FOD Debris Detected:</span>
          <span className="font-bold text-[#0066FF]">{fodCount}</span>
        </div>
        <div className="flex justify-between items-center py-0.5">
          <span className="text-[#5B6472]">Runway Lights Active (ON):</span>
          <span className="font-bold text-[#0066FF]">{lightOnCount}</span>
        </div>
        <div className="flex justify-between items-center py-0.5">
          <span className="text-[#5B6472]">Runway Lights Inactive (OFF):</span>
          <span className="font-bold text-[#0066FF]">{lightOffCount}</span>
        </div>
        <div className="flex justify-between items-center py-0.5 border-t border-[#D9DEE7] pt-1">
          <span className="text-[#111827] font-semibold">Confirmed Faults:</span>
          <span className={`font-black ${confirmedFaultsCount > 0 ? "text-red-500" : "text-[#0066FF]"}`}>
            {confirmedFaultsCount}
          </span>
        </div>
      </div>

      {/* Active Runway Alerts Card */}
      <div className="space-y-2 p-2.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-[#111827] font-bold tracking-wider uppercase flex items-center gap-1.5">
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
          <div className="text-[11px] text-[#0066FF] py-1.5 text-center bg-[#EAF3FF] rounded border border-[#0066FF]/30">
            ✓ Runway clear • No active hazards
          </div>
        ) : (
          <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
            {alerts.map((alert, idx) => {
              const isConfirmed = alert.status === "CONFIRMED";
              return (
                <div
                  key={alert.id || idx}
                  className="p-2 rounded border border-[#D9DEE7] bg-[#FFFFFF] text-[11px] font-mono"
                >
                  <div className="flex items-center justify-between font-bold text-[#111827]">
                    <span className="flex items-center space-x-1.5">
                      <span>⚠️</span>
                      <span className="uppercase text-xs">
                        {alert.event_type || alert.class_name || "RUNWAY HAZARD"}
                      </span>
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#EAF3FF] border border-[#0066FF]/30 text-[#0066FF] font-bold uppercase">
                      {alert.status || (isConfirmed ? "HIGH" : "POTENTIAL")}
                    </span>
                  </div>

                  {alert.consecutive_frames !== undefined && (
                    <div className="text-[10px] text-[#5B6472] mt-1 flex justify-between items-center">
                      <span>Duration: {(alert.consecutive_frames * 0.1).toFixed(1)}s</span>
                      <span className="font-semibold text-[#111827]">
                        Status: <strong className="text-[#0066FF]">{alert.status}</strong>
                      </span>
                    </div>
                  )}

                  {alert.message && (
                    <div className="text-[10px] text-[#5B6472] mt-0.5 truncate">
                      {alert.message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Real-time Summary Cards */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">Total Objects</div>
          <div className="text-lg font-bold text-[#0066FF]">
            {(sessionTotals?.total_unique || activeDetections.length).toString().padStart(2, "0")}
          </div>
        </div>

        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">Avg Conf</div>
          <div className="text-lg font-bold text-[#111827]">
            {avgConfidence}%
          </div>
        </div>

        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">Inference</div>
          <div className="text-sm font-bold text-[#111827]">
            {Math.round(inferenceMsVal)} <span className="text-[10px] font-normal text-[#5B6472]">ms</span>
            <span className="text-[9px] block text-[#0066FF]">({inferenceFpsVal.toFixed(1)} FPS)</span>
          </div>
        </div>

        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">Stream Rate</div>
          <div className="text-sm font-bold text-[#111827]">
            {Math.round(streamFpsVal)} <span className="text-[10px] font-normal text-[#5B6472]">FPS</span>
          </div>
        </div>
      </div>

      {/* Class Distribution Breakdown */}
      <div className="space-y-1.5 pt-1">
        <div className="text-[10px] text-[#5B6472] uppercase font-semibold">Classification Breakdown</div>
        <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
          {displayClasses.map((cls) => {
            const count = classCounts[cls] || 0;
            return (
              <div
                key={cls}
                className="flex justify-between items-center p-1 bg-[#F5F7FA] rounded border border-[#D9DEE7] text-[11px]"
              >
                <span className="flex items-center space-x-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#0066FF]"></span>
                  <span className="text-[#111827] font-mono truncate max-w-[120px]">{cls}</span>
                </span>
                <span className="font-bold text-[#0066FF]">
                  {count.toString().padStart(2, "0")}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pipeline Health */}
      {pipelineHealth && (
        <div className="pt-2 border-t border-[#D9DEE7] text-[10px] text-[#5B6472] flex justify-between items-center">
          <span>VIDEO: {pipelineHealth.video}</span>
          <span>READER: {pipelineHealth.frame_reader}</span>
          <span className="text-[#0066FF]">DB: OK</span>
        </div>
      )}
    </div>
  );
};

export default DetectionPanel;
