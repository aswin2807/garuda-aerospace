"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Download,
  ExternalLink,
  FileCode,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Lightbulb,
  ShieldAlert,
  Navigation as NavIcon,
  Video,
  Image as ImageIcon,
  Layers,
  RefreshCw,
  Eye,
  Hash,
} from "lucide-react";

import { TopBar } from "../../../components/hud/TopBar";
import { Sidebar } from "../../../components/hud/Sidebar";
import {
  getAnalysisResults,
  getMissionReport,
  getAnalyzedMediaUrl,
  getOriginalMediaUrl,
} from "../../../lib/api";
import { useAnalysisStore } from "../../../stores/analysisStore";

export default function HistoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const setActiveJob = useAnalysisStore((s) => s.setActiveJob);
  const setAnalysisType = useAnalysisStore((s) => s.setAnalysisType);

  const [record, setRecord] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeMediaTab, setActiveMediaTab] = useState<"ANNOTATED" | "ORIGINAL">("ANNOTATED");
  const [originalMediaError, setOriginalMediaError] = useState<boolean>(false);
  const [annotatedMediaError, setAnnotatedMediaError] = useState<boolean>(false);

  const loadRecord = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setOriginalMediaError(false);
    setAnnotatedMediaError(false);

    try {
      // First try analysis results
      const data = await getAnalysisResults(id);
      setRecord(data);
    } catch (err: any) {
      // If failed, try mission report
      try {
        const mData = await getMissionReport(id);
        setRecord({
          id: mData.mission_id,
          job_id: mData.mission_id,
          filename: mData.name,
          media_type: "LIVE_MISSION",
          analysis_type: "SURVEY",
          status: mData.status,
          total_frames: 0,
          processed_frames: 0,
          duration_seconds: 0,
          nav_count: 0,
          fod_count: 0,
          light_on_count: 0,
          light_off_count: 0,
          confirmed_faults: 0,
          created_at: mData.created_at,
          started_at: mData.start_time,
          completed_at: mData.end_time,
          sample_detections: [],
        });
      } catch (err2: any) {
        setError(err.message || "Failed to retrieve history audit record from backend.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecord();
  }, [id]);

  const handleOpenInAnalysis = () => {
    if (!record) return;
    const mod = record.analysis_type || "NAVIGATION";
    setAnalysisType(mod);
    setActiveJob({
      id: record.id || record.job_id,
      job_id: record.id || record.job_id,
      filename: record.filename || record.video_name,
      analysis_type: mod,
      media_type: record.media_type || "VIDEO",
      status: record.status,
      progress: 100,
      processed_frames: record.processed_frames || 0,
      total_frames: record.total_frames || 0,
      nav_count: record.nav_count || 0,
      fod_count: record.fod_count || 0,
      light_on_count: record.light_on_count || 0,
      light_off_count: record.light_off_count || 0,
      confirmed_faults: record.confirmed_faults || 0,
      duration_seconds: record.duration_seconds || 0,
      video_fps: record.video_fps || 30,
      processing_fps: record.processing_fps || 30,
      elapsed_seconds: record.duration_seconds || 0,
      remaining_seconds: 0,
    });
    router.push("/analysis");
  };

  const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const isVideo = (record?.media_type || "").toUpperCase() === "VIDEO";
  const mod = (record?.analysis_type || "NAVIGATION").toUpperCase();
  const isCompleted = record?.status === "COMPLETED";
  const isFailed = record?.status === "FAILED";

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 flex flex-col overflow-y-auto bg-[#F5F7FA] p-6 font-mono text-xs">
          {/* Top Breadcrumb & Actions Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#D9DEE7] mb-6">
            <div className="flex items-center space-x-3">
              <Link
                href="/history"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827] transition font-semibold"
              >
                <ArrowLeft className="w-3.5 h-3.5 text-[#0066FF]" />
                <span>Back to History</span>
              </Link>

              <div className="h-4 w-px bg-[#D9DEE7]" />

              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-base font-bold text-[#111827] tracking-wider uppercase">
                    ANALYSIS AUDIT RECORD: <span className="text-[#0066FF]">{id}</span>
                  </h1>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${
                      mod === "NAVIGATION"
                        ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/30"
                        : mod === "FOD"
                        ? "bg-amber-50 text-amber-700 border-amber-300"
                        : mod === "RUNWAY_LIGHT"
                        ? "bg-indigo-50 text-indigo-700 border-indigo-300"
                        : "bg-[#F5F7FA] text-[#5B6472] border-[#D9DEE7]"
                    }`}
                  >
                    {mod.replace("_", " ")}
                  </span>
                </div>
                <p className="text-[#5B6472] text-[11px] mt-0.5">
                  Verified immutable inspection audit loaded directly from database storage
                </p>
              </div>
            </div>

            {record && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleOpenInAnalysis}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#EAF3FF] hover:bg-[#0066FF] text-[#0066FF] hover:text-white transition font-semibold border border-[#0066FF]/30"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open in Workspace</span>
                </button>

                {isCompleted && (
                  <>
                    <a
                      href={`${getApiUrl()}/api/v1/analysis/${record.id || record.job_id}/report?format=csv`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827] transition font-semibold"
                    >
                      <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Export CSV</span>
                    </a>
                    <a
                      href={`${getApiUrl()}/api/v1/analysis/${record.id || record.job_id}/report?format=json`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827] transition font-semibold"
                    >
                      <FileCode className="w-3.5 h-3.5 text-[#0066FF]" />
                      <span>Export JSON</span>
                    </a>
                  </>
                )}
              </div>
            )}
          </div>

          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl">
              <RefreshCw className="w-8 h-8 animate-spin text-[#0066FF] mb-3" />
              <div className="text-sm font-bold text-[#111827]">
                Retrieving persistent audit record...
              </div>
              <div className="text-xs text-[#5B6472] mt-1">
                Reading database records and model detection outputs
              </div>
            </div>
          ) : error || !record ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-[#FFFFFF] border border-red-200 rounded-xl">
              <AlertCircle className="w-10 h-10 text-red-500 mb-3" />
              <div className="text-base font-bold text-red-700">Audit Record Unavailable</div>
              <div className="text-xs text-[#5B6472] mt-1 max-w-md text-center">
                {error || "Could not locate this analysis job in persistent storage."}
              </div>
              <div className="flex items-center space-x-3 mt-4">
                <button
                  onClick={loadRecord}
                  className="px-4 py-2 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] text-white font-semibold transition"
                >
                  Retry Retrieval
                </button>
                <Link
                  href="/history"
                  className="px-4 py-2 rounded-lg bg-[#F5F7FA] border border-[#D9DEE7] text-[#111827] font-semibold transition hover:bg-[#EAF3FF]"
                >
                  Return to History
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Failure Alert Banner if FAILED */}
              {(isFailed || record.error_message) && (
                <div className="p-4 rounded-xl bg-red-50 border border-red-300 text-red-800 flex items-start space-x-3">
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-sm uppercase">Job Execution Failure Recorded</div>
                    <div className="text-xs text-red-700 mt-1">
                      {record.error_message || "Analysis failed during processing. No valid inference output generated."}
                    </div>
                  </div>
                </div>
              )}

              {/* Overview Metadata Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
                  <div className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider mb-1">
                    Input Source
                  </div>
                  <div className="text-sm font-bold text-[#111827] truncate" title={record.filename}>
                    {record.filename || record.video_name}
                  </div>
                  <div className="text-[10px] text-[#5B6472] mt-1 flex items-center gap-1">
                    {isVideo ? <Video className="w-3 h-3 text-[#0066FF]" /> : <ImageIcon className="w-3 h-3 text-[#0066FF]" />}
                    <span>{record.media_type || "VIDEO"}</span>
                  </div>
                </div>

                <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
                  <div className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider mb-1">
                    Execution Status
                  </div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-bold ${
                        isCompleted
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-300"
                          : record.status === "ANALYZING"
                          ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30"
                          : isFailed
                          ? "bg-red-50 text-red-600 border border-red-300"
                          : "bg-[#F5F7FA] text-[#5B6472] border border-[#D9DEE7]"
                      }`}
                    >
                      {record.status}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#5B6472] mt-1">
                    Frames: {record.processed_frames} / {record.total_frames || "--"}
                  </div>
                </div>

                <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
                  <div className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider mb-1">
                    Timestamps & Duration
                  </div>
                  <div className="text-xs font-semibold text-[#111827]">
                    {record.duration_seconds ? `${record.duration_seconds.toFixed(1)}s Duration` : record.processing_time_formatted || "--"}
                  </div>
                  <div className="text-[10px] text-[#5B6472] mt-1 truncate" title={record.created_at}>
                    Created: {record.created_at ? new Date(record.created_at).toLocaleString() : "--"}
                  </div>
                </div>

                <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
                  <div className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider mb-1">
                    Inference Performance
                  </div>
                  <div className="text-xs font-bold text-[#0066FF]">
                    {record.avg_confidence ? `${(record.avg_confidence * 100).toFixed(1)}% Avg Conf` : "Conf: N/A"}
                  </div>
                  <div className="text-[10px] text-[#5B6472] mt-1">
                    Speed: {record.avg_inference_ms ? `${record.avg_inference_ms.toFixed(1)}ms / frame` : "--"}
                  </div>
                </div>
              </div>

              {/* Module-Specific Detection Summary Card */}
              <div className="p-5 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-[#D9DEE7] mb-4">
                  <div className="flex items-center space-x-2">
                    {mod === "NAVIGATION" && <NavIcon className="w-4 h-4 text-[#0066FF]" />}
                    {mod === "FOD" && <ShieldAlert className="w-4 h-4 text-amber-500" />}
                    {mod === "RUNWAY_LIGHT" && <Lightbulb className="w-4 h-4 text-[#0066FF]" />}
                    <h2 className="text-sm font-bold text-[#111827] uppercase tracking-wider">
                      Verified AI Detections Summary
                    </h2>
                  </div>
                  <span className="text-[10px] text-[#5B6472] font-semibold">
                    Model: {mod === "NAVIGATION" ? "navigation_best.pt" : mod === "FOD" ? "FOD_Karhtikeyan.pt" : "runway_light_best.pt"}
                  </span>
                </div>

                {mod === "NAVIGATION" && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                      <div className="text-[10px] text-[#5B6472] uppercase font-bold">Total Nav Objects</div>
                      <div className="text-xl font-bold text-[#0066FF] mt-1">{record.nav_count}</div>
                    </div>
                    <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                      <div className="text-[10px] text-[#5B6472] uppercase font-bold">Unique Tracked Objects</div>
                      <div className="text-xl font-bold text-[#111827] mt-1">{record.unique_nav_count || record.nav_count}</div>
                    </div>
                    <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                      <div className="text-[10px] text-[#5B6472] uppercase font-bold">Model Confidence</div>
                      <div className="text-xl font-bold text-emerald-600 mt-1">
                        {record.avg_confidence ? `${(record.avg_confidence * 100).toFixed(1)}%` : "N/A"}
                      </div>
                    </div>
                  </div>
                )}

                {mod === "FOD" && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                      <div className="text-[10px] text-[#5B6472] uppercase font-bold">Total Debris Detections</div>
                      <div className="text-xl font-bold text-amber-700 mt-1">{record.fod_count}</div>
                    </div>
                    <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                      <div className="text-[10px] text-[#5B6472] uppercase font-bold">Unique Debris Items</div>
                      <div className="text-xl font-bold text-[#111827] mt-1">{record.unique_fod_count || record.fod_count}</div>
                    </div>
                    <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                      <div className="text-[10px] text-[#5B6472] uppercase font-bold">Detection Confidence</div>
                      <div className="text-xl font-bold text-emerald-600 mt-1">
                        {record.avg_confidence ? `${(record.avg_confidence * 100).toFixed(1)}%` : "N/A"}
                      </div>
                    </div>
                  </div>
                )}

                {mod === "RUNWAY_LIGHT" && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                        <div className="text-[10px] text-[#5B6472] uppercase font-bold">Lights ON</div>
                        <div className="text-xl font-bold text-[#0066FF] mt-1">{record.light_on_count}</div>
                      </div>
                      <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                        <div className="text-[10px] text-[#5B6472] uppercase font-bold">Lights OFF</div>
                        <div className="text-xl font-bold text-[#5B6472] mt-1">{record.light_off_count}</div>
                      </div>
                      <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                        <div className="text-[10px] text-[#5B6472] uppercase font-bold">Confirmed Faults</div>
                        <div className="text-xl font-bold text-rose-600 mt-1">{record.confirmed_faults}</div>
                      </div>
                      <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                        <div className="text-[10px] text-[#5B6472] uppercase font-bold">Unknown Lights</div>
                        <div className="text-xl font-bold text-[#111827] mt-1">{record.unknown_light_count || 0}</div>
                      </div>
                      <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#D9DEE7]">
                        <div className="text-[10px] text-[#5B6472] uppercase font-bold">Rows Analyzed</div>
                        <div className="text-xl font-bold text-[#0066FF] mt-1">{record.rows_detected || 0}</div>
                      </div>
                    </div>

                    {record.row_results && record.row_results.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-[#D9DEE7]">
                        <div className="text-xs font-bold text-[#111827] mb-2 uppercase">
                          Structured Runway Grid Breakdown
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs border border-[#D9DEE7]">
                            <thead className="bg-[#F5F7FA] text-[10px] text-[#5B6472] uppercase">
                              <tr>
                                <th className="p-2 border-b border-[#D9DEE7]">Row #</th>
                                <th className="p-2 border-b border-[#D9DEE7]">Total Lights</th>
                                <th className="p-2 border-b border-[#D9DEE7]">ON</th>
                                <th className="p-2 border-b border-[#D9DEE7]">OFF</th>
                                <th className="p-2 border-b border-[#D9DEE7]">Fault Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#D9DEE7]">
                              {record.row_results.map((row: any, i: number) => (
                                <tr key={i} className="hover:bg-[#F0F6FF]">
                                  <td className="p-2 font-bold text-[#0066FF]">Row {row.row_idx !== undefined ? row.row_idx + 1 : i + 1}</td>
                                  <td className="p-2">{row.total_lights || row.lights_count || (row.on_count + row.off_count)}</td>
                                  <td className="p-2 text-[#0066FF] font-semibold">{row.on_count || 0}</td>
                                  <td className="p-2 text-[#5B6472]">{row.off_count || 0}</td>
                                  <td className="p-2">
                                    {(row.fault_count || 0) > 0 ? (
                                      <span className="text-rose-600 font-bold">⚠ {row.fault_count} FAULT(S)</span>
                                    ) : (
                                      <span className="text-emerald-600 font-semibold">NORMAL</span>
                                    )}
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
              </div>

              {/* Media Display Section (Original vs Annotated) */}
              <div className="p-5 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-[#D9DEE7] mb-4">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setActiveMediaTab("ANNOTATED")}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                        activeMediaTab === "ANNOTATED"
                          ? "bg-[#0066FF] text-white"
                          : "bg-[#F5F7FA] text-[#5B6472] hover:bg-[#EAF3FF] hover:text-[#0066FF]"
                      }`}
                    >
                      Saved Annotated Output
                    </button>
                    <button
                      onClick={() => setActiveMediaTab("ORIGINAL")}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                        activeMediaTab === "ORIGINAL"
                          ? "bg-[#0066FF] text-white"
                          : "bg-[#F5F7FA] text-[#5B6472] hover:bg-[#EAF3FF] hover:text-[#0066FF]"
                      }`}
                    >
                      Original Input Media
                    </button>
                  </div>
                  <span className="text-[11px] text-[#5B6472]">
                    Job ID: {record.id || record.job_id}
                  </span>
                </div>

                <div className="aspect-video w-full bg-[#0A0A0A] rounded-lg overflow-hidden flex items-center justify-center relative border border-[#D9DEE7]">
                  {activeMediaTab === "ANNOTATED" ? (
                    annotatedMediaError ? (
                      <div className="text-center p-6 text-[#B8B8B8]">
                        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
                        <div className="font-semibold text-xs text-white">Annotated Media Unavailable</div>
                        <div className="text-[11px] mt-1 text-[#888888]">
                          {isCompleted
                            ? "Annotated media file was not retained on disk."
                            : "Annotated media is generated only upon completed analysis."}
                        </div>
                      </div>
                    ) : isVideo ? (
                      <video
                        controls
                        src={getAnalyzedMediaUrl(record.id || record.job_id)}
                        onError={() => setAnnotatedMediaError(true)}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <img
                        src={getAnalyzedMediaUrl(record.id || record.job_id)}
                        alt="Annotated Analysis Output"
                        onError={() => setAnnotatedMediaError(true)}
                        className="w-full h-full object-contain"
                      />
                    )
                  ) : (
                    originalMediaError ? (
                      <div className="text-center p-6 text-[#B8B8B8]">
                        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-amber-500" />
                        <div className="font-semibold text-xs text-white">Original File Not Retained</div>
                        <div className="text-[11px] mt-1 text-[#888888]">
                          The original uploaded media was cleaned up or is not present on disk.
                        </div>
                      </div>
                    ) : isVideo ? (
                      <video
                        controls
                        src={getOriginalMediaUrl(record.id || record.job_id)}
                        onError={() => setOriginalMediaError(true)}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <img
                        src={getOriginalMediaUrl(record.id || record.job_id)}
                        alt="Original Uploaded Media"
                        onError={() => setOriginalMediaError(true)}
                        className="w-full h-full object-contain"
                      />
                    )
                  )}
                </div>
              </div>

              {/* Genuine Model Predictions & Bounding Boxes Table */}
              <div className="p-5 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-[#D9DEE7] mb-3">
                  <div className="flex items-center space-x-2">
                    <Hash className="w-4 h-4 text-[#0066FF]" />
                    <h2 className="text-sm font-bold text-[#111827] uppercase tracking-wider">
                      Model Detection Records & Confidence Scores
                    </h2>
                  </div>
                  <span className="text-[11px] text-[#5B6472]">
                    {record.sample_detections ? `${record.sample_detections.length} recorded items` : "0 items"}
                  </span>
                </div>

                {record.sample_detections && record.sample_detections.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-[#F5F7FA] border-b border-[#D9DEE7] text-[10px] text-[#5B6472] uppercase font-bold tracking-wider">
                          <th className="py-2.5 px-3">Frame #</th>
                          <th className="py-2.5 px-3">Class Detected</th>
                          <th className="py-2.5 px-3">Confidence</th>
                          <th className="py-2.5 px-3">Bounding Box [x1, y1, x2, y2]</th>
                          <th className="py-2.5 px-3">Track ID</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9DEE7] text-xs">
                        {record.sample_detections.map((det: any, idx: number) => (
                          <tr key={idx} className="hover:bg-[#F0F6FF]">
                            <td className="py-2.5 px-3 font-mono text-[#5B6472]">
                              Frame {det.frame !== undefined ? det.frame : "--"}
                            </td>
                            <td className="py-2.5 px-3 font-bold text-[#111827]">
                              {det.class_name}
                            </td>
                            <td className="py-2.5 px-3">
                              <span className="font-mono font-bold text-[#0066FF]">
                                {det.confidence ? `${(det.confidence * 100).toFixed(1)}%` : "--"}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-[#5B6472]">
                              {det.bbox
                                ? `[${det.bbox.map((n: number) => Math.round(n)).join(", ")}]`
                                : "--"}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-[#111827]">
                              {det.track_id !== undefined ? `#${det.track_id}` : "--"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="py-8 text-center text-[#5B6472]">
                    <div className="font-semibold text-xs">
                      {isCompleted
                        ? "Zero detections recorded for this analysis."
                        : "Results unavailable for this record."}
                    </div>
                    <p className="text-[11px] text-[#5B6472]/70 mt-1">
                      No synthetic detections are injected. All outputs reflect actual model inferences.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
