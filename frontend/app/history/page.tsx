"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  History,
  Search,
  Filter,
  Download,
  ExternalLink,
  RefreshCw,
  FileSpreadsheet,
  FileCode,
  ShieldAlert,
  Lightbulb,
  Navigation as NavIcon,
  CheckCircle2,
  Clock,
  AlertCircle,
  Calendar,
  Eye,
} from "lucide-react";

import { TopBar } from "../../components/hud/TopBar";
import { Sidebar } from "../../components/hud/Sidebar";
import { getCommandCentreRecentMissions } from "../../lib/api";
import { useAnalysisStore } from "../../stores/analysisStore";

export default function HistoryPage() {
  const router = useRouter();
  const setActiveJob = useAnalysisStore((s) => s.setActiveJob);
  const setAnalysisType = useAnalysisStore((s) => s.setAnalysisType);

  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [moduleFilter, setModuleFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [dateRangeFilter, setDateRangeFilter] = useState<string>("ALL");
  const [customStartDate, setCustomStartDate] = useState<string>("");
  const [customEndDate, setCustomEndDate] = useState<string>("");

  const loadRecords = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const data = await getCommandCentreRecentMissions(100);
      setRecords(data || []);
    } catch (err: any) {
      console.error("Failed to load history records:", err);
      setFetchError(err.message || "Failed to connect to backend server. Could not load audit history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  const filteredRecords = useMemo(() => {
    const now = new Date();

    return records.filter((r) => {
      // Search matching
      const matchesSearch =
        searchTerm === "" ||
        (r.name && r.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (r.id && r.id.toLowerCase().includes(searchTerm.toLowerCase()));

      // Module matching
      const matchesModule =
        moduleFilter === "ALL" ||
        (r.analysis_type && r.analysis_type.toUpperCase() === moduleFilter.toUpperCase());

      // Status matching
      const matchesStatus =
        statusFilter === "ALL" ||
        (r.status && r.status.toUpperCase() === statusFilter.toUpperCase());

      // Date Range matching
      let matchesDate = true;
      if (r.created_at) {
        const itemDate = new Date(r.created_at);

        if (dateRangeFilter === "TODAY") {
          matchesDate = itemDate.toDateString() === now.toDateString();
        } else if (dateRangeFilter === "LAST_7_DAYS") {
          const sevenDaysAgo = new Date();
          sevenDaysAgo.setDate(now.getDate() - 7);
          matchesDate = itemDate >= sevenDaysAgo;
        } else if (dateRangeFilter === "LAST_30_DAYS") {
          const thirtyDaysAgo = new Date();
          thirtyDaysAgo.setDate(now.getDate() - 30);
          matchesDate = itemDate >= thirtyDaysAgo;
        } else if (dateRangeFilter === "CUSTOM") {
          if (customStartDate) {
            const start = new Date(customStartDate);
            start.setHours(0, 0, 0, 0);
            if (itemDate < start) matchesDate = false;
          }
          if (customEndDate) {
            const end = new Date(customEndDate);
            end.setHours(23, 59, 59, 999);
            if (itemDate > end) matchesDate = false;
          }
        }
      }

      return matchesSearch && matchesModule && matchesStatus && matchesDate;
    });
  }, [records, searchTerm, moduleFilter, statusFilter, dateRangeFilter, customStartDate, customEndDate]);

  // Aggregate stats from real records
  const stats = useMemo(() => {
    let totalNav = 0;
    let totalFod = 0;
    let totalLightsOn = 0;
    let totalLightsOff = 0;
    let totalFaults = 0;

    records.forEach((r) => {
      totalNav += r.nav_count || 0;
      totalFod += r.fod_count || 0;
      totalLightsOn += r.light_on_count || 0;
      totalLightsOff += r.light_off_count || 0;
      totalFaults += r.confirmed_faults || 0;
    });

    return {
      totalRecords: records.length,
      totalNav,
      totalFod,
      totalLightsOn,
      totalLightsOff,
      totalFaults,
    };
  }, [records]);

  const handleOpenInAnalysis = (record: any) => {
    if (record.analysis_type) {
      setAnalysisType(record.analysis_type);
      setActiveJob({
        id: record.id,
        job_id: record.id,
        filename: record.name,
        analysis_type: record.analysis_type,
        media_type: record.media_type,
        status: record.status,
        progress: record.progress || 100,
        processed_frames: record.processed_frames || 0,
        total_frames: record.total_frames || 0,
        nav_count: record.nav_count || 0,
        fod_count: record.fod_count || 0,
        light_on_count: record.light_on_count || 0,
        light_off_count: record.light_off_count || 0,
        confirmed_faults: record.confirmed_faults || 0,
        duration_seconds: record.duration_seconds || 0,
        video_fps: 30,
        processing_fps: 30,
        elapsed_seconds: record.duration_seconds || 0,
        remaining_seconds: 0,
      });
      router.push("/analysis");
    }
  };

  const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 flex flex-col overflow-y-auto bg-[#F5F7FA] p-6 font-mono text-xs">
          {/* Page Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#D9DEE7] mb-6">
            <div>
              <div className="flex items-center space-x-2">
                <History className="w-5 h-5 text-[#0066FF]" />
                <h1 className="text-lg font-bold tracking-wider text-[#111827] uppercase">
                  ANALYSIS & MISSION AUDIT HISTORY
                </h1>
              </div>
              <p className="text-[#5B6472] text-xs mt-1">
                Persistent database records, genuine model inference audits, and certified exportable reports
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={loadRecords}
                disabled={loading}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827] transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-[#0066FF]" : ""}`} />
                <span>Refresh</span>
              </button>

              <Link
                href="/analysis"
                className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] text-white font-semibold transition shadow-sm shadow-[#0066FF]/20"
              >
                <span>+ New Analysis</span>
              </Link>
            </div>
          </div>

          {/* Aggregate Telemetry & Detection Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
              <div className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider mb-1">
                Total Persisted Jobs
              </div>
              <div className="text-2xl font-black text-[#111827]">{stats.totalRecords}</div>
              <div className="text-[10px] text-[#0066FF] mt-1 font-semibold">Verified Database Records</div>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider">
                  Navigation Objects
                </span>
                <NavIcon className="w-3.5 h-3.5 text-[#0066FF]" />
              </div>
              <div className="text-2xl font-black text-[#0066FF]">{stats.totalNav}</div>
              <div className="text-[10px] text-[#5B6472] mt-1">navigation_best.pt verified</div>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider">
                  FOD Debris Detections
                </span>
                <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
              </div>
              <div className="text-2xl font-black text-[#111827]">{stats.totalFod}</div>
              <div className="text-[10px] text-amber-700 mt-1 font-semibold">FOD_Karhtikeyan.pt verified</div>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-[#5B6472] uppercase font-bold tracking-wider">
                  Runway Lights & Faults
                </span>
                <Lightbulb className="w-3.5 h-3.5 text-[#0066FF]" />
              </div>
              <div className="text-2xl font-black text-[#111827]">
                {stats.totalLightsOn + stats.totalLightsOff}{" "}
                {stats.totalFaults > 0 && (
                  <span className="text-sm font-bold text-red-600">({stats.totalFaults} Faults)</span>
                )}
              </div>
              <div className="text-[10px] text-[#5B6472] mt-1">
                ON: {stats.totalLightsOn} | OFF: {stats.totalLightsOff}
              </div>
            </div>
          </div>

          {/* Search & Filters Bar */}
          <div className="p-3 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl mb-4 shadow-sm flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center space-x-2 flex-1 min-w-[200px]">
                <Search className="w-4 h-4 text-[#5B6472]" />
                <input
                  type="text"
                  placeholder="Search by job ID or source filename..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg px-3 py-1.5 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF]"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* Module Filter */}
                <div className="flex items-center space-x-1.5">
                  <span className="text-[10px] text-[#5B6472] uppercase font-bold">Module:</span>
                  <select
                    value={moduleFilter}
                    onChange={(e) => setModuleFilter(e.target.value)}
                    className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg px-2.5 py-1.5 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF]"
                  >
                    <option value="ALL">All Modules</option>
                    <option value="NAVIGATION">Navigation</option>
                    <option value="FOD">FOD Debris</option>
                    <option value="RUNWAY_LIGHT">Runway Light</option>
                    <option value="SURVEY">Flight Survey</option>
                  </select>
                </div>

                {/* Status Filter */}
                <div className="flex items-center space-x-1.5">
                  <span className="text-[10px] text-[#5B6472] uppercase font-bold">Status:</span>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg px-2.5 py-1.5 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF]"
                  >
                    <option value="ALL">All Statuses</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="ANALYZING">Analyzing</option>
                    <option value="QUEUED">Queued / Paused</option>
                    <option value="FAILED">Failed</option>
                  </select>
                </div>

                {/* Date Range Filter */}
                <div className="flex items-center space-x-1.5">
                  <span className="text-[10px] text-[#5B6472] uppercase font-bold">Date Range:</span>
                  <select
                    value={dateRangeFilter}
                    onChange={(e) => setDateRangeFilter(e.target.value)}
                    className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg px-2.5 py-1.5 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF]"
                  >
                    <option value="ALL">All Dates</option>
                    <option value="TODAY">Today</option>
                    <option value="LAST_7_DAYS">Last 7 Days</option>
                    <option value="LAST_30_DAYS">Last 30 Days</option>
                    <option value="CUSTOM">Custom Range</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Custom Date Inputs if CUSTOM selected */}
            {dateRangeFilter === "CUSTOM" && (
              <div className="flex items-center space-x-3 pt-2 border-t border-[#D9DEE7] text-[11px]">
                <span className="text-[#5B6472] font-semibold">From:</span>
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => setCustomStartDate(e.target.value)}
                  className="bg-[#F5F7FA] border border-[#D9DEE7] rounded px-2 py-1 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF]"
                />
                <span className="text-[#5B6472] font-semibold">To:</span>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => setCustomEndDate(e.target.value)}
                  className="bg-[#F5F7FA] border border-[#D9DEE7] rounded px-2 py-1 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF]"
                />
                {(customStartDate || customEndDate) && (
                  <button
                    onClick={() => {
                      setCustomStartDate("");
                      setCustomEndDate("");
                    }}
                    className="text-[#0066FF] hover:underline text-[10px]"
                  >
                    Clear Dates
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Backend Error State */}
          {fetchError && (
            <div className="mb-4 p-4 rounded-xl bg-red-50 border border-red-300 text-red-800 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <div>
                  <div className="font-bold text-xs uppercase">Backend Communication Error</div>
                  <div className="text-[11px] text-red-700">{fetchError}</div>
                </div>
              </div>
              <button
                onClick={loadRecords}
                className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs transition"
              >
                Retry
              </button>
            </div>
          )}

          {/* Audit Records Table */}
          <div className="flex-1 bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl overflow-hidden shadow-sm flex flex-col">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#F5F7FA] border-b border-[#D9DEE7] text-[10px] text-[#5B6472] uppercase font-bold tracking-wider">
                    <th className="py-3 px-4">Analysis ID</th>
                    <th className="py-3 px-4">Module</th>
                    <th className="py-3 px-4">Source / Filename</th>
                    <th className="py-3 px-4">Date & Time</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Verified Detections</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9DEE7]">
                  {loading ? (
                    <tr>
                      <td colSpan={8} className="py-12 text-center text-[#5B6472]">
                        <div className="flex items-center justify-center space-x-2">
                          <RefreshCw className="w-4 h-4 animate-spin text-[#0066FF]" />
                          <span>Loading audit records from database...</span>
                        </div>
                      </td>
                    </tr>
                  ) : filteredRecords.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-16 text-center text-[#5B6472]">
                        <div className="flex flex-col items-center justify-center space-y-3">
                          <History className="w-8 h-8 text-[#5B6472]/40" />
                          <div className="font-semibold text-sm text-[#111827]">
                            No analysis history available. Upload a file and run an analysis to get started.
                          </div>
                          <Link
                            href="/analysis"
                            className="px-4 py-2 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] text-white font-semibold transition text-xs"
                          >
                            Upload & Analyze Now
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredRecords.map((r) => {
                      const mod = (r.analysis_type || "NAVIGATION").toUpperCase();
                      const isCompleted = r.status === "COMPLETED";

                      return (
                        <tr
                          key={r.id}
                          className="hover:bg-[#F0F6FF] transition-colors group text-xs text-[#111827]"
                        >
                          <td className="py-3 px-4 font-mono font-bold text-[#0066FF]">
                            <Link
                              href={`/history/${r.id}`}
                              className="hover:underline"
                              title="View full audit details"
                            >
                              {r.id.slice(0, 12)}...
                            </Link>
                          </td>
                          <td className="py-3 px-4">
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
                          </td>
                          <td className="py-3 px-4 truncate max-w-[200px] font-semibold" title={r.name}>
                            {r.name}
                          </td>
                          <td className="py-3 px-4 text-[11px] text-[#5B6472]">
                            {r.created_at ? new Date(r.created_at).toLocaleString() : "--"}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                isCompleted
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-300"
                                  : r.status === "ANALYZING"
                                  ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30 animate-pulse"
                                  : r.status === "FAILED"
                                  ? "bg-red-50 text-red-600 border border-red-300"
                                  : "bg-[#F5F7FA] text-[#5B6472] border border-[#D9DEE7]"
                              }`}
                            >
                              {r.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-[11px]">
                            {mod === "NAVIGATION" && (
                              <span className="text-[#0066FF] font-semibold">
                                {r.nav_count} Nav Objects
                              </span>
                            )}
                            {mod === "FOD" && (
                              <span className="text-amber-700 font-semibold">
                                {r.fod_count} FOD Debris
                              </span>
                            )}
                            {mod === "RUNWAY_LIGHT" && (
                              <span>
                                <span className="text-[#0066FF] font-semibold">ON: {r.light_on_count}</span>
                                {" • "}
                                <span className="text-[#5B6472]">OFF: {r.light_off_count}</span>
                                {r.confirmed_faults > 0 && (
                                  <span className="text-rose-600 font-bold ml-1">
                                    ({r.confirmed_faults} Faults)
                                  </span>
                                )}
                              </span>
                            )}
                            {mod === "SURVEY" && (
                              <span className="text-[#5B6472]">Flight Waypoint Survey</span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-[11px] text-[#5B6472]">
                            {r.duration_seconds ? `${r.duration_seconds.toFixed(1)}s` : "--"}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end space-x-2">
                              {/* View Details action */}
                              <Link
                                href={`/history/${r.id}`}
                                title="View Details"
                                className="px-2 py-1 rounded bg-[#F5F7FA] hover:bg-[#EAF3FF] border border-[#D9DEE7] text-[#111827] hover:text-[#0066FF] transition text-[11px] font-semibold flex items-center gap-1"
                              >
                                <Eye className="w-3 h-3" />
                                <span>Details</span>
                              </Link>

                              {/* View Results in Analysis action */}
                              {r.analysis_type && (
                                <button
                                  onClick={() => handleOpenInAnalysis(r)}
                                  title="View in Analysis Workspace"
                                  className="px-2 py-1 rounded bg-[#EAF3FF] hover:bg-[#0066FF] text-[#0066FF] hover:text-white transition text-[11px] font-semibold flex items-center gap-1"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  <span>Results</span>
                                </button>
                              )}

                              {/* Download Reports action */}
                              {isCompleted && (
                                <>
                                  <a
                                    href={`${getApiUrl()}/api/v1/analysis/${r.id}/report?format=csv`}
                                    target="_blank"
                                    rel="noreferrer"
                                    title="Download CSV Audit Report"
                                    className="p-1 rounded bg-[#F5F7FA] hover:bg-[#EAF3FF] border border-[#D9DEE7] text-[#5B6472] hover:text-[#0066FF] transition"
                                  >
                                    <FileSpreadsheet className="w-3.5 h-3.5" />
                                  </a>
                                  <a
                                    href={`${getApiUrl()}/api/v1/analysis/${r.id}/report?format=json`}
                                    target="_blank"
                                    rel="noreferrer"
                                    title="Download JSON Report"
                                    className="p-1 rounded bg-[#F5F7FA] hover:bg-[#EAF3FF] border border-[#D9DEE7] text-[#5B6472] hover:text-[#0066FF] transition"
                                  >
                                    <FileCode className="w-3.5 h-3.5" />
                                  </a>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
