"use client";

import React from "react";
import { useNavigationStore } from "../../stores/navigationStore";

export function NavigationGuidancePanel() {
  const {
    navigationMode,
    setNavigationMode,
    guidance,
    target,
    waypoints,
    activeWaypointIndex,
    setActiveWaypointIndex,
    advanceWaypoint,
    telemetry,
  } = useNavigationStore();

  if (navigationMode === "PLANNING") {
    return null;
  }

  const isLive = navigationMode === "LIVE_GUIDANCE";
  const isPreview = navigationMode === "PREVIEW";

  // Determine active waypoint / node
  let activeNodeName = "Target Destination";
  const totalNodes = waypoints.length + 1; // waypoints + target
  const currentNodeIndex = activeWaypointIndex + 1;

  if (activeWaypointIndex < waypoints.length) {
    const wp = waypoints[activeWaypointIndex];
    activeNodeName = `Waypoint #${wp.order} (${wp.altitude_agl_m || 30}m AGL)`;
  } else if (target) {
    activeNodeName = target.name || "Target Destination";
  }

  const isArrived = guidance?.is_arrived ?? false;
  const isApproaching = guidance?.arrival_status === "APPROACHING";

  return (
    <div
      className={`border-2 rounded-xl p-4 shadow-xl text-slate-100 flex flex-col gap-3 transition-colors ${
        isLive
          ? "bg-[#0A0F1D] border-emerald-500/80"
          : "bg-[#0F1424] border-amber-500/70"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1E293B] pb-2.5">
        <div className="flex items-center gap-2">
          <span
            className={`w-3 h-3 rounded-full ${
              isLive ? "bg-emerald-400 animate-ping" : "bg-amber-400"
            }`}
          />
          <div>
            <h3
              className={`text-sm font-bold tracking-wide uppercase ${
                isLive ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {isLive ? "Active Live Guidance Mode" : "Guidance Preview Mode (FR-11)"}
            </h3>
            <p className="text-[11px] text-slate-400">
              {isLive
                ? "Live bearing, steering turn instructions, and waypoint arrival tracking"
                : "Course preview and waypoint sequence — no flight commands transmitted"}
            </p>
          </div>
        </div>

        <button
          onClick={() => setNavigationMode("PLANNING")}
          className="px-2.5 py-1 bg-[#1E293B] hover:bg-[#334155] text-slate-300 rounded text-xs font-semibold transition border border-[#334155]"
        >
          Exit to Planning
        </button>
      </div>

      {/* Target Progress Bar */}
      <div className="bg-[#0A0F1D] p-2.5 rounded-lg border border-[#1E293B] flex items-center justify-between text-xs">
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-semibold block">
            Steering Toward
          </span>
          <span className="font-bold text-slate-100 text-sm">{activeNodeName}</span>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-slate-400 uppercase font-semibold block">
            Sequence Progress
          </span>
          <span
            className={`font-mono font-bold ${
              isLive ? "text-emerald-400" : "text-amber-400"
            }`}
          >
            {currentNodeIndex} of {totalNodes}
          </span>
        </div>
      </div>

      {/* Primary Guidance HUD Metric Card */}
      <div className="bg-[#0A0F1D] p-4 rounded-xl border border-[#1E293B] flex flex-col items-center gap-3">
        {/* Tactical Compass / Steering Needles */}
        <div className="relative w-36 h-36 rounded-full border-2 border-dashed border-[#334155] flex items-center justify-center bg-[#050811] shadow-inner">
          {/* Compass cardinal ticks */}
          <span className="absolute top-1 text-[10px] font-bold text-slate-400">N</span>
          <span className="absolute bottom-1 text-[10px] font-bold text-slate-400">S</span>
          <span className="absolute left-2 text-[10px] font-bold text-slate-400">W</span>
          <span className="absolute right-2 text-[10px] font-bold text-slate-400">E</span>

          {/* Drone heading pointer if telemetry available */}
          {telemetry?.heading != null && (
            <div
              className="absolute w-full h-full flex items-center justify-center transition-transform duration-500"
              style={{ transform: `rotate(${telemetry.heading}deg)` }}
            >
              <div className="w-1 h-14 bg-slate-500/60 -translate-y-5 rounded-full" />
            </div>
          )}

          {/* Target bearing needle */}
          {guidance?.bearing_to_target_deg != null && (
            <div
              className="absolute w-full h-full flex items-center justify-center transition-transform duration-500"
              style={{ transform: `rotate(${guidance.bearing_to_target_deg}deg)` }}
            >
              <div
                className={`w-1.5 h-14 -translate-y-6 rounded-full ${
                  isLive
                    ? "bg-emerald-400 shadow-[0_0_8px_#10B981]"
                    : "bg-amber-400 shadow-[0_0_8px_#F59E0B]"
                }`}
              />
            </div>
          )}

          {/* Center readout */}
          <div className="text-center z-10">
            <span
              className={`text-lg font-mono font-bold block ${
                isLive ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {guidance?.bearing_to_target_deg != null
                ? `${guidance.bearing_to_target_deg.toFixed(0)}°`
                : "--°"}
            </span>
            <span className="text-[10px] font-bold text-slate-300">
              {guidance?.compass_direction || "--"}
            </span>
          </div>
        </div>

        {/* Big Steering Instruction */}
        <div className="w-full text-center">
          <span
            className={`inline-block px-4 py-1.5 rounded-lg text-sm font-bold tracking-wide uppercase shadow-sm ${
              isArrived
                ? "bg-emerald-500 text-slate-950 animate-bounce"
                : isApproaching
                ? "bg-amber-500 text-slate-950"
                : isLive
                ? "bg-[#1E293B] text-emerald-300 border border-emerald-800"
                : "bg-[#1E293B] text-amber-300 border border-amber-800"
            }`}
          >
            {guidance?.steering_instruction || "Acquiring course..."}
          </span>
        </div>

        {/* Distance Remaining & Relative Turn Angle */}
        <div className="grid grid-cols-2 gap-2 w-full text-xs mt-1">
          <div className="bg-[#1E293B]/70 p-2 rounded border border-[#334155] text-center">
            <span className="text-[10px] text-slate-400 block font-semibold">
              Distance to Target
            </span>
            <span className="font-mono text-sm font-bold text-slate-100">
              {guidance?.distance_to_target_m != null
                ? guidance.distance_to_target_m >= 1000
                  ? `${(guidance.distance_to_target_m / 1000).toFixed(2)} km`
                  : `${guidance.distance_to_target_m.toFixed(1)} m`
                : "-- m"}
            </span>
          </div>

          <div className="bg-[#1E293B]/70 p-2 rounded border border-[#334155] text-center">
            <span className="text-[10px] text-slate-400 block font-semibold">
              Relative Turn Angle
            </span>
            <span className="font-mono text-sm font-bold text-cyan-400">
              {guidance?.relative_bearing_deg != null
                ? `${guidance.relative_bearing_deg > 0 ? "+" : ""}${guidance.relative_bearing_deg}°`
                : "--°"}
            </span>
          </div>
        </div>

        {/* Next Waypoint Advance Control */}
        <div className="w-full pt-1">
          <button
            onClick={advanceWaypoint}
            disabled={activeWaypointIndex >= waypoints.length}
            className="w-full py-1.5 bg-[#1E293B] hover:bg-[#334155] disabled:opacity-40 text-slate-300 rounded font-semibold text-xs border border-[#334155] transition flex items-center justify-center gap-1.5"
          >
            <span>⏭ Skip / Advance to Next Waypoint</span>
          </button>
        </div>
      </div>
    </div>
  );
}
