"use client";

import React, { useState, useMemo } from "react";
import { RunwayLightSlot, RunwayFaultItem } from "../../types/detection";

interface RunwayGridMatrixProps {
  matrix?: RunwayLightSlot[];
  faults?: RunwayFaultItem[];
  totalLights?: number;
  lightsOn?: number;
  lightsOff?: number;
  lightsUnknown?: number;
  confirmedFaults?: number;
  rowsDetected?: number;
}

export const RunwayGridMatrix: React.FC<RunwayGridMatrixProps> = ({
  matrix = [],
  faults = [],
  totalLights,
  lightsOn,
  lightsOff,
  lightsUnknown,
  confirmedFaults,
  rowsDetected,
}) => {
  const [filter, setFilter] = useState<"ALL" | "FAULTS" | "ON" | "OFF">("ALL");
  const [selectedSlot, setSelectedSlot] = useState<RunwayLightSlot | null>(null);

  // Group slots by row
  const rowsMap = useMemo(() => {
    const map = new Map<number, RunwayLightSlot[]>();
    for (const slot of matrix) {
      const r = slot.row_id || 1;
      if (!map.has(r)) map.set(r, []);
      map.get(r)!.push(slot);
    }
    // Sort columns within each row
    map.forEach((slots) => {
      slots.sort((a, b) => a.column_id - b.column_id);
    });
    return map;
  }, [matrix]);

  const sortedRowKeys = useMemo(() => {
    const keys: number[] = [];
    rowsMap.forEach((_, k) => {
      keys.push(k);
    });
    return keys.sort((a, b) => a - b);
  }, [rowsMap]);

  // Derived counts
  const calcTotal = totalLights ?? matrix.length;
  const calcOn = lightsOn ?? matrix.filter((s) => s.status === "ON").length;
  const calcOff = lightsOff ?? matrix.filter((s) => s.status === "OFF").length;
  const calcFaults = confirmedFaults ?? faults.length ?? matrix.filter((s) => s.is_confirmed && s.status === "OFF").length;
  const calcRows = rowsDetected ?? sortedRowKeys.length;

  const filteredSlots = useMemo(() => {
    if (filter === "ALL") return matrix;
    if (filter === "FAULTS") return matrix.filter((s) => s.is_confirmed || s.status === "OFF");
    if (filter === "ON") return matrix.filter((s) => s.status === "ON");
    if (filter === "OFF") return matrix.filter((s) => s.status === "OFF");
    return matrix;
  }, [matrix, filter]);

  if (matrix.length === 0) {
    return (
      <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-5 font-mono shadow-sm">
        <div className="flex items-center space-x-2 border-b border-[#D9DEE7] pb-3 mb-4">
          <div className="w-2.5 h-2.5 rounded-full bg-[#0066FF]" />
          <h4 className="text-xs font-bold text-[#111827] tracking-wider uppercase">
            RUNWAY LIGHT ROW & COLUMN GRID MATRIX
          </h4>
        </div>
        <div className="p-8 text-center text-[#5B6472] text-xs">
          Awaiting runway grid detection data. The matrix will render once runway lights are identified and tracked.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-5 font-mono shadow-sm flex flex-col space-y-4">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#D9DEE7] pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-3 h-3 rounded-full bg-[#0066FF] shadow-sm shadow-[#0066FF]/30" />
          <div>
            <h4 className="text-xs font-bold text-[#111827] tracking-wider uppercase">
              RUNWAY LIGHT ROW & COLUMN GRID MATRIX
            </h4>
            <p className="text-[10px] text-[#5B6472]">
              Persistent Slot Assignment (R#-C#) • Multi-Frame Validation (5 frames) • Deduplicated Physical Count
            </p>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center space-x-1.5 text-[11px] bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-1">
          {(["ALL", "FAULTS", "ON", "OFF"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-2.5 py-1 rounded font-semibold transition-colors ${
                filter === tab
                  ? "bg-[#0066FF] text-white shadow-xs"
                  : "text-[#5B6472] hover:text-[#111827] hover:bg-[#EAF3FF]"
              }`}
            >
              {tab === "ALL" && `ALL (${matrix.length})`}
              {tab === "FAULTS" && `FAULTS (${calcFaults})`}
              {tab === "ON" && `ON (${calcOn})`}
              {tab === "OFF" && `OFF (${calcOff})`}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Summary Header Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 text-center">
          <span className="text-[9px] uppercase tracking-wider text-[#5B6472]">TOTAL LIGHTS</span>
          <div className="text-base font-extrabold text-[#111827] mt-0.5">{calcTotal}</div>
          <span className="text-[9px] text-[#0066FF] font-semibold">100% Unique</span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 text-center">
          <span className="text-[9px] uppercase tracking-wider text-[#5B6472]">LIGHTS ACTIVE (ON)</span>
          <div className="text-base font-extrabold text-[#0066FF] mt-0.5">{calcOn}</div>
          <span className="text-[9px] text-emerald-600 font-semibold">Operational</span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 text-center">
          <span className="text-[9px] uppercase tracking-wider text-[#5B6472]">LIGHTS INACTIVE (OFF)</span>
          <div className="text-base font-extrabold text-red-600 mt-0.5">{calcOff}</div>
          <span className="text-[9px] text-red-600 font-semibold">Inactive</span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 text-center">
          <span className="text-[9px] uppercase tracking-wider text-[#5B6472]">OPERATIONAL RATE</span>
          <div className="text-base font-extrabold text-emerald-600 mt-0.5">
            {calcTotal > 0 ? `${Math.round((calcOn / calcTotal) * 100)}%` : "100%"}
          </div>
          <span className="text-[9px] text-emerald-600 font-semibold">Array Health</span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 text-center">
          <span className="text-[9px] uppercase tracking-wider text-[#5B6472]">CONFIRMED FAULTS</span>
          <div className="text-base font-extrabold text-red-600 mt-0.5 flex items-center justify-center space-x-1">
            <span>{calcFaults}</span>
            {calcFaults > 0 && <span className="w-2 h-2 rounded-full bg-red-600 animate-ping inline-block" />}
          </div>
          <span className="text-[9px] text-red-600 font-semibold">Verified ≥5 F</span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 text-center">
          <span className="text-[9px] uppercase tracking-wider text-[#5B6472]">GRID ROWS</span>
          <div className="text-base font-extrabold text-[#111827] mt-0.5">{calcRows}</div>
          <span className="text-[9px] text-[#0066FF] font-semibold">Runway Array</span>
        </div>
      </div>

      {/* Row-by-Row Visual Slot Matrix */}
      <div className="flex flex-col space-y-3 pt-2">
        {sortedRowKeys.map((rowNum) => {
          const rowSlots = rowsMap.get(rowNum) || [];
          const visibleSlots = rowSlots.filter((s) => filteredSlots.includes(s));

          if (visibleSlots.length === 0 && filter !== "ALL") return null;

          return (
            <div key={rowNum} className="border border-[#D9DEE7] rounded-lg p-3 bg-[#FAFAFA]">
              {/* Row Label */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded bg-[#0066FF] text-white text-[10px] font-bold">
                    ROW {rowNum}
                  </span>
                  <span className="text-[11px] text-[#5B6472]">
                    Total: {rowSlots.length} • ON: {rowSlots.filter((s) => s.status === "ON").length} • OFF: {rowSlots.filter((s) => s.status === "OFF").length}
                    {rowSlots.some((s) => s.is_confirmed || (s.status === "OFF" && (s.consecutive_off ?? 0) >= 5)) && (
                      <span className="text-red-600 font-semibold ml-1">
                        • {rowSlots.filter((s) => s.is_confirmed || (s.status === "OFF" && (s.consecutive_off ?? 0) >= 5)).length} FAULT(S)
                      </span>
                    )}
                  </span>
                </div>
              </div>

              {/* Slot Cards in this Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
                {visibleSlots.map((slot) => {
                  const isFault = slot.is_confirmed || (slot.status === "OFF" && (slot.consecutive_off ?? 0) >= 5);
                  const isOff = slot.status === "OFF";
                  const isOn = slot.status === "ON";
                  const isUnk = slot.status === "UNKNOWN";

                  let cardBorder = "border-[#D9DEE7]";
                  let badgeBg = "bg-gray-100 text-gray-700";

                  if (isFault) {
                    cardBorder = "border-red-500 bg-red-50/50 ring-1 ring-red-400";
                    badgeBg = "bg-red-100 text-red-800 font-bold";
                  } else if (isOff) {
                    cardBorder = "border-red-300 bg-red-50/20";
                    badgeBg = "bg-red-50 text-red-700 font-semibold";
                  } else if (isOn) {
                    cardBorder = "border-emerald-300 bg-emerald-50/20";
                    badgeBg = "bg-emerald-50 text-emerald-700 font-semibold";
                  } else if (isUnk) {
                    cardBorder = "border-amber-300 bg-amber-50/20";
                    badgeBg = "bg-amber-50 text-amber-700 font-semibold";
                  }

                  return (
                    <div
                      key={slot.light_id}
                      onClick={() => setSelectedSlot(slot)}
                      className={`cursor-pointer rounded-lg p-2.5 border transition-all hover:scale-[1.02] hover:shadow-xs flex flex-col justify-between ${cardBorder}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#111827]">{slot.light_id}</span>
                        {isFault && (
                          <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" title="Confirmed Fault" />
                        )}
                      </div>

                      <div className="mt-1.5 flex items-center justify-between">
                        <span className={`text-[9px] px-1.5 py-0.5 rounded border border-transparent ${badgeBg}`}>
                          {slot.status}
                        </span>
                        <span className="text-[9px] text-[#5B6472]">
                          {(slot.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <div className="mt-1 flex items-center justify-between text-[8px] text-[#5B6472]">
                        <span>Col {slot.column_id}</span>
                        {slot.track_id && <span>#{slot.track_id}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Slot Detail Modal */}
      {selectedSlot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-[#D9DEE7] rounded-xl p-5 max-w-md w-full shadow-xl font-mono">
            <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-3 mb-3">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-[#0066FF]" />
                <h5 className="font-bold text-sm text-[#111827]">
                  LIGHT SLOT INSPECTION: {selectedSlot.light_id}
                </h5>
              </div>
              <button
                onClick={() => setSelectedSlot(null)}
                className="text-[#5B6472] hover:text-[#111827] text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">Slot Identity:</span>
                <span className="font-bold text-[#111827]">{selectedSlot.light_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">Grid Location:</span>
                <span className="font-bold text-[#111827]">Row {selectedSlot.row_id}, Column {selectedSlot.column_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">Current Status:</span>
                <span className={`font-bold ${selectedSlot.status === "ON" ? "text-emerald-600" : selectedSlot.status === "OFF" ? "text-red-600" : "text-amber-600"}`}>
                  {selectedSlot.status}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">Confirmed Fault:</span>
                <span className="font-bold text-[#111827]">{selectedSlot.is_confirmed ? "YES (≥5 Frames Verified)" : "NO"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">Confidence:</span>
                <span className="font-bold text-[#111827]">{(selectedSlot.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">ByteTrack ID:</span>
                <span className="font-bold text-[#111827]">{selectedSlot.track_id ? `#${selectedSlot.track_id}` : "N/A"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">Consecutive OFF Observations:</span>
                <span className="font-bold text-[#111827]">{selectedSlot.consecutive_off ?? 0}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-[#5B6472]">Total Observations:</span>
                <span className="font-bold text-[#111827]">{selectedSlot.total_observations ?? 1}</span>
              </div>
              {selectedSlot.bbox && (
                <div className="flex justify-between py-1 border-b border-gray-100">
                  <span className="text-[#5B6472]">Bounding Box [x1, y1, x2, y2]:</span>
                  <span className="font-mono text-[11px] text-[#111827]">
                    [{selectedSlot.bbox.join(", ")}]
                  </span>
                </div>
              )}
            </div>

            <button
              onClick={() => setSelectedSlot(null)}
              className="mt-4 w-full py-2 bg-[#0066FF] hover:bg-[#008CFF] text-white rounded-lg text-xs font-bold transition-colors"
            >
              CLOSE INSPECTION
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
