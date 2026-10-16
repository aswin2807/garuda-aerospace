"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Database,
  Search,
  Filter,
  RefreshCw,
  ExternalLink,
  Calendar,
  CheckCircle2,
  Clock,
  AlertCircle,
  XCircle,
  FileText,
  Video,
  Image as ImageIcon,
  ChevronRight,
  ChevronLeft,
  X,
  Download,
  Eye,
  SlidersHorizontal,
  Navigation,
  AlertTriangle,
  Lightbulb,
  Radio,
  MapPin,
} from "lucide-react";
import { TopBar } from "../../components/hud/TopBar";
import { Sidebar } from "../../components/hud/Sidebar";
import { DebrisLocationMapModal } from "../../components/analysis/DebrisLocationMapModal";
import {
  getCentralResults,
  getCentralResultsSummary,
  getCentralResultDetails,
  triggerCentralBackfill,
  CentralResultItem
} from "../../lib/api";

type ModuleFilter = "all" | "navigation" | "rod_debris" | "runway_lights" | "live_surveillance" | "offline_surveillance";
type StatusFilter = "all" | "completed" | "processing" | "queued" | "failed";

export default function CentralResultsPage() {
  const [selectedModule, setSelectedModule] = useState<ModuleFilter>("all");
  const [selectedStatus, setSelectedStatus] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const [resultsData, setResultsData] = useState<{
    total: number;
    items: CentralResultItem[];
    total_pages: number;
  }>({ total: 0, items: [], total_pages: 1 });

  const [summaryData, setSummaryData] = useState<{
    total_results: number;
    by_module: Record<string, number>;
    by_status: Record<string, number>;
    total_events: number;
  }>({
    total_results: 0,
    by_module: { navigation: 0, rod_debris: 0, runway_lights: 0, live_surveillance: 0, offline_surveillance: 0 },
    by_status: { completed: 0, processing: 0, queued: 0, failed: 0 },
    total_events: 0
  });

  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedResult, setSelectedResult] = useState<any | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [selectedDebrisForMap, setSelectedDebrisForMap] = useState<any | null>(null);

  // Fetch summary
  const fetchSummary = useCallback(async () => {
    try {
      const sum = await getCentralResultsSummary();
      setSummaryData(sum);
    } catch (err) {
      console.error("Error fetching results summary:", err);
    }
  }, []);

  // Fetch paginated results
  const fetchResults = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCentralResults({
        module_type: selectedModule !== "all" ? selectedModule : undefined,
        status: selectedStatus !== "all" ? selectedStatus : undefined,
        search: searchQuery.trim() || undefined,
        page,
        page_size: pageSize
      });
      setResultsData({
        total: data.total,
        items: data.items,
        total_pages: data.total_pages
      });
    } catch (err) {
      console.error("Error fetching results:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedModule, selectedStatus, searchQuery, page]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await triggerCentralBackfill();
    await fetchSummary();
    await fetchResults();
  };

  const handleOpenDetails = async (id: string) => {
    setLoadingDetails(true);
    setSelectedResult(null);
    try {
      const det = await getCentralResultDetails(id);
      setSelectedResult(det);
    } catch (err) {
      console.error("Error fetching result details:", err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const getModuleBadge = (mod: string) => {
    const m = (mod || "").toLowerCase();
    switch (m) {
      case "navigation":
        return {
          label: "Navigation",
          icon: <Navigation className="w-3.5 h-3.5 mr-1" />,
          color: "bg-[#E0F2FE] text-[#0284C7] border-[#BAE6FD]"
        };
      case "rod_debris":
      case "fod_debris":
        return {
          label: "Rod Debris (FOD)",
          icon: <AlertTriangle className="w-3.5 h-3.5 mr-1" />,
          color: "bg-[#FEE2E2] text-[#DC2626] border-[#FECACA]"
        };
      case "runway_lights":
      case "runway_light":
        return {
          label: "Runway Lights",
          icon: <Lightbulb className="w-3.5 h-3.5 mr-1" />,
          color: "bg-[#FEF3C7] text-[#D97706] border-[#FDE68A]"
        };
      case "live_surveillance":
        return {
          label: "Live Surveillance",
          icon: <Radio className="w-3.5 h-3.5 mr-1" />,
          color: "bg-[#EAF3FF] text-[#0066FF] border-[#BFDBFE]"
        };
      case "offline_surveillance":
        return {
          label: "Recorded Media",
          icon: <Video className="w-3.5 h-3.5 mr-1" />,
          color: "bg-[#F3E8FF] text-[#7C3AED] border-[#E9D5FF]"
        };
      default:
        return {
          label: mod.toUpperCase(),
          icon: <Database className="w-3.5 h-3.5 mr-1" />,
          color: "bg-[#F1F5F9] text-[#475569] border-[#CBD5E1]"
        };
    }
  };

  const getStatusBadge = (st: string) => {
    const s = (st || "").toLowerCase();
    switch (s) {
      case "completed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            COMPLETED
          </span>
        );
      case "processing":
      case "analyzing":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-[#EAF3FF] text-[#0066FF] border border-[#BFDBFE] animate-pulse">
            <Clock className="w-3 h-3 mr-1" />
            PROCESSING
          </span>
        );
      case "queued":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]">
            <Clock className="w-3 h-3 mr-1" />
            QUEUED
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]">
            <XCircle className="w-3 h-3 mr-1" />
            FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-700">
            {st.toUpperCase()}
          </span>
        );
    }
  };

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return "N/A";
    try {
      const d = new Date(isoStr);
      return d.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      {/* Top Header */}
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Central Results Workspace */}
        <main className="flex-1 flex flex-col overflow-y-auto bg-[#F5F7FA]">
          {/* Page Top Title Bar */}
          <div className="px-6 py-3 bg-[#FFFFFF] border-b border-[#D9DEE7] flex items-center justify-between font-mono text-xs">
            <div className="flex items-center space-x-3">
              <span className="w-2.5 h-2.5 rounded-full bg-[#0066FF]" />
              <span className="font-bold text-[#111827] uppercase tracking-wider text-sm flex items-center">
                <Database className="w-4 h-4 mr-2 text-[#0066FF]" />
                Centralized Results Management System
              </span>
              <span className="text-[10px] text-[#0066FF] px-2 py-0.5 rounded bg-[#EAF3FF] border border-[#0066FF]/20 font-bold">
                POSTGRESQL / SQLITE UNIFIED REPOSITORY
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[#FFFFFF] border border-[#D9DEE7] hover:bg-[#F5F7FA] text-[#111827] font-semibold text-xs transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-[#0066FF] ${isRefreshing ? "animate-spin" : ""}`} />
                <span>{isRefreshing ? "Syncing..." : "Sync Database"}</span>
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6">
            {/* Metric KPI Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="bg-[#FFFFFF] p-4 rounded-lg border border-[#D9DEE7] shadow-sm">
                <div className="text-[11px] font-mono text-[#5B6472] uppercase tracking-wider">
                  Total Results
                </div>
                <div className="text-2xl font-bold text-[#111827] mt-1">
                  {summaryData.total_results.toLocaleString()}
                </div>
                <div className="text-[11px] text-[#059669] mt-1 flex items-center font-mono">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  {summaryData.by_status.completed || 0} completed
                </div>
              </div>

              <div className="bg-[#FFFFFF] p-4 rounded-lg border border-[#D9DEE7] shadow-sm">
                <div className="text-[11px] font-mono text-[#5B6472] uppercase tracking-wider flex items-center">
                  <Navigation className="w-3 h-3 mr-1 text-[#0284C7]" />
                  Navigation
                </div>
                <div className="text-2xl font-bold text-[#0284C7] mt-1">
                  {summaryData.by_module.navigation || 0}
                </div>
                <div className="text-[11px] text-[#5B6472] mt-1 font-mono">
                  Flight corridor scans
                </div>
              </div>

              <div className="bg-[#FFFFFF] p-4 rounded-lg border border-[#D9DEE7] shadow-sm">
                <div className="text-[11px] font-mono text-[#5B6472] uppercase tracking-wider flex items-center">
                  <AlertTriangle className="w-3 h-3 mr-1 text-[#DC2626]" />
                  Rod Debris (FOD)
                </div>
                <div className="text-2xl font-bold text-[#DC2626] mt-1">
                  {summaryData.by_module.rod_debris || 0}
                </div>
                <div className="text-[11px] text-[#5B6472] mt-1 font-mono">
                  Runway debris sweeps
                </div>
              </div>

              <div className="bg-[#FFFFFF] p-4 rounded-lg border border-[#D9DEE7] shadow-sm">
                <div className="text-[11px] font-mono text-[#5B6472] uppercase tracking-wider flex items-center">
                  <Lightbulb className="w-3 h-3 mr-1 text-[#D97706]" />
                  Runway Lights
                </div>
                <div className="text-2xl font-bold text-[#D97706] mt-1">
                  {summaryData.by_module.runway_lights || 0}
                </div>
                <div className="text-[11px] text-[#5B6472] mt-1 font-mono">
                  Light state inspections
                </div>
              </div>

              <div className="bg-[#FFFFFF] p-4 rounded-lg border border-[#D9DEE7] shadow-sm">
                <div className="text-[11px] font-mono text-[#5B6472] uppercase tracking-wider flex items-center">
                  <Radio className="w-3 h-3 mr-1 text-[#0066FF]" />
                  Surveillance
                </div>
                <div className="text-2xl font-bold text-[#0066FF] mt-1">
                  {(summaryData.by_module.live_surveillance || 0) + (summaryData.by_module.offline_surveillance || 0)}
                </div>
                <div className="text-[11px] text-[#5B6472] mt-1 font-mono">
                  Live & offline sessions
                </div>
              </div>
            </div>

            {/* Filter and Search Controls */}
            <div className="bg-[#FFFFFF] p-4 rounded-lg border border-[#D9DEE7] shadow-sm space-y-4">
              {/* Module Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2 border-b border-[#E2E8F0] pb-3">
                <span className="text-xs font-mono text-[#5B6472] font-semibold mr-2 flex items-center">
                  <Filter className="w-3.5 h-3.5 mr-1" /> MODULE:
                </span>

                {[
                  { id: "all", label: "All Modules", count: summaryData.total_results },
                  { id: "navigation", label: "Navigation", count: summaryData.by_module.navigation || 0 },
                  { id: "rod_debris", label: "Rod Debris (FOD)", count: summaryData.by_module.rod_debris || 0 },
                  { id: "runway_lights", label: "Runway Lights", count: summaryData.by_module.runway_lights || 0 },
                  { id: "live_surveillance", label: "Live Surveillance", count: summaryData.by_module.live_surveillance || 0 },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setSelectedModule(tab.id as ModuleFilter);
                      setPage(1);
                    }}
                    className={`px-3 py-1.5 rounded-full text-xs font-mono font-medium transition flex items-center space-x-1.5 ${
                      selectedModule === tab.id
                        ? "bg-[#0066FF] text-[#FFFFFF] shadow-sm"
                        : "bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]"
                    }`}
                  >
                    <span>{tab.label}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                        selectedModule === tab.id ? "bg-[#FFFFFF]/25 text-[#FFFFFF]" : "bg-[#E2E8F0] text-[#64748B]"
                      }`}
                    >
                      {tab.count}
                    </span>
                  </button>
                ))}
              </div>

              {/* Status and Search Filters */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Search Result ID, Title, Session..."
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setPage(1);
                      }}
                      className="pl-9 pr-4 py-1.5 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-md text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:border-[#0066FF] w-64 md:w-80 font-mono"
                    />
                  </div>

                  <select
                    value={selectedStatus}
                    onChange={(e) => {
                      setSelectedStatus(e.target.value as StatusFilter);
                      setPage(1);
                    }}
                    className="text-xs font-mono bg-[#F8FAFC] border border-[#CBD5E1] rounded-md px-3 py-1.5 text-[#1E293B] focus:outline-none focus:border-[#0066FF]"
                  >
                    <option value="all">Status: All</option>
                    <option value="completed">Status: Completed</option>
                    <option value="processing">Status: Processing</option>
                    <option value="queued">Status: Queued</option>
                    <option value="failed">Status: Failed</option>
                  </select>
                </div>

                <div className="text-xs font-mono text-[#64748B]">
                  Showing <span className="font-bold text-[#1E293B]">{resultsData.items.length}</span> of{" "}
                  <span className="font-bold text-[#1E293B]">{resultsData.total}</span> records
                </div>
              </div>
            </div>

            {/* Results Table */}
            <div className="bg-[#FFFFFF] rounded-lg border border-[#D9DEE7] shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-sans">
                  <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] font-mono text-[#475569] uppercase text-[11px]">
                    <tr>
                      <th className="py-3 px-4">Result ID</th>
                      <th className="py-3 px-4">Module</th>
                      <th className="py-3 px-4">Analysis / Session Title</th>
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Summary</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0]">
                    {loading ? (
                      <tr>
                        <td colSpan={7} className="text-center py-12 text-[#64748B] font-mono">
                          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#0066FF] mb-2" />
                          Loading centralized results...
                        </td>
                      </tr>
                    ) : resultsData.items.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-12 text-[#64748B] font-mono">
                          <Database className="w-8 h-8 text-[#94A3B8] mx-auto mb-2" />
                          No results found matching selected criteria.
                        </td>
                      </tr>
                    ) : (
                      resultsData.items.map((row) => {
                        const badge = getModuleBadge(row.module_type);
                        return (
                          <tr key={row.id} className="hover:bg-[#F8FAFC] transition">
                            <td className="py-3 px-4 font-mono font-medium text-[#0066FF]">
                              <span className="cursor-pointer hover:underline" onClick={() => handleOpenDetails(row.id)}>
                                {row.id}
                              </span>
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-mono border ${badge.color}`}
                              >
                                {badge.icon}
                                {badge.label}
                              </span>
                            </td>
                            <td className="py-3 px-4 font-medium text-[#1E293B]">
                              <div>{row.title}</div>
                              {row.session_id && (
                                <div className="text-[10px] text-[#64748B] font-mono">
                                  Session: {row.session_id}
                                </div>
                              )}
                            </td>
                            <td className="py-3 px-4 font-mono text-[#64748B] text-[11px]">
                              {formatDate(row.created_at)}
                            </td>
                            <td className="py-3 px-4">{getStatusBadge(row.status)}</td>
                            <td className="py-3 px-4 text-[#475569] max-w-xs truncate" title={row.summary || ""}>
                              {row.summary || "—"}
                            </td>
                            <td className="py-3 px-4 text-right space-x-2">
                              <button
                                onClick={() => handleOpenDetails(row.id)}
                                className="px-2.5 py-1 text-xs rounded bg-[#EAF3FF] hover:bg-[#D5E8FF] text-[#0066FF] font-semibold transition"
                              >
                                View Details
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              {resultsData.total_pages > 1 && (
                <div className="px-4 py-3 border-t border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between font-mono text-xs text-[#64748B]">
                  <div>
                    Page <span className="font-bold text-[#1E293B]">{page}</span> of{" "}
                    <span className="font-bold text-[#1E293B]">{resultsData.total_pages}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      className="px-2.5 py-1 rounded bg-[#FFFFFF] border border-[#CBD5E1] disabled:opacity-50 hover:bg-[#F1F5F9] transition flex items-center"
                    >
                      <ChevronLeft className="w-3.5 h-3.5 mr-1" />
                      Prev
                    </button>
                    <button
                      onClick={() => setPage((p) => Math.min(resultsData.total_pages, p + 1))}
                      disabled={page >= resultsData.total_pages}
                      className="px-2.5 py-1 rounded bg-[#FFFFFF] border border-[#CBD5E1] disabled:opacity-50 hover:bg-[#F1F5F9] transition flex items-center"
                    >
                      Next
                      <ChevronRight className="w-3.5 h-3.5 ml-1" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Slide-over Result Details Modal / Drawer (FR-09) */}
      {selectedResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/40 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-2xl h-full bg-[#FFFFFF] shadow-2xl flex flex-col overflow-hidden animate-slideLeft">
            {/* Drawer Header */}
            <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between bg-[#F8FAFC]">
              <div className="flex items-center space-x-2">
                <Database className="w-5 h-5 text-[#0066FF]" />
                <div>
                  <h3 className="font-bold text-[#1E293B] text-sm">Result Details: {selectedResult.id}</h3>
                  <div className="text-[11px] font-mono text-[#64748B]">
                    Module: {selectedResult.module_type.toUpperCase()} • Created: {formatDate(selectedResult.created_at)}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedResult(null)}
                className="p-1.5 rounded-full hover:bg-[#E2E8F0] text-[#64748B] transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Status and Title Card */}
              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-[#1E293B] text-base">{selectedResult.title}</h4>
                  <div>{getStatusBadge(selectedResult.status)}</div>
                </div>
                <p className="text-xs text-[#475569] leading-relaxed">
                  {selectedResult.summary || "No textual summary recorded."}
                </p>
                {selectedResult.error_message && (
                  <div className="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded text-xs text-[#DC2626] font-mono">
                    <span className="font-bold">Error:</span> {selectedResult.error_message}
                  </div>
                )}
              </div>

              {/* Module-Specific Structured Result Data (JSON) */}
              <div>
                <h5 className="text-xs font-mono font-bold text-[#475569] uppercase tracking-wider mb-2 flex items-center">
                  <SlidersHorizontal className="w-3.5 h-3.5 mr-1.5 text-[#0066FF]" />
                  Result Metrics & Execution Data
                </h5>
                <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3 font-mono text-xs">
                  <pre className="text-[#1E293B] overflow-x-auto max-h-48 whitespace-pre-wrap">
                    {JSON.stringify(selectedResult.result_data || {}, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Associated Media Assets (FR-09) */}
              <div>
                <h5 className="text-xs font-mono font-bold text-[#475569] uppercase tracking-wider mb-2 flex items-center">
                  <Video className="w-3.5 h-3.5 mr-1.5 text-[#0066FF]" />
                  Associated Media & Reports ({selectedResult.media_assets?.length || 0})
                </h5>
                {selectedResult.media_assets?.length === 0 ? (
                  <div className="text-xs text-[#64748B] font-mono p-3 bg-[#F8FAFC] rounded border border-[#E2E8F0]">
                    No external media files registered.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {selectedResult.media_assets.map((asset: any) => (
                      <div
                        key={asset.id}
                        className="flex items-center justify-between p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg"
                      >
                        <div className="flex items-center space-x-2 text-xs">
                          {asset.media_type === "video" ? (
                            <Video className="w-4 h-4 text-[#0066FF]" />
                          ) : asset.media_type === "image" ? (
                            <ImageIcon className="w-4 h-4 text-[#059669]" />
                          ) : (
                            <FileText className="w-4 h-4 text-[#D97706]" />
                          )}
                          <div>
                            <div className="font-medium text-[#1E293B]">{asset.file_name}</div>
                            <div className="text-[10px] text-[#64748B] font-mono">
                              {asset.media_type.toUpperCase()} • {(asset.file_size / 1024).toFixed(1)} KB
                            </div>
                          </div>
                        </div>
                        {asset.storage_key && (
                          <a
                            href={asset.storage_key.startsWith("http") ? asset.storage_key : `/api/v1/analysis/${selectedResult.id}/media`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-2.5 py-1 text-xs rounded bg-[#FFFFFF] border border-[#CBD5E1] hover:bg-[#F1F5F9] text-[#1E293B] font-mono font-semibold transition flex items-center"
                          >
                            <ExternalLink className="w-3 h-3 mr-1" /> View / Download
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Granular Detection Events Timeline (FR-09) */}
              <div>
                <h5 className="text-xs font-mono font-bold text-[#475569] uppercase tracking-wider mb-2 flex items-center">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-[#0066FF]" />
                  Detection Events Log ({selectedResult.events?.length || 0})
                </h5>
                {selectedResult.events?.length === 0 ? (
                  <div className="text-xs text-[#64748B] font-mono p-3 bg-[#F8FAFC] rounded border border-[#E2E8F0]">
                    Zero detection events recorded for this session.
                  </div>
                ) : (
                  <div className="border border-[#E2E8F0] rounded-lg overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] font-mono text-[10px] text-[#64748B]">
                        <tr>
                          <th className="py-2 px-3">Class</th>
                          <th className="py-2 px-3">Event Type</th>
                          <th className="py-2 px-3">Confidence</th>
                          <th className="py-2 px-3">Coordinates</th>
                          <th className="py-2 px-3">Video Time</th>
                          <th className="py-2 px-3 text-right">Map</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E2E8F0] font-mono text-[11px]">
                        {selectedResult.events.slice(0, 25).map((ev: any) => {
                          const loc = ev.location_data || ev.event_data?.debris_coordinates;
                          const lat = loc?.latitude;
                          const lon = loc?.longitude;
                          const unc = loc?.uncertainty_m;
                          const st = loc?.status;
                          const hasCoords = typeof lat === "number" && typeof lon === "number" && !isNaN(lat) && !isNaN(lon) && st !== "unavailable";

                          return (
                            <tr key={ev.id} className="hover:bg-[#F8FAFC]">
                              <td className="py-2 px-3 font-semibold text-[#1E293B]">{ev.class_name}</td>
                              <td className="py-2 px-3 text-[#64748B]">{ev.event_type}</td>
                              <td className="py-2 px-3 text-[#059669]">
                                {ev.confidence ? `${(ev.confidence * 100).toFixed(1)}%` : "N/A"}
                              </td>
                              <td className="py-2 px-3">
                                {hasCoords ? (
                                  <span className="text-[#1E293B] font-semibold">
                                    {lat.toFixed(5)}°, {lon.toFixed(5)}° (±{(unc ?? 1.5).toFixed(1)}m)
                                  </span>
                                ) : (
                                  <span className="text-[#64748B] italic">Unavailable</span>
                                )}
                              </td>
                              <td className="py-2 px-3 text-[#64748B]">
                                {ev.video_timestamp !== null ? `${ev.video_timestamp.toFixed(2)}s` : "Live"}
                              </td>
                              <td className="py-2 px-3 text-right">
                                {hasCoords ? (
                                  <button
                                    onClick={() =>
                                      setSelectedDebrisForMap({
                                        id: ev.id,
                                        class_name: ev.class_name,
                                        confidence: ev.confidence,
                                        bbox: ev.bbox_data,
                                        debris_coordinates: loc,
                                        latitude: lat,
                                        longitude: lon,
                                        coordinate_uncertainty_m: unc,
                                        coordinate_status: st,
                                      })
                                    }
                                    className="px-2 py-0.5 rounded text-[10px] bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#0066FF] font-semibold inline-flex items-center space-x-1"
                                    title="View location on map"
                                  >
                                    <MapPin className="w-3 h-3" />
                                    <span>Map</span>
                                  </button>
                                ) : (
                                  <span className="text-[#94A3B8] text-[10px]">--</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            {/* Drawer Footer */}
            <div className="px-6 py-3 border-t border-[#E2E8F0] bg-[#F8FAFC] flex justify-end">
              <button
                onClick={() => setSelectedResult(null)}
                className="px-4 py-1.5 rounded bg-[#0066FF] text-[#FFFFFF] text-xs font-mono font-bold hover:bg-[#0052CC] transition"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reusable Debris Location Map Modal (FR-08) */}
      <DebrisLocationMapModal
        isOpen={!!selectedDebrisForMap}
        onClose={() => setSelectedDebrisForMap(null)}
        detection={selectedDebrisForMap}
        droneTelemetry={null}
      />
    </div>
  );
}
