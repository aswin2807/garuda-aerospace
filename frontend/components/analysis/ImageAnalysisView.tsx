"use client";

import React, { useState } from "react";
import { useAnalysisStore } from "../../stores/analysisStore";
import { useAnalysis } from "../../hooks/useAnalysis";
import { UploadMedia } from "./UploadMedia";
import { DebrisLocationMapModal } from "./DebrisLocationMapModal";
import { MapPin } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const ImageAnalysisView: React.FC = () => {
  const activeJob = useAnalysisStore((s) => s.activeJob);
  const filePreviewUrl = useAnalysisStore((s) => s.filePreviewUrl);
  const selectedFile = useAnalysisStore((s) => s.selectedFile);
  const jobResults = useAnalysisStore((s) => s.jobResults);
  const resetAnalysis = useAnalysisStore((s) => s.resetAnalysis);

  const { start, loading, error } = useAnalysis();
  const [activeTab, setActiveTab] = useState<"annotated" | "original">("annotated");
  const [selectedDebrisForMap, setSelectedDebrisForMap] = useState<any | null>(null);

  const analysisType = useAnalysisStore((s) => s.analysisType);

  const results = jobResults || activeJob;
  const isCompleted = results?.status === "COMPLETED";
  const annotatedImagePath = results?.annotated_media_path;
  const atype = (results?.analysis_type || activeJob?.analysis_type || analysisType || "NAVIGATION").toUpperCase();

  const handleStartAnalysis = async () => {
    const jid = activeJob?.job_id || activeJob?.id;
    if (jid) {
      await start(jid);
    }
  };

  const resultJobId = results?.job_id || results?.id || "";

  return (
    <div className="flex flex-col space-y-4 font-mono">
      {!activeJob && !selectedFile ? (
        <UploadMedia />
      ) : (
        <div className="flex flex-col bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl overflow-hidden shadow-sm">
          {/* Top Bar */}
          <div className="flex items-center justify-between px-4 py-2.5 bg-[#FFFFFF] border-b border-[#D9DEE7]">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-[#111827] uppercase tracking-wider">
                {atype.replace("_", " ")} INSPECTION:
              </span>
              <span className="text-[11px] text-[#5B6472] bg-[#F5F7FA] px-2 py-0.5 rounded border border-[#D9DEE7]">
                {activeJob?.filename || selectedFile?.name}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              {isCompleted && annotatedImagePath && (
                <div className="flex items-center space-x-1 bg-[#F5F7FA] border border-[#D9DEE7] rounded p-0.5 text-[11px]">
                  <button
                    onClick={() => setActiveTab("annotated")}
                    className={`px-2 py-0.5 rounded font-medium transition-colors ${
                      activeTab === "annotated"
                        ? "bg-[#0066FF] text-[#FFFFFF]"
                        : "text-[#5B6472] hover:text-[#111827]"
                    }`}
                  >
                    AI Annotated
                  </button>
                  <button
                    onClick={() => setActiveTab("original")}
                    className={`px-2 py-0.5 rounded font-medium transition-colors ${
                      activeTab === "original"
                        ? "bg-[#0066FF] text-[#FFFFFF]"
                        : "text-[#5B6472] hover:text-[#111827]"
                    }`}
                  >
                    Original
                  </button>
                </div>
              )}

              <button
                onClick={resetAnalysis}
                className="text-[11px] text-[#5B6472] hover:text-rose-600 transition-colors px-2 py-1 rounded hover:bg-[#F0F6FF]"
              >
                Upload Different Image
              </button>
            </div>
          </div>

          {/* Main Visual Display (Black for contrast) */}
          <div className="relative aspect-video max-h-[500px] bg-[#000000] flex items-center justify-center overflow-hidden p-2">
            {isCompleted && annotatedImagePath && activeTab === "annotated" && resultJobId ? (
              // Serving via analysis image download / results
              <img
                src={`${API_BASE}/api/v1/analysis/${encodeURIComponent(resultJobId)}/video`}
                alt="AI Annotated Output"
                className="w-full h-full object-contain rounded"
              />
            ) : filePreviewUrl ? (
              <img
                src={filePreviewUrl}
                alt="Original Drone Frame"
                className="w-full h-full object-contain rounded"
              />
            ) : (
              <div className="text-[#5B6472] text-xs">No image preview available</div>
            )}

            {/* Awaiting Start Overlay */}
            {(!isCompleted && results?.status !== "ANALYZING") && (
              <div className="absolute inset-0 bg-[#000000]/75 backdrop-blur-[2px] flex flex-col items-center justify-center p-6 text-center select-none">
                <button
                  onClick={handleStartAnalysis}
                  disabled={loading}
                  className="flex items-center space-x-2 px-6 py-2.5 bg-[#0066FF] hover:bg-[#008CFF] text-[#FFFFFF] text-xs font-bold rounded-lg shadow-md border border-[#0066FF] transition-all transform hover:scale-105 active:scale-95 disabled:opacity-50"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  <span>
                    RUN {atype.replace("_", " ")} INFERENCE
                  </span>
                </button>
                <p className="text-[11px] text-[#EAF3FF] mt-2 max-w-sm">
                  {atype === "NAVIGATION" && "Executes isolated Navigation model (navigation_best.pt)."}
                  {atype === "FOD" && "Executes isolated FOD model (FOD_Karhtikeyan.pt)."}
                  {atype === "RUNWAY_LIGHT" && "Executes isolated Runway Light model (runway_light_best.pt)."}
                </p>
              </div>
            )}

            {/* In-flight Loading Overlay */}
            {results?.status === "ANALYZING" && (
              <div className="absolute inset-0 bg-[#000000]/80 backdrop-blur-[2px] flex flex-col items-center justify-center select-none">
                <div className="w-8 h-8 border-2 border-[#0066FF] border-t-transparent rounded-full animate-spin mb-3" />
                <span className="text-xs font-bold text-[#008CFF] uppercase tracking-wider">
                  Executing {atype.replace("_", " ")} Inference...
                </span>
              </div>
            )}
          </div>

          {/* Metrics & Detection Breakdown (When Completed) */}
          {isCompleted && (
            <div className="p-4 bg-[#FFFFFF] border-t border-[#D9DEE7] flex flex-col space-y-4">
              {atype === "NAVIGATION" && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">Nav Objects</div>
                    <div className="text-base font-bold text-[#0066FF] mt-0.5">
                      {results.nav_count ?? 0}
                    </div>
                  </div>
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">Inference Latency</div>
                    <div className="text-base font-bold text-[#111827] mt-0.5">
                      {results.processing_time_ms ? `${results.processing_time_ms} ms` : "--"}
                    </div>
                  </div>
                </div>
              )}

              {atype === "FOD" && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">FOD Debris</div>
                    <div className="text-base font-bold text-[#111827] mt-0.5">
                      {results.fod_count ?? 0}
                    </div>
                  </div>
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">Inference Latency</div>
                    <div className="text-base font-bold text-[#0066FF] mt-0.5">
                      {results.processing_time_ms ? `${results.processing_time_ms} ms` : "--"}
                    </div>
                  </div>
                </div>
              )}

              {atype === "RUNWAY_LIGHT" && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">Lights Active</div>
                    <div className="text-base font-bold text-[#0066FF] mt-0.5">
                      {results.light_on_count ?? 0}
                    </div>
                  </div>
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">Lights Inactive</div>
                    <div className="text-base font-bold text-[#5B6472] mt-0.5">
                      {results.light_off_count ?? 0}
                    </div>
                  </div>
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">Runway Faults</div>
                    <div className="text-base font-bold text-rose-600 mt-0.5">
                      {results.confirmed_faults ?? 0}
                    </div>
                  </div>
                  <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded p-2 text-center">
                    <div className="text-[9px] text-[#5B6472] uppercase font-bold">Total Lights</div>
                    <div className="text-base font-bold text-[#111827] mt-0.5">
                      {(results.light_on_count ?? 0) + (results.light_off_count ?? 0)}
                    </div>
                  </div>
                </div>
              )}

              {/* Detected Objects Table */}
              {results.sample_detections && results.sample_detections.length > 0 && (
                <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg p-3">
                  <div className="text-xs font-bold text-[#111827] uppercase mb-2 flex items-center justify-between">
                    <span>Detected Entities ({results.sample_detections.length})</span>
                    {atype === "FOD" && (
                      <span className="text-[10px] text-red-600 font-bold uppercase">
                        ROD Debris Spatial Geolocation Active
                      </span>
                    )}
                  </div>
                  <div className="max-h-60 overflow-y-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="text-[#5B6472] border-b border-[#D9DEE7]">
                          <th className="py-1.5 px-2">Model</th>
                          <th className="py-1.5 px-2">Class</th>
                          <th className="py-1.5 px-2">Confidence</th>
                          <th className="py-1.5 px-2">Bounding Box</th>
                          <th className="py-1.5 px-2">Debris Coordinates</th>
                          <th className="py-1.5 px-2 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9DEE7]">
                        {results.sample_detections.map((det: any, i: number) => {
                          const coords = det.debris_coordinates;
                          const lat = coords?.latitude ?? det.latitude;
                          const lon = coords?.longitude ?? det.longitude;
                          const unc = coords?.uncertainty_m ?? det.coordinate_uncertainty_m;
                          const st = (coords?.status ?? det.coordinate_status ?? "unavailable").toLowerCase();
                          const hasCoords = typeof lat === "number" && typeof lon === "number" && !isNaN(lat) && !isNaN(lon) && st !== "unavailable";

                          return (
                            <tr key={i} className="text-[#111827] hover:bg-[#F0F6FF]">
                              <td className="py-2 px-2 uppercase text-[#5B6472] text-[10px]">{det.model || "yolo"}</td>
                              <td className="py-2 px-2 font-bold text-[#0066FF]">{det.class_name}</td>
                              <td className="py-2 px-2 text-[#0066FF]">{(det.confidence * 100).toFixed(1)}%</td>
                              <td className="py-2 px-2 text-[#5B6472] font-mono text-[10px]">
                                {Array.isArray(det.bbox)
                                  ? `[${det.bbox.map((v: number) => Math.round(v)).join(", ")}]`
                                  : JSON.stringify(det.bbox)}
                              </td>
                              <td className="py-2 px-2 text-[11px]">
                                {hasCoords ? (
                                  <div className="flex items-center space-x-1.5">
                                    <span className="font-bold text-[#111827]">
                                      {lat.toFixed(5)}°, {lon.toFixed(5)}°
                                    </span>
                                    <span
                                      className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${
                                        st === "verified"
                                          ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                          : "bg-sky-50 text-[#0066FF] border-sky-300"
                                      }`}
                                    >
                                      ±{(unc ?? 1.5).toFixed(1)}m
                                    </span>
                                  </div>
                                ) : (
                                  <span className="text-[#5B6472] italic text-[10px]">
                                    {coords?.formatted || "Unavailable"}
                                  </span>
                                )}
                              </td>
                              <td className="py-2 px-2 text-right">
                                <button
                                  onClick={() => setSelectedDebrisForMap(det)}
                                  className="px-2 py-0.5 rounded text-[10px] bg-[#F5F7FA] hover:bg-[#EAF3FF] hover:text-[#0066FF] border border-[#D9DEE7] text-[#5B6472] font-semibold inline-flex items-center space-x-1"
                                  title="View on Map"
                                >
                                  <MapPin className="w-3 h-3 text-[#0066FF]" />
                                  <span>Map</span>
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="p-3 bg-rose-50 border-t border-rose-200 text-rose-700 text-xs">
              {error}
            </div>
          )}

          {/* Reusable Debris Location Map Modal (FR-08) */}
          <DebrisLocationMapModal
            isOpen={!!selectedDebrisForMap}
            onClose={() => setSelectedDebrisForMap(null)}
            detection={selectedDebrisForMap}
            droneTelemetry={results.drone_telemetry}
          />
        </div>
      )}
    </div>
  );
};
