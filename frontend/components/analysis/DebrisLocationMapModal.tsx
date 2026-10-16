"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  MapPin,
  ExternalLink,
  Copy,
  Check,
  Compass,
  Navigation,
  ShieldAlert,
  Crosshair,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Info,
} from "lucide-react";
import { DebrisCoordinates } from "../../types/detection";

export interface DebrisLocationMapModalProps {
  isOpen: boolean;
  onClose: () => void;
  detection: {
    id?: string | number;
    frame?: number;
    class_name?: string;
    confidence?: number;
    bbox?: [number, number, number, number] | any;
    debris_coordinates?: DebrisCoordinates | null;
    latitude?: number | null;
    longitude?: number | null;
    coordinate_uncertainty_m?: number | null;
    coordinate_status?: string;
    coordinate_method?: string;
    coordinate_crs?: string;
    coordinate_formatted?: string;
    source_note?: string;
  } | null;
  droneTelemetry?: {
    latitude?: number;
    longitude?: number;
    altitude?: number;
    heading?: number;
  } | null;
}

export const DebrisLocationMapModal: React.FC<DebrisLocationMapModalProps> = ({
  isOpen,
  onClose,
  detection,
  droneTelemetry,
}) => {
  const [copied, setCopied] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !detection) return null;

  const coords = detection.debris_coordinates;
  const lat = coords?.latitude ?? detection.latitude;
  const lon = coords?.longitude ?? detection.longitude;
  const uncertainty = coords?.uncertainty_m ?? detection.coordinate_uncertainty_m;
  const status = (coords?.status ?? detection.coordinate_status ?? "unavailable").toLowerCase();
  const method = coords?.method ?? "raycast_intrinsic_euler";
  const crs = coords?.crs ?? "WGS 84 / EPSG:4326";
  const sourceNote = coords?.source_note;
  const groundPoint = coords?.ground_point_pixels;

  const hasValidCoords =
    typeof lat === "number" &&
    typeof lon === "number" &&
    !isNaN(lat) &&
    !isNaN(lon) &&
    status !== "unavailable";

  // Convert decimal degrees to DMS format
  const toDMS = (val: number, isLat: boolean): string => {
    const absVal = Math.abs(val);
    const degrees = Math.floor(absVal);
    const minutes = Math.floor((absVal - degrees) * 60);
    const seconds = ((absVal - degrees) * 60 - minutes) * 60;
    const direction = isLat ? (val >= 0 ? "N" : "S") : (val >= 0 ? "E" : "W");
    return `${degrees}° ${minutes}' ${seconds.toFixed(2)}" ${direction}`;
  };

  const formattedDMS = hasValidCoords
    ? `${toDMS(lat, true)}, ${toDMS(lon, false)}`
    : "N/A";

  const formattedDD = hasValidCoords
    ? `${lat.toFixed(6)}°, ${lon.toFixed(6)}°`
    : "Coordinates unavailable";

  const handleCopy = () => {
    if (!hasValidCoords) return;
    const textToCopy = `${lat.toFixed(7)}, ${lon.toFixed(7)}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const googleMapsUrl = hasValidCoords
    ? `https://www.google.com/maps?q=${lat},${lon}`
    : "#";

  const osmUrl = hasValidCoords
    ? `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=18/${lat}/${lon}`
    : "#";

  // Bounding box display helper
  const bboxStr = Array.isArray(detection.bbox)
    ? `[${detection.bbox.map((v: number) => Math.round(v)).join(", ")}]`
    : typeof detection.bbox === "object" && detection.bbox
    ? `[${Math.round(detection.bbox.x1 ?? 0)}, ${Math.round(detection.bbox.y1 ?? 0)}, ${Math.round(detection.bbox.x2 ?? 0)}, ${Math.round(detection.bbox.y2 ?? 0)}]`
    : "--";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in font-mono">
      <div className="relative w-full max-w-4xl bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#D9DEE7] bg-[#F5F7FA]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600">
              <Crosshair className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-[#111827] uppercase tracking-wider">
                  ROD Debris Spatial Geolocation & Tactical Map
                </h3>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${
                    status === "verified"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                      : status === "estimated"
                      ? "bg-sky-50 text-[#0066FF] border-sky-300"
                      : "bg-amber-50 text-amber-700 border-amber-300"
                  }`}
                >
                  {status === "verified"
                    ? "Verified RTK"
                    : status === "estimated"
                    ? `Estimated (±${uncertainty ?? 1.5}m)`
                    : "Coordinates Unavailable"}
                </span>
              </div>
              <p className="text-[11px] text-[#5B6472] mt-0.5">
                Garuda Aerospace Runway Observation & Detection (ROD) Engine
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#5B6472] hover:text-[#111827] hover:bg-[#D9DEE7]/50 transition-colors"
            title="Close (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Top Quick Status Callout */}
          {!hasValidCoords && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 flex items-start space-x-2.5">
              <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Notice:</span> Coordinates could not be calculated for this debris detection.
                {sourceNote ? (
                  <span className="block text-[11px] text-amber-700 mt-0.5">{sourceNote}</span>
                ) : (
                  <span className="block text-[11px] text-amber-700 mt-0.5">
                    Drone GPS telemetry or altitude AGL data was missing at the time of frame capture.
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Tactical Map Display Area */}
          <div className="relative w-full h-80 rounded-xl bg-[#0F172A] border border-[#334155] overflow-hidden flex items-center justify-center select-none shadow-inner">
            {/* Tactical Grid Background */}
            <svg
              className="absolute inset-0 w-full h-full opacity-30 pointer-events-none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <pattern id="tactical-grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#38BDF8" strokeWidth="0.5" />
                </pattern>
                <radialGradient id="radar-glow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#0284C7" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#0F172A" stopOpacity="0" />
                </radialGradient>
              </defs>
              <rect width="100%" height="100%" fill="url(#tactical-grid)" />
              <circle cx="50%" cy="50%" r="35%" fill="url(#radar-glow)" />
            </svg>

            {/* Runway Representation (Center Gray Strip) */}
            <div
              className="absolute w-[80%] h-24 bg-[#1E293B] border-y-2 border-dashed border-[#94A3B8]/60 flex items-center justify-between px-6 transition-transform duration-300"
              style={{ transform: `scale(${zoomLevel})` }}
            >
              <span className="text-[12px] font-black text-[#94A3B8]/50 tracking-widest">09L</span>
              <div className="flex-1 flex justify-evenly items-center">
                <span className="w-12 h-1 bg-[#F8FAFC]/40 rounded-full" />
                <span className="w-12 h-1 bg-[#F8FAFC]/40 rounded-full" />
                <span className="w-12 h-1 bg-[#F8FAFC]/40 rounded-full" />
                <span className="w-12 h-1 bg-[#F8FAFC]/40 rounded-full" />
              </div>
              <span className="text-[12px] font-black text-[#94A3B8]/50 tracking-widest">27R</span>
            </div>

            {/* Interactive Target Visuals */}
            {hasValidCoords ? (
              <div
                className="relative z-10 flex flex-col items-center justify-center transition-transform duration-300"
                style={{ transform: `scale(${zoomLevel})` }}
              >
                {/* Uncertainty Circle Radius in meters */}
                <div
                  className="absolute rounded-full border-2 border-red-500/40 bg-red-500/10 animate-pulse pointer-events-none"
                  style={{
                    width: `${Math.max(64, (uncertainty || 1.5) * 40)}px`,
                    height: `${Math.max(64, (uncertainty || 1.5) * 40)}px`,
                  }}
                  title={`Spatial Uncertainty: ±${(uncertainty ?? 1.5).toFixed(1)}m`}
                />

                {/* Concentric Radar Rings */}
                <div className="absolute w-32 h-32 rounded-full border border-sky-400/20 pointer-events-none" />
                <div className="absolute w-48 h-48 rounded-full border border-sky-400/10 pointer-events-none" />

                {/* Debris Target Pin Marker */}
                <div className="relative flex flex-col items-center group cursor-pointer">
                  <div className="w-9 h-9 rounded-full bg-red-600 text-white flex items-center justify-center shadow-lg shadow-red-600/50 border-2 border-white ring-4 ring-red-400/30">
                    <MapPin className="w-5 h-5 fill-current" />
                  </div>
                  <div className="mt-1 px-2 py-0.5 rounded bg-black/80 backdrop-blur border border-red-500/40 text-[10px] font-bold text-red-400 tracking-wider">
                    {detection.class_name || "FOD"} • ±{(uncertainty ?? 1.5).toFixed(1)}m
                  </div>
                </div>

                {/* Drone Location Marker (if telemetry provided) */}
                {droneTelemetry?.latitude && (
                  <div
                    className="absolute -top-24 -left-28 flex flex-col items-center pointer-events-none"
                    style={{
                      transform: `rotate(${droneTelemetry.heading || 0}deg)`,
                    }}
                  >
                    <div className="w-8 h-8 rounded-full bg-[#0066FF] text-white flex items-center justify-center shadow-md border border-white">
                      <Navigation className="w-4 h-4 fill-current transform -rotate-45" />
                    </div>
                    <div className="w-0.5 h-12 bg-gradient-to-b from-[#0066FF] to-transparent" />
                  </div>
                )}
              </div>
            ) : (
              <div className="relative z-10 flex flex-col items-center text-center p-4">
                <ShieldAlert className="w-10 h-10 text-amber-400 mb-2 opacity-80" />
                <span className="text-xs font-bold text-slate-200">
                  GEOLOCATION PROJECTION UNAVAILABLE
                </span>
                <span className="text-[11px] text-slate-400 mt-1 max-w-sm">
                  Debris detected visually in camera frame, but geographic ground raycast requires flight telemetry.
                </span>
              </div>
            )}

            {/* Compass Rose in Corner */}
            <div className="absolute top-3 left-3 bg-[#1E293B]/80 backdrop-blur border border-[#334155] rounded-lg p-2 flex items-center space-x-1.5 text-[10px] text-sky-400">
              <Compass className="w-4 h-4 text-sky-400" />
              <span className="font-bold">GRID NORTH (WGS 84)</span>
            </div>

            {/* Zoom Controls */}
            <div className="absolute bottom-3 right-3 flex items-center space-x-1 bg-[#1E293B]/80 backdrop-blur border border-[#334155] rounded-lg p-1 text-slate-300">
              <button
                onClick={() => setZoomLevel((z) => Math.min(2.0, z + 0.25))}
                className="p-1 hover:text-white hover:bg-slate-700/50 rounded transition"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={() => setZoomLevel(1.0)}
                className="p-1 hover:text-white hover:bg-slate-700/50 rounded transition"
                title="Reset Zoom"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.25))}
                className="p-1 hover:text-white hover:bg-slate-700/50 rounded transition"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Coordinates and Geodetic Specs Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Decimal Degrees & DMS Card */}
            <div className="p-4 rounded-xl border border-[#D9DEE7] bg-[#F5F7FA] space-y-3">
              <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2">
                <span className="text-xs font-bold text-[#111827] uppercase tracking-wider flex items-center space-x-1.5">
                  <MapPin className="w-3.5 h-3.5 text-[#0066FF]" />
                  <span>Geographic Coordinates</span>
                </span>
                {hasValidCoords && (
                  <button
                    onClick={handleCopy}
                    className="flex items-center space-x-1 text-[11px] font-semibold text-[#0066FF] hover:text-[#0052CC] bg-white px-2 py-0.5 rounded border border-[#D9DEE7] transition shadow-xs"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-600">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy DD</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              <div>
                <div className="text-[10px] text-[#5B6472] uppercase font-semibold">Decimal Degrees (DD)</div>
                <div className="text-base font-bold text-[#111827] mt-0.5 select-all font-mono">
                  {formattedDD}
                </div>
              </div>

              <div>
                <div className="text-[10px] text-[#5B6472] uppercase font-semibold">Degrees Minutes Seconds (DMS)</div>
                <div className="text-xs font-semibold text-[#5B6472] mt-0.5 select-all font-mono">
                  {formattedDMS}
                </div>
              </div>

              <div className="pt-2 border-t border-[#D9DEE7] flex items-center justify-between text-xs">
                <div>
                  <span className="text-[10px] text-[#5B6472] block">Coordinate Status:</span>
                  <span className="font-bold text-[#111827] capitalize">{status}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#5B6472] block">Spatial Uncertainty:</span>
                  <span className="font-bold text-red-600">
                    {uncertainty !== null && uncertainty !== undefined ? `±${uncertainty.toFixed(1)} m` : "N/A"}
                  </span>
                </div>
              </div>
            </div>

            {/* Projection & Detection Metadata Card */}
            <div className="p-4 rounded-xl border border-[#D9DEE7] bg-[#F5F7FA] space-y-3">
              <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2">
                <span className="text-xs font-bold text-[#111827] uppercase tracking-wider flex items-center space-x-1.5">
                  <Crosshair className="w-3.5 h-3.5 text-red-600" />
                  <span>Detection & Raycast Provenance</span>
                </span>
                <span className="text-[11px] font-bold text-[#0066FF]">
                  {detection.confidence ? `${(detection.confidence * 100).toFixed(1)}% Conf` : "--"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-[10px] text-[#5B6472] uppercase block">Entity Class</span>
                  <span className="font-bold text-[#111827]">{detection.class_name || "FOD"}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#5B6472] uppercase block">Target Frame #</span>
                  <span className="font-bold text-[#111827]">
                    {detection.frame !== undefined ? `Frame ${detection.frame}` : "Static Image"}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#5B6472] uppercase block">Datum / CRS</span>
                  <span className="font-bold text-[#111827] text-[11px]">{crs}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#5B6472] uppercase block">Math Model</span>
                  <span className="font-bold text-[#111827] text-[11px]">{method}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-[#D9DEE7] text-[11px] space-y-1">
                <div className="flex justify-between">
                  <span className="text-[#5B6472]">Bounding Box:</span>
                  <span className="font-bold text-[#111827]">{bboxStr}</span>
                </div>
                {groundPoint && (
                  <div className="flex justify-between">
                    <span className="text-[#5B6472]">Ground Contact Point:</span>
                    <span className="font-bold text-[#0066FF]">
                      ({Math.round(groundPoint[0])}px, {Math.round(groundPoint[1])}px)
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* External Map Services (FR-08) */}
          {hasValidCoords && (
            <div className="p-3 rounded-lg border border-[#D9DEE7] bg-white flex flex-wrap items-center justify-between gap-3 text-xs">
              <span className="text-[#5B6472] font-semibold flex items-center space-x-1.5">
                <ExternalLink className="w-3.5 h-3.5 text-[#0066FF]" />
                <span>External Navigation & Satellite Imagery:</span>
              </span>
              <div className="flex items-center space-x-2">
                <a
                  href={googleMapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-[#F5F7FA] hover:bg-[#EAF3FF] hover:text-[#0066FF] border border-[#D9DEE7] text-[#111827] font-semibold transition flex items-center space-x-1.5"
                >
                  <span>Google Maps</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
                <a
                  href={osmUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-[#F5F7FA] hover:bg-[#EAF3FF] hover:text-[#0066FF] border border-[#D9DEE7] text-[#111827] font-semibold transition flex items-center space-x-1.5"
                >
                  <span>OpenStreetMap</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-[#D9DEE7] bg-[#F5F7FA] flex items-center justify-between">
          <span className="text-[10px] text-[#5B6472]">
            WGS 84 Geodesic Projection • Raycast Decoupled Spatial Uncertainty
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#0066FF] hover:bg-[#0052CC] text-white text-xs font-bold transition shadow-sm"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
};
