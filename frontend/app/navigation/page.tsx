"use client";

import React from "react";
import { TopBar } from "../../components/hud/TopBar";
import { Sidebar } from "../../components/hud/Sidebar";
import { AnalysisWorkspace } from "../../components/analysis/AnalysisWorkspace";

export default function NavigationPage() {
  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      {/* Top Header */}
      <TopBar />

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentFocus="navigation" />
        <main className="flex-1 flex flex-col overflow-hidden bg-[#F5F7FA]">
          <AnalysisWorkspace initialType="NAVIGATION" fixedType={true} />
        </main>
      </div>
    </div>
  );
}
