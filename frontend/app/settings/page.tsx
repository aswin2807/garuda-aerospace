"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Sidebar } from "../../components/hud/Sidebar";
import { TopBar } from "../../components/hud/TopBar";
import { checkBackendHealth } from "../../lib/api";

export default function SettingsPage() {
  const [health, setHealth] = useState<any>({ api: "checking...", database: "checking...", model: "checking..." });

  useEffect(() => {
    async function loadHealth() {
      const res = await checkBackendHealth();
      setHealth(res);
    }
    loadHealth();
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] text-[#111827] overflow-hidden font-mono select-none">
      <TopBar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-y-auto p-6 bg-[#F5F7FA]">
          <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-4 mb-6">
            <div>
              <h1 className="text-xl font-bold tracking-wider text-[#0066FF]">SYSTEM SETTINGS & HEALTH</h1>
              <p className="text-xs text-[#5B6472]">Service connectivity and platform configurations</p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] rounded text-xs font-medium transition-colors"
            >
              ← Return to Mission Control HUD
            </Link>
          </div>

          <div className="max-w-2xl space-y-6">
            {/* Service Health Card */}
            <div className="p-5 bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg space-y-4 shadow-sm">
              <h2 className="text-sm font-bold text-[#111827] uppercase tracking-wider">Service Health Status</h2>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
                  <div className="text-[#5B6472] uppercase text-[10px]">FastAPI</div>
                  <div className="font-bold text-[#0066FF] mt-1 uppercase">{health.api}</div>
                </div>
                <div className="p-3 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
                  <div className="text-[#5B6472] uppercase text-[10px]">Database</div>
                  <div className="font-bold text-[#0066FF] mt-1 uppercase">{health.database}</div>
                </div>
                <div className="p-3 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
                  <div className="text-[#5B6472] uppercase text-[10px]">YOLOv11 Model</div>
                  <div className="font-bold text-[#0066FF] mt-1 uppercase">{health.model}</div>
                </div>
              </div>
            </div>

            {/* Endpoints Configuration */}
            <div className="p-5 bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg space-y-4 text-xs shadow-sm">
              <h2 className="text-sm font-bold text-[#111827] uppercase tracking-wider">API & WebSocket URLs</h2>
              <div className="space-y-3">
                <div>
                  <label className="block text-[#5B6472] mb-1 font-semibold uppercase text-[10px]">Backend REST API</label>
                  <input
                    type="text"
                    readOnly
                    value={process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
                    className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-[#111827] font-mono text-xs focus:border-[#0066FF] outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[#5B6472] mb-1 font-semibold uppercase text-[10px]">Detection WebSocket URL</label>
                  <input
                    type="text"
                    readOnly
                    value={process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"}
                    className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-[#111827] font-mono text-xs focus:border-[#0066FF] outline-none"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
