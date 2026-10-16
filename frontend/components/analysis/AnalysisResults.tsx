"use client";

import React, { useState } from "react";
import { useAnalysisStore } from "../../stores/analysisStore";
import { RunwayGridMatrix } from "../runway/RunwayGridMatrix";
import { DebrisLocationMapModal } from "./DebrisLocationMapModal";
import { OfflineVideoReviewWorkspace } from "./OfflineVideoReviewWorkspace";
import { MapPin, ExternalLink, AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const AnalysisResults: React.FC = () => {
  const activeJob = useAnalysisStore((s) => s.activeJob);
  const jobResults = useAnalysisStore((s) => s.jobResults);

  const [isPlayingAnalyzedVideo, setIsPlayingAnalyzedVideo] = useState(false);
  const [showDetectionSamples, setShowDetectionSamples] = useState(false);
  const [selectedDebrisForMap, setSelectedDebrisForMap] = useState<any | null>(null);

  if (!activeJob && !jobResults) return null;

  const data = jobResults || activeJob;
  const isCompleted = activeJob?.status === "COMPLETED" || jobResults?.status === "COMPLETED";

  if (!isCompleted || !data) return null;

  const formatTime = (seconds?: number) => {
    if (!seconds) return "0s";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  const jobId = data.job_id || data.id || "";
  const analyzedVideoUrl = `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/video`;
  const csvReportUrl = `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/report?format=csv`;
  const jsonReportUrl = `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/report?format=json`;

  const atype = (data.analysis_type || activeJob?.analysis_type || "NAVIGATION").toUpperCase();

  return (
    <div className="flex flex-col bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl overflow-hidden font-mono shadow-sm space-y-4 p-5">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#D9DEE7] pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-3 h-3 rounded-full bg-[#0066FF] shadow-sm shadow-[#0066FF]/30" />
          <h3 className="text-sm font-bold text-[#111827] tracking-wider uppercase">
            {atype === "NAVIGATION" && "NAVIGATION AI ANALYSIS COMPLETED — SUMMARY REPORT"}
            {atype === "FOD" && "FOD DEBRIS AI ANALYSIS COMPLETED — SUMMARY REPORT"}
            {atype === "RUNWAY_LIGHT" && "RUNWAY LIGHT FAULT AI ANALYSIS COMPLETED — SUMMARY REPORT"}
            {atype !== "NAVIGATION" && atype !== "FOD" && atype !== "RUNWAY_LIGHT" && `${atype} AI ANALYSIS COMPLETED`}
          </h3>
        </div>

        <div className="flex items-center space-x-2">
          <a
            href={csvReportUrl}
            download
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] text-xs font-semibold transition-colors"
          >
            <svg className="w-3.5 h-3.5 text-[#0066FF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>DOWNLOAD CSV</span>
          </a>

          <a
            href={jsonReportUrl}
            download
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] text-xs font-semibold transition-colors"
          >
            <svg className="w-3.5 h-3.5 text-[#0066FF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>DOWNLOAD JSON</span>
          </a>
        </div>
      </div>

      {/* Model Verification Provenance & Section 9.2 Transparency Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[#5B6472] font-semibold">MODEL PROVENANCE:</span>
          {data.model_path && (
            <span className="text-[#111827] font-bold">
              {data.model_path.split("/").pop()}
            </span>
          )}
          {data.model_version && (
            <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-[#FFFFFF] text-[#0066FF] border border-[#0066FF]/30 font-semibold" title={`Cryptographic SHA-256 prefix: ${data.model_version}`}>
              SHA256:{data.model_version.substring(0, 10)}
            </span>
          )}
          {data.confidence_threshold !== undefined && data.confidence_threshold !== null && (
            <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-[#FFFFFF] text-[#5B6472] border border-[#D9DEE7]">
              CONF THRESHOLD: {(Number(data.confidence_threshold) * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {data.outcome_status && (
          <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold border ${
            data.outcome_status === "COMPLETED_WITH_DETECTIONS"
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : data.outcome_status === "COMPLETED_NO_DETECTIONS"
              ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30"
              : "bg-amber-50 text-amber-700 border-amber-200"
          }`}>
            {data.outcome_status.replace(/_/g, " ")}
          </span>
        )}
      </div>

      {atype === "NAVIGATION" && (
        <div className="flex flex-col space-y-3">
          <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-[#0066FF]" />
              <span className="text-xs font-bold text-[#111827]">
                {(data.unique_nav_count ?? data.nav_count ?? 0) > 0
                  ? `NAVIGATION DETECTION COMPLETED — ${(data.unique_nav_count ?? data.nav_count ?? 0)} UNIQUE OBJECTS IDENTIFIED`
                  : "NAVIGATION DETECTION COMPLETED — NO NAVIGATION TARGETS DETECTED"}
              </span>
            </div>
            <span className="text-[10px] text-[#5B6472] font-semibold">
              Technical job completed (100% frames processed)
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Unique Navigation Objects
              </span>
              <div className="text-xl font-bold text-[#0066FF] mt-1">
                {(data.unique_nav_count ?? data.nav_count ?? 0).toLocaleString()}
              </div>
              <span className="text-[10px] text-[#5B6472]">
                Total Frame Hits: {(data.total_detections ?? data.total_frame_detections ?? 0).toLocaleString()}
              </span>
            </div>

            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Processing Speed & Ratio
              </span>
              <div className="text-xl font-bold text-[#111827] mt-1">
                {data.processing_fps ? `${data.processing_fps.toFixed(1)} FPS` : "--"}
              </div>
              <span className="text-[10px] text-[#0066FF] font-semibold">
                Speed Ratio: {data.speed_ratio ? `${data.speed_ratio.toFixed(2)}x` : (data.duration_seconds > 0 ? `${((data.elapsed_seconds || 0) / data.duration_seconds).toFixed(2)}x` : "--")}
              </span>
            </div>

            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Analysis vs Video Duration
              </span>
              <div className="text-xl font-bold text-[#111827] mt-1">
                {formatTime(data.elapsed_seconds)}
              </div>
              <span className="text-[10px] text-[#5B6472]">
                Video Length: {formatTime(data.duration_seconds)}
              </span>
            </div>

            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Total Frames Inferred
              </span>
              <div className="text-xl font-bold text-[#111827] mt-1">
                {(data.processed_frames || data.total_frames || 0).toLocaleString()}
              </div>
              <span className="text-[10px] text-[#5B6472]">
                Avg Latency: {data.avg_inference_ms ? `${data.avg_inference_ms.toFixed(1)} ms` : "--"}
              </span>
            </div>
          </div>
        </div>
      )}

      {atype === "FOD" && (
        <div className="flex flex-col space-y-3">
          {/* Honest Status & Detection Outcome Banner */}
          {(data.unique_fod_count ?? data.fod_count ?? 0) > 0 ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2.5">
                <span className="w-3 h-3 rounded-full bg-red-600 animate-pulse flex-shrink-0" />
                <div>
                  <div className="text-xs font-bold text-red-700 tracking-wider">
                    HAZARD ALERT — {(data.unique_fod_count ?? data.fod_count ?? 0)} UNIQUE UNWANTED OBJECT(S) DETECTED
                  </div>
                  <div className="text-[11px] text-red-600 mt-0.5">
                    Trained FOD model identified foreign debris across {(data.total_detections ?? data.total_frame_detections ?? 0).toLocaleString()} frame detections.
                  </div>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <span className="inline-block px-2.5 py-1 rounded bg-red-100 text-red-800 text-[10px] font-bold">
                  DEBRIS DETECTED
                </span>
              </div>
            </div>
          ) : (
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2.5">
                <span className="w-3 h-3 rounded-full bg-emerald-600 flex-shrink-0" />
                <div>
                  <div className="text-xs font-bold text-emerald-800 tracking-wider">
                    CLEAN RUNWAY — NO UNWANTED FOD OBJECTS DETECTED (0 FOUND)
                  </div>
                  <div className="text-[11px] text-emerald-700 mt-0.5">
                    Technical processing job completed (100% of frames analyzed). No debris surpassed detection confidence threshold.
                  </div>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <span className="inline-block px-2.5 py-1 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                  RUNWAY CLEAR
                </span>
              </div>
            </div>
          )}

          {/* Runway Pathway ROI Filter Status (PRD Section 4 & 5) */}
          <div className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-bold text-[#111827]">RUNWAY PATHWAY ROI:</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-300">
                ACTIVE · RESTRICTED TO VALID RUNWAY CORRIDOR
              </span>
            </div>
            <div className="flex items-center space-x-3 text-[11px] text-[#475569]">
              <span>Boundary Rule: <strong className="text-[#0F172A]">{data.roi_info?.boundary_rule || "BOTTOM_CENTER"}</strong></span>
              <span>In-Pathway Debris: <strong className="text-emerald-700 font-bold">{(data.unique_fod_count ?? data.fod_count ?? 0)}</strong></span>
              {(data.pathway_filtered_count || data.outside_pathway_filtered) ? (
                <span>Filtered Out-of-Pathway: <strong className="text-amber-700 font-bold">{data.pathway_filtered_count || data.outside_pathway_filtered}</strong></span>
              ) : null}
            </div>
          </div>

          {/* Detailed FOD Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Total Unique FOD Objects
              </span>
              <div className="text-xl font-bold text-red-600 mt-1">
                {(data.unique_fod_count ?? data.fod_count ?? 0).toLocaleString()}
              </div>
              <span className="text-[10px] text-[#5B6472]">
                Multi-Frame Tracked Objects
              </span>
            </div>

            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Total Frame Detections
              </span>
              <div className="text-xl font-bold text-[#0066FF] mt-1">
                {(data.total_detections ?? data.total_frame_detections ?? 0).toLocaleString()}
              </div>
              <span className="text-[10px] text-[#5B6472]">
                Cumulative Video Hits
              </span>
            </div>

            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Processing Speed & Ratio
              </span>
              <div className="text-xl font-bold text-[#111827] mt-1">
                {data.processing_fps ? `${data.processing_fps.toFixed(1)} FPS` : "--"}
              </div>
              <span className="text-[10px] text-[#0066FF] font-semibold">
                Speed Ratio: {data.speed_ratio ? `${data.speed_ratio.toFixed(2)}x` : (data.duration_seconds > 0 ? `${((data.elapsed_seconds || 0) / data.duration_seconds).toFixed(2)}x` : "--")}
              </span>
            </div>

            <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-3">
              <span className="text-[10px] text-[#5B6472] uppercase tracking-wider">
                Analysis vs Video Duration
              </span>
              <div className="text-xl font-bold text-[#111827] mt-1">
                {formatTime(data.elapsed_seconds)}
              </div>
              <span className="text-[10px] text-[#5B6472]">
                Video Length: {formatTime(data.duration_seconds)}
              </span>
            </div>
          </div>

          {/* Model Information & Category Breakdown */}
          <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-2">
              <span className="text-[#5B6472] font-semibold">Trained AI Model:</span>
              <span className="font-bold text-[#111827]">FOD_Karhtikeyan.pt (YOLOv11)</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-[#5B6472] font-semibold">Category Breakdown:</span>
              <span className="font-bold text-[#0066FF]">
                FOD Debris: {(data.unique_fod_count ?? data.fod_count ?? 0)} objects ({(data.total_detections ?? data.total_frame_detections ?? 0)} frames)
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-[#5B6472] font-semibold">Avg Latency:</span>
              <span className="font-bold text-[#111827]">
                {data.avg_inference_ms ? `${data.avg_inference_ms.toFixed(1)} ms / frame` : "--"}
              </span>
            </div>
          </div>

          {/* ROD Debris Detections & Predicted Coordinates Table (FR-01, FR-07, FR-08) */}
          <div className="pt-2 border-t border-[#D9DEE7]">
            <div className="text-xs font-bold text-red-600 uppercase tracking-wider mb-2 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-pulse" />
                <span>ROD DEBRIS DETECTIONS & PREDICTED COORDINATES TABLE</span>
              </div>
              <span className="text-[11px] font-normal text-[#5B6472]">
                WGS 84 Geodesic Plane • Decoupled Spatial Uncertainty
              </span>
            </div>

            {data.sample_detections && data.sample_detections.length > 0 ? (
              <div className="overflow-x-auto rounded-lg border border-[#D9DEE7] bg-white">
                <table className="w-full text-left font-mono text-xs">
                  <thead className="bg-[#F5F7FA] text-[#5B6472] border-b border-[#D9DEE7]">
                    <tr>
                      <th className="py-2.5 px-3 font-semibold">ID / Frame</th>
                      <th className="py-2.5 px-3 font-semibold">Debris Class</th>
                      <th className="py-2.5 px-3 font-semibold text-center">Confidence</th>
                      <th className="py-2.5 px-3 font-semibold text-center">BBox & Ground Contact</th>
                      <th className="py-2.5 px-3 font-semibold text-center">Pathway ROI</th>
                      <th className="py-2.5 px-3 font-semibold text-center">Debris Coordinates</th>
                      <th className="py-2.5 px-3 font-semibold text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D9DEE7]">
                    {data.sample_detections.map((det: any, idx: number) => {
                      const coords = det.debris_coordinates;
                      const lat = coords?.latitude ?? det.latitude;
                      const lon = coords?.longitude ?? det.longitude;
                      const unc = coords?.uncertainty_m ?? det.coordinate_uncertainty_m;
                      const st = (coords?.status ?? det.coordinate_status ?? "unavailable").toLowerCase();
                      const hasCoords = typeof lat === "number" && typeof lon === "number" && !isNaN(lat) && !isNaN(lon) && st !== "unavailable";
                      const bboxStr = Array.isArray(det.bbox)
                        ? `[${det.bbox.map((n: number) => Math.round(n)).join(", ")}]`
                        : typeof det.bbox === "object" && det.bbox
                        ? `[${Math.round(det.bbox.x1 ?? 0)}, ${Math.round(det.bbox.y1 ?? 0)}, ${Math.round(det.bbox.x2 ?? 0)}, ${Math.round(det.bbox.y2 ?? 0)}]`
                        : "--";
                      const groundPoint = coords?.ground_point_pixels;

                      return (
                        <tr key={idx} className="hover:bg-red-50/30 transition-colors">
                          <td className="py-2.5 px-3 font-bold text-[#111827]">
                            {det.frame !== undefined ? `Frame ${det.frame}` : `#${idx + 1}`}
                            {det.track_id !== undefined && (
                              <span className="block text-[10px] text-[#5B6472] font-normal">
                                Track #{det.track_id}
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-red-600">
                            {det.class_name || "FOD"}
                          </td>
                          <td className="py-2.5 px-3 text-center font-bold text-[#0066FF]">
                            {det.confidence ? `${(det.confidence * 100).toFixed(1)}%` : "--"}
                          </td>
                          <td className="py-2.5 px-3 text-center text-[10px] text-[#5B6472]">
                            <div>{bboxStr}</div>
                            {groundPoint && (
                              <div className="text-[9px] text-[#0066FF] font-semibold mt-0.5">
                                Base: ({Math.round(groundPoint[0])}, {Math.round(groundPoint[1])})
                              </div>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-300">
                              {det.roi_status ? String(det.roi_status).replace(/_/g, " ") : "IN PATHWAY"}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            {hasCoords ? (
                              <div className="flex flex-col items-center space-y-1">
                                <span className="font-bold text-[#111827] text-xs">
                                  {coords?.formatted || `${lat.toFixed(6)}°, ${lon.toFixed(6)}°`}
                                </span>
                                <div className="flex items-center space-x-1.5">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                                      st === "verified"
                                        ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                        : "bg-sky-50 text-[#0066FF] border-sky-300"
                                    }`}
                                  >
                                    {st === "verified" ? "Verified RTK" : `Estimated (±${(unc ?? 1.5).toFixed(1)}m)`}
                                  </span>
                                </div>
                              </div>
                            ) : (
                              <div className="flex flex-col items-center space-y-0.5">
                                <span className="text-[#5B6472] italic text-[11px]">Coordinates unavailable</span>
                                <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-amber-50 text-amber-700 border border-amber-300" title={coords?.source_note || "GPS/altitude telemetry missing"}>
                                  Telemetry Missing
                                </span>
                              </div>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <button
                              onClick={() => setSelectedDebrisForMap(det)}
                              className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1 mx-auto transition border ${
                                hasCoords
                                  ? "bg-[#0066FF] hover:bg-[#0052CC] text-white border-[#0066FF] shadow-xs"
                                  : "bg-[#F5F7FA] text-[#5B6472] hover:bg-[#EAF3FF] hover:text-[#0066FF] border-[#D9DEE7]"
                              }`}
                              title={hasCoords ? "View location on tactical map" : "Inspect coordinate projection status"}
                            >
                              <MapPin className="w-3.5 h-3.5" />
                              <span>View on Map</span>
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4 rounded-lg border border-[#D9DEE7] bg-[#F5F7FA] text-center text-[#5B6472]">
                <span className="text-xs font-semibold">Zero debris detections recorded. Runway surface clear.</span>
              </div>
            )}
          </div>
        </div>
      )}

      {atype === "RUNWAY_LIGHT" && (
        <div className="flex flex-col space-y-4">
          {/* Visual Interactive Row & Column Grid Matrix */}
          <RunwayGridMatrix
            matrix={data.matrix}
            faults={data.faults}
            totalLights={data.total_lights}
            lightsOn={data.light_on_count}
            lightsOff={data.light_off_count}
            lightsUnknown={data.unknown_light_count}
            confirmedFaults={data.confirmed_faults}
            rowsDetected={data.rows_detected}
          />

          {/* Confirmed Faults List Table if any exist */}
          {((data.faults && data.faults.length > 0) || (data.confirmed_faults ?? 0) > 0) && (
            <div className="pt-2 border-t border-[#D9DEE7]">
              <div className="text-xs font-bold text-red-600 uppercase tracking-wider mb-2 flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-pulse" />
                <span>CONFIRMED RUNWAY LIGHT FAULTS LIST (VERIFIED ≥5 CONSECUTIVE FRAMES)</span>
              </div>
              <div className="overflow-x-auto rounded-lg border border-red-200 bg-red-50/20">
                <table className="w-full text-left font-mono text-xs">
                  <thead className="bg-red-100/60 text-red-800 border-b border-red-200">
                    <tr>
                      <th className="py-2 px-3 font-semibold">Light ID</th>
                      <th className="py-2 px-3 font-semibold text-center">Row</th>
                      <th className="py-2 px-3 font-semibold text-center">Column</th>
                      <th className="py-2 px-3 font-semibold text-center">Status</th>
                      <th className="py-2 px-3 font-semibold text-center">Consecutive OFF</th>
                      <th className="py-2 px-3 font-semibold text-center">Confidence</th>
                      <th className="py-2 px-3 font-semibold text-center">Location (BBox)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-red-200 bg-white">
                    {(data.faults && data.faults.length > 0
                      ? data.faults
                      : (data.matrix || []).filter((s: any) => s.is_confirmed || s.status === "OFF")
                    ).map((f: any, idx: number) => (
                      <tr key={idx} className="hover:bg-red-50 transition-colors">
                        <td className="py-2 px-3 font-bold text-red-700">{f.light_id}</td>
                        <td className="py-2 px-3 text-center text-[#111827]">Row {f.row_id}</td>
                        <td className="py-2 px-3 text-center text-[#111827]">Col {f.column_id}</td>
                        <td className="py-2 px-3 text-center">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700">
                            FAULT (OFF)
                          </span>
                        </td>
                        <td className="py-2 px-3 text-center font-bold text-red-600">
                          {f.consecutive_off ?? "≥5"} frames
                        </td>
                        <td className="py-2 px-3 text-center text-[#111827]">
                          {(f.confidence * 100).toFixed(1)}%
                        </td>
                        <td className="py-2 px-3 text-center text-[#5B6472] text-[10px]">
                          {f.bbox ? `[${f.bbox.join(", ")}]` : "Detected"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Row-by-Row Analysis Table for RUNWAY_LIGHT */}
          {data.row_results && data.row_results.length > 0 && (
            <div className="pt-2 border-t border-[#D9DEE7]">
              <div className="text-xs font-bold text-[#111827] uppercase tracking-wider mb-2 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-[#0066FF]" />
                <span>RUNWAY LIGHT ROW-BY-ROW SCAN & FAULT ANALYSIS</span>
              </div>
              <div className="overflow-x-auto rounded-lg border border-[#D9DEE7]">
                <table className="w-full text-left font-mono text-xs">
                  <thead className="bg-[#F5F7FA] text-[#5B6472] border-b border-[#D9DEE7]">
                    <tr>
                      <th className="py-2 px-3 font-semibold">Row</th>
                      <th className="py-2 px-3 font-semibold text-center">Total Lights</th>
                      <th className="py-2 px-3 font-semibold text-center text-[#0066FF]">Lights ON</th>
                      <th className="py-2 px-3 font-semibold text-center text-[#5B6472]">Lights OFF</th>
                      <th className="py-2 px-3 font-semibold text-center text-red-600">Confirmed Faults</th>
                      <th className="py-2 px-3 font-semibold text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D9DEE7] bg-white">
                    {data.row_results.map((r: any, idx: number) => (
                      <tr key={idx} className="hover:bg-[#F0F6FF] transition-colors">
                        <td className="py-2 px-3 font-bold text-[#111827]">{r.row}</td>
                        <td className="py-2 px-3 text-center font-bold text-[#111827]">{r.total}</td>
                        <td className="py-2 px-3 text-center font-bold text-[#0066FF]">{r.on}</td>
                        <td className="py-2 px-3 text-center font-bold text-[#5B6472]">{r.off}</td>
                        <td className={`py-2 px-3 text-center font-bold ${r.faults > 0 ? "text-red-600 bg-red-50" : "text-[#5B6472]"}`}>{r.faults}</td>
                        <td className="py-2 px-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${r.faults > 0 ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"}`}>
                            {r.faults > 0 ? "FAULT" : "NORMAL"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Video Review Workspace with Player, Seek, and Detections (FR-05, FR-06, FR-07, FR-08) */}
      {data.media_type === "VIDEO" && (
        <div className="pt-2 border-t border-[#D9DEE7]">
          <OfflineVideoReviewWorkspace
            jobId={jobId}
            filename={data.filename || data.video_name || "offline_video.mp4"}
            mediaType={data.media_type || "VIDEO"}
            analysisType={atype}
            modelPath={data.model_path}
            modelVersion={data.model_version}
            confidenceThreshold={data.confidence_threshold}
            totalFrames={data.total_frames || 0}
            processedFrames={data.processed_frames || 0}
            durationSeconds={data.duration_seconds || 0}
            elapsedSeconds={data.elapsed_seconds || 0}
            processingFps={data.processing_fps || 0}
            outcomeStatus={data.outcome_status}
            detections={data.sample_detections || []}
            classCounts={data.class_counts || {}}
            originalVideoUrl={`${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/original`}
            annotatedVideoUrl={analyzedVideoUrl}
            csvReportUrl={csvReportUrl}
            jsonReportUrl={jsonReportUrl}
          />
        </div>
      )}

      {/* Frame Detections Toggle */}
      {data.sample_detections && data.sample_detections.length > 0 && (
        <div className="pt-2 border-t border-[#D9DEE7]">
          <button
            onClick={() => setShowDetectionSamples(!showDetectionSamples)}
            className="flex items-center space-x-1.5 text-xs text-[#5B6472] hover:text-[#0066FF] transition-colors"
          >
            <span>{showDetectionSamples ? "Hide" : "Show"} Frame-by-Frame Detection Log ({data.sample_detections.length} sampled)</span>
            <svg
              className={`w-3.5 h-3.5 transform transition-transform ${showDetectionSamples ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showDetectionSamples && (
            <div className="mt-2 max-h-60 overflow-y-auto rounded border border-[#D9DEE7] bg-[#FFFFFF] p-2 text-[11px]">
              <table className="w-full text-left font-mono">
                <thead>
                  <tr className="text-[#5B6472] border-b border-[#D9DEE7]">
                    <th className="py-1">Model</th>
                    <th className="py-1">Class</th>
                    <th className="py-1">Confidence</th>
                    <th className="py-1">Track ID</th>
                    <th className="py-1">Coordinates</th>
                    <th className="py-1 text-right">Map</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9DEE7]">
                  {data.sample_detections.map((det: any, idx: number) => {
                    const coords = det.debris_coordinates;
                    const lat = coords?.latitude ?? det.latitude;
                    const lon = coords?.longitude ?? det.longitude;
                    const unc = coords?.uncertainty_m ?? det.coordinate_uncertainty_m;
                    const st = (coords?.status ?? det.coordinate_status ?? "unavailable").toLowerCase();
                    const hasCoords = typeof lat === "number" && typeof lon === "number" && !isNaN(lat) && !isNaN(lon) && st !== "unavailable";

                    return (
                      <tr key={idx} className="text-[#111827] hover:bg-[#F0F6FF]">
                        <td className="py-1 uppercase text-[#5B6472]">{det.model || "yolo"}</td>
                        <td className="py-1 font-bold text-[#0066FF]">{det.class_name}</td>
                        <td className="py-1 text-[#0066FF]">{(det.confidence * 100).toFixed(1)}%</td>
                        <td className="py-1 text-[#5B6472]">#{det.track_id ?? "-"}</td>
                        <td className="py-1 text-[10px]">
                          {hasCoords ? (
                            <span className="text-[#111827] font-semibold">
                              {lat.toFixed(5)}°, {lon.toFixed(5)}° (±{(unc ?? 1.5).toFixed(1)}m)
                            </span>
                          ) : (
                            <span className="text-[#5B6472] italic">Unavailable</span>
                          )}
                        </td>
                        <td className="py-1 text-right">
                          <button
                            onClick={() => setSelectedDebrisForMap(det)}
                            className="px-2 py-0.5 rounded text-[10px] bg-[#F5F7FA] hover:bg-[#EAF3FF] hover:text-[#0066FF] border border-[#D9DEE7] text-[#5B6472] font-semibold inline-flex items-center space-x-1"
                            title="Inspect on map"
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
          )}
        </div>
      )}

      {/* Reusable Debris Location Map Modal (FR-08) */}
      <DebrisLocationMapModal
        isOpen={!!selectedDebrisForMap}
        onClose={() => setSelectedDebrisForMap(null)}
        detection={selectedDebrisForMap}
        droneTelemetry={data.drone_telemetry}
      />
    </div>
  );
};
