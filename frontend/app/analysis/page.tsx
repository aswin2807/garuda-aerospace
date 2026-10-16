"use client";

import React from "react";
import { TopBar } from "../../components/hud/TopBar";
import { Sidebar } from "../../components/hud/Sidebar";
import { AnalysisWorkspace } from "../../components/analysis/AnalysisWorkspace";

/**
 * AnalysisPage — Dedicated offline AI media analysis workspace
 * Supports:
 * - Module switching: Navigation, FOD Debris, Runway Light
 * - Media upload: Video & Static Image
 * - Frame-by-frame genuine YOLO inference
 * - Dynamic ETA & speed metrics
 * - Exportable audit reports (CSV / JSON)
 */
export default function AnalysisPage() {
  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      {/* Top Header with Garuda Aerospace branding */}
      <TopBar />

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-hidden bg-[#F5F7FA]">
          <AnalysisWorkspace initialType="NAVIGATION" fixedType={false} />
        </main>
      </div>
    </div>
  );
}
