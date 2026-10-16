"use client";

import React, { useEffect, useState } from "react";
import { useNavigationStore } from "../../stores/navigationStore";
import { DebrisTargetItem } from "../../lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function DebrisTargetSelectorModal({ isOpen, onClose }: Props) {
  const { debrisTargets, loadDebrisTargetsAction, setTarget } = useNavigationStore();
  const [loading, setLoading] = useState(false);
  const [filterNavigableOnly, setFilterNavigableOnly] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      loadDebrisTargetsAction().finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const displayedItems = filterNavigableOnly
    ? debrisTargets.filter((item) => item.is_navigable)
    : debrisTargets;

  const handleSelect = (item: DebrisTargetItem) => {
    if (!item.is_navigable || item.latitude == null || item.longitude == null) return;

    setTarget({
      latitude: item.latitude,
      longitude: item.longitude,
      name: `${item.class_name} (Debris #${item.id.slice(-6)})`,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-[#0F172A] border border-[#334155] rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1E293B] bg-[#1E293B]/50">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span>🎯</span>
              <span>Select Navigation Target from Detected Debris (ROD)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Query Foreign Object Debris (FOD) with verified or estimated geographic coordinates (FR-08)
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-lg p-1 transition"
          >
            ✕
          </button>
        </div>

        {/* Filter bar */}
        <div className="px-5 py-3 border-b border-[#1E293B] flex items-center justify-between bg-[#0A0F1D] text-xs">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={filterNavigableOnly}
              onChange={(e) => setFilterNavigableOnly(e.target.checked)}
              className="rounded bg-[#1E293B] border-[#334155] text-cyan-500 focus:ring-0"
            />
            <span className="text-slate-300">Show only navigable items with valid GPS</span>
          </label>
          <span className="text-slate-400">
            {displayedItems.length} records found
          </span>
        </div>

        {/* List Content */}
        <div className="p-4 flex-1 overflow-y-auto divide-y divide-[#1E293B] space-y-2">
          {loading ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-cyan-400 border-t-transparent mb-2" />
              <p>Querying debris database...</p>
            </div>
          ) : displayedItems.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              <p className="text-base font-medium text-slate-300 mb-1">No debris targets available</p>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                No foreign object debris with valid geodetic coordinates has been recorded yet. Perform a debris inspection run with drone GPS enabled first.
              </p>
            </div>
          ) : (
            displayedItems.map((item) => (
              <div
                key={item.id}
                className={`pt-2.5 pb-2.5 px-3 rounded-lg flex items-center justify-between transition ${
                  item.is_navigable
                    ? "bg-[#1E293B]/40 hover:bg-[#1E293B] border border-transparent hover:border-[#38BDF8]/40"
                    : "bg-[#1E293B]/20 opacity-60 border border-transparent"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-200 text-sm">
                      {item.class_name}
                    </span>
                    {item.confidence && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {Math.round(item.confidence * 100)}% conf
                      </span>
                    )}
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        item.status === "verified"
                          ? "bg-emerald-950/80 text-emerald-400 border border-emerald-700/60"
                          : item.status === "estimated"
                          ? "bg-amber-950/80 text-amber-400 border border-amber-700/60"
                          : "bg-slate-800 text-slate-400 border border-slate-700"
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>

                  <div className="text-xs font-mono text-slate-300 flex items-center gap-2">
                    {item.is_navigable ? (
                      <>
                        <span className="text-cyan-400">
                          {item.latitude?.toFixed(6)}° N, {item.longitude?.toFixed(6)}° E
                        </span>
                        {item.uncertainty_m && (
                          <span className="text-slate-400 text-[11px]">
                            (±{item.uncertainty_m}m)
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-amber-400/90 italic text-[11px]">
                        ⚠️ {item.navigable_reason || "Coordinates unavailable"}
                      </span>
                    )}
                  </div>

                  <div className="text-[11px] text-slate-400 flex items-center gap-3">
                    <span>Source: {item.source_module}</span>
                    {item.timestamp && (
                      <span>Time: {new Date(item.timestamp).toLocaleString()}</span>
                    )}
                  </div>
                </div>

                <div>
                  <button
                    disabled={!item.is_navigable}
                    onClick={() => handleSelect(item)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                      item.is_navigable
                        ? "bg-cyan-600 hover:bg-cyan-500 text-white shadow-md active:scale-95"
                        : "bg-slate-800 text-slate-500 cursor-not-allowed"
                    }`}
                  >
                    Set as Target
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#1E293B] bg-[#0A0F1D] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#1E293B] hover:bg-[#334155] text-slate-300 rounded-lg text-xs font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
