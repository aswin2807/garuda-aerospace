"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Sidebar } from "../../components/hud/Sidebar";
import { TopBar } from "../../components/hud/TopBar";
import { getDetectionHistory } from "../../lib/api";

export default function DetectionsHistoryPage() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [classFilter, setClassFilter] = useState<string>("ALL");
  const [minConfFilter, setMinConfFilter] = useState<number>(0.5);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const data = await getDetectionHistory({ minConfidence: minConfFilter });
        setHistory(data);
      } catch (err) {
        console.error("Failed to load history:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [minConfFilter]);

  const filteredHistory = history.filter((item) => {
    if (classFilter !== "ALL" && item.class_name.toUpperCase() !== classFilter) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] text-[#111827] overflow-hidden font-mono select-none">
      <TopBar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-y-auto p-6 bg-[#F5F7FA]">
          {/* Top Navigation */}
          <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-4 mb-6">
            <div>
              <h1 className="text-xl font-bold tracking-wider text-[#0066FF]">
                DETECTION AUDIT & HISTORY
              </h1>
              <p className="text-xs text-[#5B6472]">Historical YOLOv11 beacon detection records</p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] rounded text-xs font-medium transition-colors"
            >
              ← Return to Mission Control HUD
            </Link>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center space-x-6 bg-[#FFFFFF] p-4 border border-[#D9DEE7] rounded-lg mb-6 text-xs">
            <div>
              <label className="block text-[#5B6472] mb-1 font-semibold uppercase text-[10px]">Class Filter</label>
              <select
                value={classFilter}
                onChange={(e) => setClassFilter(e.target.value)}
                className="bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-1.5 text-[#111827] focus:border-[#0066FF] outline-none"
              >
                <option value="ALL">All Classes</option>
                <option value="ON">ON (Active Beacon)</option>
                <option value="OFF">OFF (Dark Beacon)</option>
              </select>
            </div>

            <div>
              <label className="block text-[#5B6472] mb-1 font-semibold uppercase text-[10px]">Min Confidence ({Math.round(minConfFilter * 100)}%)</label>
              <input
                type="range"
                min="0.1"
                max="0.95"
                step="0.05"
                value={minConfFilter}
                onChange={(e) => setMinConfFilter(parseFloat(e.target.value))}
                className="accent-[#0066FF]"
              />
            </div>
          </div>

          {/* Table */}
          <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F5F7FA] text-[#5B6472] border-b border-[#D9DEE7]">
                <tr>
                  <th className="p-3">Time</th>
                  <th className="p-3">Object / Class</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Coordinates (X, Y, W, H)</th>
                  <th className="p-3">Drone ID</th>
                  <th className="p-3">Mission ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#D9DEE7] text-[#111827]">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-[#5B6472]">
                      Loading detection records...
                    </td>
                  </tr>
                ) : filteredHistory.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-[#5B6472]">
                      No detection records matching current criteria.
                    </td>
                  </tr>
                ) : (
                  filteredHistory.map((item) => (
                    <tr key={item.id} className="hover:bg-[#F0F6FF] transition-colors">
                      <td className="p-3 text-[#5B6472]">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            item.class_name.toLowerCase() === "on"
                              ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30"
                              : "bg-[#F5F7FA] text-[#5B6472] border-[#D9DEE7]"
                          }`}
                        >
                          {item.class_name.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-3 font-semibold text-[#0066FF]">
                        {Math.round(item.confidence * 100)}%
                      </td>
                      <td className="p-3 text-[#5B6472]">
                        [{item.x.toFixed(0)}, {item.y.toFixed(0)}, {item.width.toFixed(0)}, {item.height.toFixed(0)}]
                      </td>
                      <td className="p-3 text-[#0066FF] font-medium">{item.drone_id || "DR-01"}</td>
                      <td className="p-3 text-[#111827]">{item.mission_id || "M001"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
