"use client";

import React, { useState, useEffect } from "react";
import { useNavigationStore, NavigationMode } from "../../stores/navigationStore";
import { DebrisTargetSelectorModal } from "./DebrisTargetSelectorModal";

export function RoutePlanningPanel() {
  const {
    target,
    setTarget,
    waypoints,
    addWaypoint,
    updateWaypoint,
    removeWaypoint,
    reorderWaypoint,
    editingWaypointOrder,
    setEditingWaypointOrder,
    clearWaypoints,
    clearAllRoute,
    cruiseSpeedMps,
    setCruiseSpeed,
    speedSource,
    setSpeedSource,
    operationalLimitM,
    setOperationalLimit,
    calculatedRoute,
    calculateRouteAction,
    saveRouteAction,
    loadSavedRoutesAction,
    savedRoutes,
    loadRouteById,
    deleteRouteAction,
    isLoadingRoute,
    isSavingRoute,
    errorMessage,
    navigationMode,
    setNavigationMode,
    telemetry,
  } = useNavigationStore();

  // Target Form states
  const [targetLat, setTargetLat] = useState("");
  const [targetLon, setTargetLon] = useState("");
  const [targetName, setTargetName] = useState("");
  const [targetError, setTargetError] = useState<string | null>(null);

  // Waypoint Form states
  const [wpLat, setWpLat] = useState("");
  const [wpLon, setWpLon] = useState("");
  const [wpAlt, setWpAlt] = useState("30");
  const [wpError, setWpError] = useState<string | null>(null);

  // Edit Waypoint states
  const [editLat, setEditLat] = useState("");
  const [editLon, setEditLon] = useState("");
  const [editAlt, setEditAlt] = useState("");

  // Modals & Drawers
  const [saveName, setSaveName] = useState("");
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showSavedList, setShowSavedList] = useState(false);
  const [showDebrisModal, setShowDebrisModal] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showLimitSettings, setShowLimitSettings] = useState(false);
  const [tempLimitKm, setTempLimitKm] = useState("3.0");

  // Sync target form when store target updates
  useEffect(() => {
    if (target) {
      setTargetLat(target.latitude.toFixed(6));
      setTargetLon(target.longitude.toFixed(6));
      setTargetName(target.name || "Target Destination");
      setTargetError(null);
    }
  }, [target]);

  // Load saved routes on mount
  useEffect(() => {
    loadSavedRoutesAction();
  }, [loadSavedRoutesAction]);

  useEffect(() => {
    if (operationalLimitM) {
      setTempLimitKm((operationalLimitM / 1000.0).toFixed(1));
    }
  }, [operationalLimitM]);

  // Target submission with strict validation (FR-03)
  const handleApplyTarget = (e: React.FormEvent) => {
    e.preventDefault();
    setTargetError(null);

    const lat = parseFloat(targetLat);
    const lon = parseFloat(targetLon);

    if (isNaN(lat) || lat < -90 || lat > 90) {
      setTargetError("Latitude must be a valid number between -90.0° and +90.0°");
      return;
    }
    if (isNaN(lon) || lon < -180 || lon > 180) {
      setTargetError("Longitude must be a valid number between -180.0° and +180.0°");
      return;
    }

    setTarget({
      latitude: Number(lat.toFixed(7)),
      longitude: Number(lon.toFixed(7)),
      name: targetName.trim() || `Target (${lat.toFixed(4)}°, ${lon.toFixed(4)}°)`,
    });
  };

  // Waypoint submission with strict validation (FR-04)
  const handleAddWaypoint = (e: React.FormEvent) => {
    e.preventDefault();
    setWpError(null);

    const lat = parseFloat(wpLat);
    const lon = parseFloat(wpLon);
    const alt = parseFloat(wpAlt) || 30.0;

    if (isNaN(lat) || lat < -90 || lat > 90) {
      setWpError("Latitude must be between -90.0° and +90.0°");
      return;
    }
    if (isNaN(lon) || lon < -180 || lon > 180) {
      setWpError("Longitude must be between -180.0° and +180.0°");
      return;
    }
    if (alt < 0 || alt > 500) {
      setWpError("Altitude AGL must be between 0m and 500m");
      return;
    }

    addWaypoint({
      latitude: Number(lat.toFixed(7)),
      longitude: Number(lon.toFixed(7)),
      altitude_agl_m: alt,
    });

    setWpLat("");
    setWpLon("");
  };

  // Start editing a waypoint
  const startEditingWaypoint = (order: number) => {
    const wp = waypoints.find((w) => w.order === order);
    if (!wp) return;
    setEditingWaypointOrder(order);
    setEditLat(wp.latitude.toFixed(6));
    setEditLon(wp.longitude.toFixed(6));
    setEditAlt(String(wp.altitude_agl_m || 30));
  };

  // Save edited waypoint
  const handleSaveEditWaypoint = (order: number) => {
    const lat = parseFloat(editLat);
    const lon = parseFloat(editLon);
    const alt = parseFloat(editAlt) || 30.0;

    if (isNaN(lat) || lat < -90 || lat > 90 || isNaN(lon) || lon < -180 || lon > 180) {
      alert("Invalid coordinates for waypoint");
      return;
    }

    updateWaypoint(order, {
      latitude: lat,
      longitude: lon,
      altitude_agl_m: alt,
    });
  };

  const handleSaveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!saveName.trim()) return;
    const ok = await saveRouteAction(saveName.trim());
    if (ok) {
      setShowSaveModal(false);
      setSaveName("");
    }
  };

  const handleApplyOperationalLimit = (e: React.FormEvent) => {
    e.preventDefault();
    const km = parseFloat(tempLimitKm);
    if (!isNaN(km) && km >= 0.5 && km <= 50.0) {
      setOperationalLimit(km * 1000.0);
      setShowLimitSettings(false);
    }
  };

  const isDroneLiveAndReady =
    telemetry?.connected && !telemetry?.is_stale && telemetry?.has_gps_fix;

  return (
    <div className="bg-[#0F172A] border border-[#1E293B] rounded-xl p-4 shadow-md text-slate-100 flex flex-col gap-4 text-xs">
      {/* Navigation Mode Selector (FR-11: Planning vs Preview vs Live Guidance) */}
      <div className="bg-[#070B14] p-1.5 rounded-lg border border-[#1E293B] flex items-center justify-between">
        <span className="text-[10px] text-slate-400 uppercase font-bold pl-1.5">
          Mode (FR-11):
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => setNavigationMode("PLANNING")}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition ${
              navigationMode === "PLANNING"
                ? "bg-cyan-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Planning
          </button>
          <button
            onClick={() => setNavigationMode("PREVIEW")}
            disabled={!calculatedRoute}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition disabled:opacity-40 ${
              navigationMode === "PREVIEW"
                ? "bg-amber-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
            title="Guidance preview without sending commands"
          >
            Preview
          </button>
          <button
            onClick={() => setNavigationMode("LIVE_GUIDANCE")}
            disabled={!isDroneLiveAndReady || !calculatedRoute}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1 disabled:opacity-30 disabled:cursor-not-allowed ${
              navigationMode === "LIVE_GUIDANCE"
                ? "bg-emerald-600 text-white shadow-md animate-pulse"
                : isDroneLiveAndReady && calculatedRoute
                ? "bg-[#1E293B] text-emerald-400 hover:bg-[#334155]"
                : "text-slate-500"
            }`}
            title={
              !isDroneLiveAndReady
                ? "Requires active, non-stale drone GPS telemetry fix"
                : !calculatedRoute
                ? "Calculate route before engaging live guidance"
                : "Engage verified live guidance"
            }
          >
            <span>🧭</span>
            <span>Live Flight</span>
          </button>
        </div>
      </div>

      {/* Target Destination Section (FR-03, FR-08) */}
      <div className="space-y-2 border-b border-[#1E293B] pb-3">
        <div className="flex items-center justify-between">
          <h4 className="font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
            <span className="text-red-400">🎯</span> Target Destination (FR-03)
          </h4>
          <button
            onClick={() => setShowDebrisModal(true)}
            className="px-2.5 py-1 bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 rounded border border-cyan-700/60 font-semibold transition"
          >
            From Debris Module →
          </button>
        </div>

        <form onSubmit={handleApplyTarget} className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-400 font-semibold block mb-1">
                Target Latitude (°N, -90 to +90)
              </label>
              <input
                type="number"
                step="0.000001"
                placeholder="e.g. 13.085000"
                value={targetLat}
                onChange={(e) => setTargetLat(e.target.value)}
                className="w-full bg-[#1E293B] border border-[#334155] rounded px-2.5 py-1.5 text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-400 font-semibold block mb-1">
                Target Longitude (°E, -180 to +180)
              </label>
              <input
                type="number"
                step="0.000001"
                placeholder="e.g. 80.275000"
                value={targetLon}
                onChange={(e) => setTargetLon(e.target.value)}
                className="w-full bg-[#1E293B] border border-[#334155] rounded px-2.5 py-1.5 text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          {targetError && (
            <div className="text-[11px] text-red-400 bg-red-950/40 p-1.5 rounded border border-red-800">
              {targetError}
            </div>
          )}

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Target Label (e.g. Runway 07 Inspection Zone)"
              value={targetName}
              onChange={(e) => setTargetName(e.target.value)}
              className="flex-1 bg-[#1E293B] border border-[#334155] rounded px-2.5 py-1.5 text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded font-bold transition shadow-sm"
            >
              Set Target
            </button>
          </div>
        </form>
      </div>

      {/* Waypoint Management Section (FR-04: Add, Edit, Delete, Reorder) */}
      <div className="space-y-2 border-b border-[#1E293B] pb-3">
        <div className="flex items-center justify-between">
          <h4 className="font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
            <span className="text-cyan-400">📍</span> Route Waypoints ({waypoints.length})
          </h4>
          {waypoints.length > 0 && (
            <button
              onClick={() => setShowClearConfirm(true)}
              className="text-[11px] text-slate-400 hover:text-red-400 transition"
            >
              Clear All WPs
            </button>
          )}
        </div>

        {/* Clear Waypoints Confirmation Dialog */}
        {showClearConfirm && (
          <div className="p-2.5 bg-red-950/60 border border-red-800 rounded-lg space-y-2">
            <p className="text-slate-200 text-xs">Clear all planned intermediate waypoints?</p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-2 py-0.5 bg-[#1E293B] text-slate-300 rounded text-[11px]"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  clearWaypoints();
                  setShowClearConfirm(false);
                }}
                className="px-2.5 py-0.5 bg-red-600 hover:bg-red-500 text-white rounded text-[11px] font-bold"
              >
                Confirm Clear
              </button>
            </div>
          </div>
        )}

        {/* Waypoints List */}
        <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
          {waypoints.length === 0 ? (
            <div className="py-3 text-center text-slate-500 bg-[#1E293B]/20 rounded-lg border border-dashed border-[#334155]">
              No intermediate waypoints added. Direct point-to-point path planned.
            </div>
          ) : (
            waypoints.map((wp) => (
              <div
                key={wp.order}
                className="bg-[#1E293B]/60 p-2 rounded-lg border border-[#334155]/60 flex flex-col gap-1.5"
              >
                {editingWaypointOrder === wp.order ? (
                  // Inline Waypoint Edit Form (FR-04)
                  <div className="space-y-1.5 bg-[#0F172A] p-2 rounded border border-cyan-500">
                    <span className="text-[10px] text-cyan-400 font-bold block">
                      Edit Waypoint #{wp.order}
                    </span>
                    <div className="grid grid-cols-3 gap-1">
                      <input
                        type="number"
                        step="0.000001"
                        placeholder="Lat"
                        value={editLat}
                        onChange={(e) => setEditLat(e.target.value)}
                        className="bg-[#1E293B] border border-[#334155] rounded px-1.5 py-0.5 text-slate-100 font-mono text-[11px]"
                      />
                      <input
                        type="number"
                        step="0.000001"
                        placeholder="Lon"
                        value={editLon}
                        onChange={(e) => setEditLon(e.target.value)}
                        className="bg-[#1E293B] border border-[#334155] rounded px-1.5 py-0.5 text-slate-100 font-mono text-[11px]"
                      />
                      <input
                        type="number"
                        step="1"
                        placeholder="Alt (m)"
                        value={editAlt}
                        onChange={(e) => setEditAlt(e.target.value)}
                        className="bg-[#1E293B] border border-[#334155] rounded px-1.5 py-0.5 text-slate-100 font-mono text-[11px]"
                      />
                    </div>
                    <div className="flex justify-end gap-1.5 pt-1">
                      <button
                        onClick={() => setEditingWaypointOrder(null)}
                        className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px]"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveEditWaypoint(wp.order)}
                        className="px-2.5 py-0.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-[10px] font-bold"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  // Waypoint Display Row
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-cyan-600 text-white font-bold flex items-center justify-center text-[10px]">
                        #{wp.order}
                      </span>
                      <div>
                        <span className="font-mono text-slate-200 text-[11px] block">
                          {wp.latitude.toFixed(5)}°, {wp.longitude.toFixed(5)}°
                        </span>
                        <span className="text-[10px] text-slate-400">
                          Alt: {wp.altitude_agl_m}m AGL
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      {/* Edit Button */}
                      <button
                        onClick={() => startEditingWaypoint(wp.order)}
                        className="p-1 text-slate-400 hover:text-cyan-400 text-[11px]"
                        title="Edit Coordinates"
                      >
                        ✏️
                      </button>
                      {/* Reorder UP */}
                      <button
                        disabled={wp.order === 1}
                        onClick={() => reorderWaypoint(wp.order, "UP")}
                        className="p-1 text-slate-400 hover:text-slate-200 disabled:opacity-30"
                        title="Move Up"
                      >
                        ▲
                      </button>
                      {/* Reorder DOWN */}
                      <button
                        disabled={wp.order === waypoints.length}
                        onClick={() => reorderWaypoint(wp.order, "DOWN")}
                        className="p-1 text-slate-400 hover:text-slate-200 disabled:opacity-30"
                        title="Move Down"
                      >
                        ▼
                      </button>
                      {/* Delete */}
                      <button
                        onClick={() => removeWaypoint(wp.order)}
                        className="p-1 text-red-400 hover:text-red-300 ml-1"
                        title="Remove Waypoint"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Add Waypoint Form */}
        <form onSubmit={handleAddWaypoint} className="pt-2 border-t border-[#1E293B]/60 space-y-1.5">
          <span className="text-[10px] text-slate-400 font-semibold block">
            Add Waypoint Manually (or click on map in &quot;Add Waypoint&quot; mode)
          </span>
          <div className="grid grid-cols-3 gap-1.5">
            <input
              type="number"
              step="0.000001"
              placeholder="Lat"
              value={wpLat}
              onChange={(e) => setWpLat(e.target.value)}
              className="bg-[#1E293B] border border-[#334155] rounded px-2 py-1 text-slate-100 font-mono text-xs focus:outline-none"
            />
            <input
              type="number"
              step="0.000001"
              placeholder="Lon"
              value={wpLon}
              onChange={(e) => setWpLon(e.target.value)}
              className="bg-[#1E293B] border border-[#334155] rounded px-2 py-1 text-slate-100 font-mono text-xs focus:outline-none"
            />
            <input
              type="number"
              step="1"
              placeholder="Alt (m)"
              value={wpAlt}
              onChange={(e) => setWpAlt(e.target.value)}
              className="bg-[#1E293B] border border-[#334155] rounded px-2 py-1 text-slate-100 font-mono text-xs focus:outline-none"
            />
          </div>
          {wpError && <div className="text-[10px] text-red-400">{wpError}</div>}
          <button
            type="submit"
            className="w-full py-1 bg-[#1E293B] hover:bg-[#334155] text-cyan-400 rounded font-semibold transition border border-[#334155]"
          >
            + Add Waypoint
          </button>
        </form>
      </div>

      {/* Speed, Operational Limit & Calculation Section (FR-05, FR-06, FR-08) */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <div>
            <label className="text-[11px] text-slate-300 font-semibold block">
              Cruise Speed: {cruiseSpeedMps.toFixed(1)} m/s ({(cruiseSpeedMps * 3.6).toFixed(0)} km/h)
            </label>
            <span className="text-[10px] text-slate-500">
              Source: {speedSource === "MEASURED_TELEMETRY" ? "Live Telemetry" : "Configured Cruise"}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <input
              type="number"
              min="1"
              max="40"
              step="0.5"
              value={cruiseSpeedMps}
              onChange={(e) => setCruiseSpeed(parseFloat(e.target.value) || 10)}
              className="w-16 bg-[#1E293B] border border-[#334155] rounded px-2 py-1 text-slate-100 font-mono text-xs text-right focus:outline-none"
            />
          </div>
        </div>

        {/* Operational Range Limit Indicator (FR-08) */}
        <div className="flex items-center justify-between text-[10px] text-slate-400 bg-[#1E293B]/40 px-2 py-1.5 rounded border border-[#334155]/40">
          <span>Operational Range Limit: {(operationalLimitM / 1000.0).toFixed(1)} km</span>
          <button
            onClick={() => setShowLimitSettings(!showLimitSettings)}
            className="text-cyan-400 hover:text-cyan-300 font-semibold"
          >
            Adjust ⚙
          </button>
        </div>

        {showLimitSettings && (
          <form onSubmit={handleApplyOperationalLimit} className="flex items-center gap-2 bg-[#1E293B]/70 p-2 rounded-lg border border-[#334155]">
            <span className="text-[11px] text-slate-300">Max Range (km):</span>
            <input
              type="number"
              min="0.5"
              max="50.0"
              step="0.5"
              value={tempLimitKm}
              onChange={(e) => setTempLimitKm(e.target.value)}
              className="w-16 bg-[#0F172A] border border-[#334155] rounded px-2 py-0.5 text-xs text-slate-100 font-mono text-right"
            />
            <button
              type="submit"
              className="px-2.5 py-0.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-bold transition"
            >
              Set Limit
            </button>
          </form>
        )}

        {errorMessage && (
          <div className="p-2 bg-red-950/60 border border-red-800 rounded text-red-300 text-[11px]">
            {errorMessage}
          </div>
        )}

        <button
          onClick={calculateRouteAction}
          disabled={!target || isLoadingRoute}
          className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-lg transition shadow-md flex items-center justify-center gap-2 text-sm active:scale-98"
        >
          {isLoadingRoute ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              <span>Computing WGS 84 Geodesic Route...</span>
            </>
          ) : (
            <>
              <span>⚡</span>
              <span>Calculate Flight Route (FR-05, FR-06)</span>
            </>
          )}
        </button>
      </div>

      {/* Route Flight Plan Summary Box (FR-05, FR-06: Precise calculations & distinct distances) */}
      {calculatedRoute && (
        <div className="bg-[#0A0F1D] p-3 rounded-xl border border-cyan-500/40 space-y-2.5">
          <div className="flex items-center justify-between border-b border-[#1E293B] pb-1.5">
            <span className="font-bold text-cyan-400 uppercase tracking-wide">
              Route Flight Plan Summary
            </span>
            <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold text-[10px] border border-emerald-800">
              {calculatedRoute.status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            {/* Total Multi-Segment Route Distance */}
            <div className="bg-[#1E293B]/70 p-2 rounded">
              <span className="text-[10px] text-slate-400 block font-semibold">
                Total Route Distance
              </span>
              <span className="font-mono text-sm font-bold text-slate-100">
                {calculatedRoute.total_distance_m >= 1000
                  ? `${(calculatedRoute.total_distance_m / 1000).toFixed(2)} km`
                  : `${calculatedRoute.total_distance_m.toFixed(1)} m`}
              </span>
            </div>

            {/* Direct Straight-Line Distance */}
            <div className="bg-[#1E293B]/70 p-2 rounded">
              <span className="text-[10px] text-slate-400 block font-semibold">
                Direct Straight-Line
              </span>
              <span className="font-mono text-sm font-bold text-slate-100">
                {calculatedRoute.straight_line_distance_m >= 1000
                  ? `${(calculatedRoute.straight_line_distance_m / 1000).toFixed(2)} km`
                  : `${calculatedRoute.straight_line_distance_m.toFixed(1)} m`}
              </span>
            </div>

            {/* Estimated Travel Time (FR-06: Formats hours properly, e.g. 3h 27m 50s for 124.7km) */}
            <div className="col-span-2 bg-[#1E293B]/70 p-2 rounded flex justify-between items-center">
              <div>
                <span className="text-[10px] text-slate-400 block font-semibold">
                  Estimated Travel Time (FR-06)
                </span>
                <span className="font-mono text-base font-bold text-emerald-400">
                  {calculatedRoute.estimated_time_formatted}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block">
                  Detour: +{calculatedRoute.detour_percentage}%
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  at {calculatedRoute.speed_used_mps.toFixed(1)} m/s
                </span>
              </div>
            </div>
          </div>

          {/* Safety Warnings & Airspace Notices (FR-08) */}
          {calculatedRoute.warnings.length > 0 && (
            <div className="p-2 bg-amber-950/40 border border-amber-800/60 rounded text-[10px] text-amber-300 space-y-1">
              {calculatedRoute.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-1">
                  <span>⚠️</span>
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Action Row: Guidance Preview / Save Route */}
          <div className="pt-1 flex gap-2">
            <button
              onClick={() => setNavigationMode(isDroneLiveAndReady ? "LIVE_GUIDANCE" : "PREVIEW")}
              className={`flex-1 py-2 font-bold rounded-lg transition shadow-md flex items-center justify-center gap-1.5 ${
                isDroneLiveAndReady
                  ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                  : "bg-amber-600 hover:bg-amber-500 text-white"
              }`}
            >
              <span>🧭</span>
              <span>{isDroneLiveAndReady ? "Start Live Guidance" : "Start Guidance Preview"}</span>
            </button>

            <button
              onClick={() => setShowSaveModal(true)}
              className="px-3 py-2 bg-[#1E293B] hover:bg-[#334155] text-slate-200 font-semibold rounded-lg transition border border-[#334155]"
              title="Save Route"
            >
              💾 Save
            </button>
          </div>
        </div>
      )}

      {/* Saved Routes & Clear Drawer (FR-10) */}
      <div className="border-t border-[#1E293B] pt-3 flex items-center justify-between">
        <button
          onClick={() => setShowSavedList(!showSavedList)}
          className="text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
        >
          <span>📁 Saved Routes ({savedRoutes.length})</span>
          <span>{showSavedList ? "▲" : "▼"}</span>
        </button>

        <button
          onClick={clearAllRoute}
          className="text-slate-400 hover:text-red-400 transition"
        >
          Reset Plan
        </button>
      </div>

      {/* Saved Routes Drawer */}
      {showSavedList && (
        <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1 bg-[#0A0F1D] p-2 rounded-lg border border-[#1E293B]">
          {savedRoutes.length === 0 ? (
            <div className="py-2 text-center text-slate-500">No saved routes in database</div>
          ) : (
            savedRoutes.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between p-2 rounded bg-[#1E293B]/60 hover:bg-[#1E293B] transition"
              >
                <div>
                  <span className="font-semibold text-slate-200 block">{r.name}</span>
                  <span className="text-[10px] text-slate-400">
                    {r.total_distance_m >= 1000
                      ? `${(r.total_distance_m / 1000).toFixed(2)}km`
                      : `${r.total_distance_m}m`}{" "}
                    · {r.waypoints.length} WPs
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => loadRouteById(r.id)}
                    className="px-2 py-0.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-[10px] font-semibold"
                  >
                    Load
                  </button>
                  <button
                    onClick={() => deleteRouteAction(r.id)}
                    className="p-1 text-red-400 hover:text-red-300 text-[10px]"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Save Route Dialog Modal (FR-10) */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#0F172A] border border-[#334155] rounded-xl p-5 shadow-2xl w-full max-w-sm text-slate-100 space-y-4">
            <h3 className="font-bold text-base text-slate-100">Save Planned Route</h3>
            <form onSubmit={handleSaveSubmit} className="space-y-3">
              <div>
                <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                  Route Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Runway 07 North Inspection"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  className="w-full bg-[#1E293B] border border-[#334155] rounded px-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowSaveModal(false)}
                  className="px-3 py-1.5 bg-[#1E293B] hover:bg-[#334155] text-slate-300 rounded text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingRoute}
                  className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded text-xs transition"
                >
                  {isSavingRoute ? "Saving..." : "Save Route"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Debris Target Selector Modal (FR-08) */}
      <DebrisTargetSelectorModal
        isOpen={showDebrisModal}
        onClose={() => setShowDebrisModal(false)}
      />
    </div>
  );
}
