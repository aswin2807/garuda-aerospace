"use client";

import React from "react";
import { TopBar } from "../../components/hud/TopBar";
import { Sidebar } from "../../components/hud/Sidebar";
import { AnalysisWorkspace } from "../../components/analysis/AnalysisWorkspace";

/**
 * OfflineSurveillancePage — Dedicated Offline Surveillance Module
 * Provides genuine AI model analysis for uploaded videos and images:
 * - Model Selector: Navigation, FOD Debris, Runway Light
 * - Media preview before and during analysis
 * - Live progress tracking with dynamic ETA & processing FPS
 * - Post-analysis annotated output with bounding boxes & counters
 * - Exportable audit records & reports
 */
export default function OfflineSurveillancePage() {
  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      {/* Top Header with Garuda Aerospace Command Centre branding */}
      <TopBar />

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-hidden bg-[#F5F7FA]">
          <div className="px-6 py-2.5 bg-[#FFFFFF] border-b border-[#D9DEE7] flex items-center justify-between font-mono text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#0066FF]" />
              <span className="font-bold text-[#111827] uppercase tracking-wider text-sm">
                Offline Surveillance & Media Analysis
              </span>
              <span className="text-[10px] text-[#5B6472] px-2 py-0.5 rounded bg-[#F0F6FF] border border-[#D9DEE7]">
                SECURE LOCAL INFERENCE ENGINE
              </span>
            </div>
            <div className="text-[11px] text-[#5B6472]">
              MODELS: NAVIGATION • FOD DEBRIS • RUNWAY LIGHT
            </div>
          </div>
          <AnalysisWorkspace initialType="NAVIGATION" fixedType={false} />
        </main>
      </div>
    </div>
  );
}
