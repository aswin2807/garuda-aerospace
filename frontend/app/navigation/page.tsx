"use client";

import React, { useState } from "react";
import { TopBar } from "../../components/hud/TopBar";
import { Sidebar } from "../../components/hud/Sidebar";
import { AnalysisWorkspace } from "../../components/analysis/AnalysisWorkspace";
import { InteractiveNavigationMap } from "../../components/navigation/InteractiveNavigationMap";
import { DroneStatusPanel } from "../../components/navigation/DroneStatusPanel";
import { RoutePlanningPanel } from "../../components/navigation/RoutePlanningPanel";
import { NavigationGuidancePanel } from "../../components/navigation/NavigationGuidancePanel";

export default function NavigationPage() {
  const [activeTab, setActiveTab] = useState<"TACTICAL" | "INSPECTION">("TACTICAL");

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0A0F1D] overflow-hidden font-sans select-none text-slate-100">
      {/* Top Header */}
      <TopBar />

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentFocus="navigation" />

        <main className="flex-1 flex flex-col overflow-hidden bg-[#070B14]">
          {/* Sub-Header Navigation Mode Selector Bar */}
          <div className="h-12 bg-[#0F172A] border-b border-[#1E293B] px-6 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab("TACTICAL")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition ${
                  activeTab === "TACTICAL"
                    ? "bg-cyan-600 text-white shadow-md border border-cyan-400/40"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#1E293B]"
                }`}
              >
                <span>🧭</span>
                <span>TACTICAL NAVIGATION & ROUTE GUIDANCE</span>
              </button>

              <button
                onClick={() => setActiveTab("INSPECTION")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition ${
                  activeTab === "INSPECTION"
                    ? "bg-cyan-600 text-white shadow-md border border-cyan-400/40"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#1E293B]"
                }`}
              >
                <span>🔍</span>
                <span>OBSTACLE & NAV AI INSPECTION</span>
              </button>
            </div>

            <div className="text-[11px] text-slate-400 font-medium hidden md:flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>ROD Mission Control</span>
              </span>
              <span>·</span>
              <span>WGS 84 Geodesic Standards</span>
            </div>
          </div>

          {/* Tab 1: Tactical Route Planning & Interactive Map (PRD Core) */}
          {activeTab === "TACTICAL" ? (
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden p-3 gap-3">
              {/* Left / Center: Interactive Map */}
              <div className="flex-1 flex flex-col h-full min-h-[400px]">
                <InteractiveNavigationMap />
              </div>

              {/* Right: Mission Control & Route Planning Sidebar */}
              <div className="w-full md:w-[420px] lg:w-[460px] flex flex-col gap-3 h-full overflow-y-auto pr-1 shrink-0">
                {/* Drone Live Status Panel */}
                <DroneStatusPanel />

                {/* Active Waypoint Guidance HUD (Visible when guidance mode is engaged) */}
                <NavigationGuidancePanel />

                {/* Route Planning, Waypoints & Persistence Panel */}
                <RoutePlanningPanel />
              </div>
            </div>
          ) : (
            /* Tab 2: Existing Video / Media AI Obstacle Analysis Workspace (FR-09) */
            <div className="flex-1 flex flex-col overflow-hidden bg-[#F5F7FA]">
              <div className="bg-[#0F172A] border-b border-[#1E293B] px-6 py-2.5 text-xs text-slate-300 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  <span className="font-bold text-slate-100">Obstacle & Nav AI Model:</span>
                  <code className="text-cyan-300 bg-[#1E293B] px-1.5 py-0.5 rounded text-[11px]">
                    navigation_best.pt (80 Classes)
                  </code>
                  <span className="text-slate-400 text-[11px] hidden lg:inline">
                    · Identifies runway vehicles, aircraft, personnel & ground obstacles
                  </span>
                </div>
                <span className="text-[10px] text-amber-300 bg-amber-950/60 border border-amber-800/80 px-2 py-0.5 rounded font-mono">
                  2D Camera Detection (FR-09)
                </span>
              </div>
              <AnalysisWorkspace initialType="NAVIGATION" fixedType={true} />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
