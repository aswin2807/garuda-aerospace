"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Sidebar } from "../../components/hud/Sidebar";
import { TopBar } from "../../components/hud/TopBar";
import { getMissions } from "../../lib/api";

export default function MissionsPage() {
  const [missions, setMissions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadMissions() {
      try {
        const data = await getMissions();
        setMissions(data);
      } catch (err) {
        console.error("Failed to fetch missions:", err);
      } finally {
        setLoading(false);
      }
    }
    loadMissions();
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] text-[#111827] overflow-hidden font-mono select-none">
      <TopBar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-y-auto p-6 bg-[#F5F7FA]">
          {/* Top Header */}
          <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-4 mb-6">
            <div>
              <h1 className="text-xl font-bold tracking-wider text-[#0066FF]">
                MISSION MANAGEMENT & PLANNING
              </h1>
              <p className="text-xs text-[#5B6472]">Autonomous flight missions and survey waypoints</p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] rounded text-xs font-medium transition-colors"
            >
              ← Return to Mission Control HUD
            </Link>
          </div>

          {/* Mission Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {loading ? (
              <div className="col-span-3 text-center text-[#5B6472] py-12">Loading missions...</div>
            ) : missions.length === 0 ? (
              <div className="col-span-3 text-center text-[#5B6472] py-12">No active missions found.</div>
            ) : (
              missions.map((m) => (
                <div
                  key={m.id}
                  className="p-5 bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg flex flex-col justify-between space-y-4 hover:border-[#0066FF] hover:shadow-md transition-all"
                >
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold text-sm text-[#111827]">{m.name}</h3>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30">
                        {m.status}
                      </span>
                    </div>
                    <p className="text-xs text-[#5B6472] leading-relaxed">{m.description || "No description provided."}</p>
                  </div>

                  <div className="pt-3 border-t border-[#D9DEE7] flex justify-between items-center text-xs">
                    <span className="text-[#5B6472]">ID: {m.id.slice(0, 8)}...</span>
                    <div className="flex space-x-2">
                      <button className="px-3 py-1 bg-[#0066FF] hover:bg-[#008CFF] text-[#FFFFFF] rounded text-xs font-semibold shadow-sm transition-all">
                        Execute
                      </button>
                      <button className="px-3 py-1 bg-[#F5F7FA] hover:bg-[#F0F6FF] text-[#5B6472] hover:text-[#111827] border border-[#D9DEE7] rounded text-xs transition-all">
                        Details
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
