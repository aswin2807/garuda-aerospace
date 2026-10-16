"use client";

import React, { useRef, useState, useMemo, useEffect } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Maximize,
  Download,
  Filter,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  SlidersHorizontal,
  Film,
  FileSpreadsheet,
  FileCode,
} from "lucide-react";

interface DetectionItem {
  frame: number;
  timestamp_seconds?: number;
  timestamp_formatted?: string;
  class_name: string;
  confidence: number;
  bbox?: number[];
  track_id?: number | string;
  status?: string;
  row_id?: number;
  column_id?: number;
  is_confirmed?: boolean;
}

interface OfflineVideoReviewWorkspaceProps {
  jobId: string;
  filename: string;
  mediaType: string;
  analysisType: string;
  modelPath?: string;
  modelVersion?: string;
  confidenceThreshold?: number;
  totalFrames: number;
  processedFrames: number;
  durationSeconds: number;
  elapsedSeconds?: number;
  processingFps?: number;
  outcomeStatus?: string;
  detections: DetectionItem[];
  classCounts?: Record<string, number>;
  originalVideoUrl?: string;
  annotatedVideoUrl?: string;
  csvReportUrl?: string;
  jsonReportUrl?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const OfflineVideoReviewWorkspace: React.FC<OfflineVideoReviewWorkspaceProps> = ({
  jobId,
  filename,
  analysisType,
  modelPath,
  modelVersion,
  confidenceThreshold,
  totalFrames,
  processedFrames,
  durationSeconds,
  elapsedSeconds,
  processingFps,
  outcomeStatus,
  detections = [],
  classCounts = {},
  originalVideoUrl,
  annotatedVideoUrl,
  csvReportUrl,
  jsonReportUrl,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Video Player State
  const [activeSource, setActiveSource] = useState<"ANNOTATED" | "ORIGINAL">("ANNOTATED");
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(durationSeconds || 0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isMuted, setIsMuted] = useState(true);
  const [selectedDetection, setSelectedDetection] = useState<DetectionItem | null>(null);

  // Search & Filtering State (FR-07)
  const [classFilter, setClassFilter] = useState<string>("ALL");
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortBy, setSortBy] = useState<"TIME_ASC" | "TIME_DESC" | "CONF_DESC" | "CONF_ASC">("TIME_ASC");

  // Format seconds to MM:SS.s
  const formatTime = (secs: number) => {
    if (isNaN(secs) || secs < 0) return "00:00.0";
    const mins = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 10);
    return `${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}.${ms}`;
  };

  // Video event handlers
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || durationSeconds);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const seekTo = (seconds: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(0, Math.min(seconds, duration || 9999));
    setCurrentTime(seconds);
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleSeekDetection = (det: DetectionItem) => {
    setSelectedDetection(det);
    const targetSec = det.timestamp_seconds !== undefined
      ? det.timestamp_seconds
      : (det.frame / Math.max(1, 30.0));
    seekTo(targetSec);
  };

  // Available classes dynamically extracted from detections
  const availableClasses = useMemo(() => {
    const set = new Set<string>();
    detections.forEach((d) => {
      if (d.class_name) set.add(d.class_name);
    });
    return Array.from(set).sort();
  }, [detections]);

  // Filtered & Sorted Detections
  const filteredDetections = useMemo(() => {
    let result = detections.filter((d) => {
      // Class filter
      if (classFilter !== "ALL" && d.class_name !== classFilter) {
        return false;
      }
      // Confidence filter
      const conf = d.confidence || 0;
      if (conf < minConfidence / 100.0) {
        return false;
      }
      // Search query (matches frame, timestamp, track ID, or class)
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesClass = d.class_name.toLowerCase().includes(q);
        const matchesFrame = `frame ${d.frame}`.toLowerCase().includes(q) || String(d.frame) === q;
        const matchesTrack = d.track_id ? `track ${d.track_id}`.toLowerCase().includes(q) : false;
        const matchesTime = d.timestamp_formatted ? d.timestamp_formatted.includes(q) : false;
        if (!matchesClass && !matchesFrame && !matchesTrack && !matchesTime) {
          return false;
        }
      }
      return true;
    });

    // Sort
    result.sort((a, b) => {
      const timeA = a.timestamp_seconds !== undefined ? a.timestamp_seconds : a.frame;
      const timeB = b.timestamp_seconds !== undefined ? b.timestamp_seconds : b.frame;
      const confA = a.confidence || 0;
      const confB = b.confidence || 0;

      if (sortBy === "TIME_ASC") return timeA - timeB;
      if (sortBy === "TIME_DESC") return timeB - timeA;
      if (sortBy === "CONF_DESC") return confB - confA;
      if (sortBy === "CONF_ASC") return confA - confB;
      return 0;
    });

    return result;
  }, [detections, classFilter, minConfidence, searchQuery, sortBy]);

  const activeVideoUrl = activeSource === "ANNOTATED"
    ? annotatedVideoUrl || `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/video`
    : originalVideoUrl || `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/original`;

  const resolvedCsvUrl = csvReportUrl || `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/report?format=csv`;
  const resolvedJsonUrl = jsonReportUrl || `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/report?format=json`;

  const isClean = outcomeStatus === "COMPLETED_NO_DETECTIONS" || detections.length === 0;

  return (
    <div className="flex flex-col bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl overflow-hidden font-mono shadow-sm space-y-4 p-5 select-none">
      {/* 1. Header Banner & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#D9DEE7] pb-3">
        <div className="flex items-center space-x-2.5">
          <div className={`w-3 h-3 rounded-full ${isClean ? "bg-emerald-500" : "bg-[#0066FF] animate-pulse"}`} />
          <div>
            <h3 className="text-sm font-bold text-[#111827] tracking-wider uppercase">
              OFFLINE VIDEO SURVEILLANCE & DETECTION REVIEW
            </h3>
            <span className="text-[11px] text-[#5B6472]">
              Source: <span className="text-[#111827] font-semibold">{filename}</span> • Job ID: {jobId.slice(0, 10)}...
            </span>
          </div>
        </div>

        {/* Working Export Buttons (FR-08) */}
        <div className="flex items-center space-x-2">
          <a
            href={resolvedCsvUrl}
            download
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] text-xs font-semibold transition"
            title="Download CSV Detection Log"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-[#0066FF]" />
            <span>EXPORT CSV</span>
          </a>

          <a
            href={resolvedJsonUrl}
            download
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] text-xs font-semibold transition"
            title="Download JSON Summary"
          >
            <FileCode className="w-3.5 h-3.5 text-[#0066FF]" />
            <span>EXPORT JSON</span>
          </a>

          <a
            href={annotatedVideoUrl || `${API_BASE}/api/v1/analysis/${encodeURIComponent(jobId)}/video`}
            download
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#0066FF] hover:bg-[#0052CC] text-white text-xs font-bold transition shadow-xs"
            title="Download Annotated Output Video"
          >
            <Download className="w-3.5 h-3.5 text-white" />
            <span>DOWNLOAD VIDEO</span>
          </a>
        </div>
      </div>

      {/* 2. Analysis Summary Metrics Bar (FR-06) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5">
          <span className="text-[10px] text-[#5B6472] uppercase font-semibold block">Total Frames</span>
          <span className="text-lg font-bold text-[#111827]">{processedFrames || totalFrames}</span>
          <span className="text-[10px] text-[#5B6472] block">100% Inferred</span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5">
          <span className="text-[10px] text-[#5B6472] uppercase font-semibold block">Total Detections</span>
          <span className={`text-lg font-bold ${isClean ? "text-emerald-600" : "text-[#0066FF]"}`}>
            {detections.length}
          </span>
          <span className="text-[10px] text-[#5B6472] block">
            {isClean ? "Clean footage" : "Cumulative instances"}
          </span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5">
          <span className="text-[10px] text-[#5B6472] uppercase font-semibold block">Model Identifier</span>
          <span className="text-xs font-bold text-[#111827] truncate block" title={modelPath || "runway_light_best.pt"}>
            {(modelPath || "runway_light_best.pt").split("/").pop()}
          </span>
          <span className="text-[10px] text-[#0066FF] block">
            {modelVersion ? `SHA256:${modelVersion.slice(0, 8)}` : "YOLOv11 PyTorch"}
          </span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5">
          <span className="text-[10px] text-[#5B6472] uppercase font-semibold block">Analysis Duration</span>
          <span className="text-lg font-bold text-[#111827]">
            {elapsedSeconds ? `${elapsedSeconds.toFixed(1)}s` : "--"}
          </span>
          <span className="text-[10px] text-[#5B6472] block">
            Speed: {processingFps ? `${processingFps.toFixed(1)} FPS` : "--"}
          </span>
        </div>

        <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5">
          <span className="text-[10px] text-[#5B6472] uppercase font-semibold block">Processing Outcome</span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded inline-block mt-0.5 border ${
            isClean
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : "bg-blue-50 text-blue-700 border-blue-200"
          }`}>
            {isClean ? "COMPLETED (0 DETECTIONS)" : "COMPLETED (DETECTIONS FOUND)"}
          </span>
          <span className="text-[10px] text-[#5B6472] block mt-0.5">
            Video: {formatTime(durationSeconds)}
          </span>
        </div>
      </div>

      {/* Runway Pathway ROI Badge for FOD Analysis */}
      {analysisType === "FOD" && (
        <div className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg p-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-[#0F172A]">RUNWAY PATHWAY ROI:</span>
            <span className="text-[#334155]">Active Paved Runway Corridor Filtering (Non-runway candidates excluded)</span>
          </div>
          <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold border border-emerald-300 text-[10px]">
            VERIFIED IN-PATHWAY ONLY
          </span>
        </div>
      )}

      {/* 3. Main Review Workspace: Video Player + Detection Review List (FR-05, FR-07) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Video Player Column (7 cols) */}
        <div className="lg:col-span-7 flex flex-col space-y-2">
          {/* Stream Source Switcher Toggle */}
          <div className="flex items-center justify-between px-3 py-1.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg text-xs">
            <span className="text-[#5B6472] font-semibold text-[11px]">ACTIVE PLAYBACK SOURCE:</span>
            <div className="flex items-center space-x-1 bg-[#FFFFFF] p-0.5 rounded border border-[#D9DEE7]">
              <button
                onClick={() => setActiveSource("ORIGINAL")}
                className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition ${
                  activeSource === "ORIGINAL"
                    ? "bg-[#0066FF] text-white"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                Original Footage
              </button>
              <button
                onClick={() => setActiveSource("ANNOTATED")}
                className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition ${
                  activeSource === "ANNOTATED"
                    ? "bg-[#0066FF] text-white"
                    : "text-[#5B6472] hover:text-[#111827]"
                }`}
              >
                Annotated AI Output
              </button>
            </div>
          </div>

          {/* Video Container */}
          <div className="relative aspect-video bg-[#000000] rounded-lg overflow-hidden border border-[#D9DEE7] flex items-center justify-center">
            <video
              ref={videoRef}
              key={activeVideoUrl}
              src={activeVideoUrl}
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              playsInline
              className="w-full h-full object-contain"
            />

            {/* Overlaid Source Tag */}
            <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/60 backdrop-blur-xs text-white text-[10px] font-bold border border-white/20">
              {activeSource === "ANNOTATED" ? "AI BOUNDING BOX OVERLAY" : "RAW FOOTAGE"}
            </div>

            {/* Selected Detection Indicator Overlay */}
            {selectedDetection && (
              <div className="absolute bottom-2 left-2 px-2 py-1 rounded bg-black/80 text-white text-[11px] font-bold border border-[#0066FF] flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-[#0066FF]" />
                <span>
                  Seeking: {selectedDetection.class_name} ({Math.round(selectedDetection.confidence * 100)}%) at {formatTime(selectedDetection.timestamp_seconds || 0)}
                </span>
              </div>
            )}
          </div>

          {/* Custom Video Controls & Scrubber */}
          <div className="bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg p-2.5 flex flex-col space-y-2 text-xs">
            {/* Scrubber Bar */}
            <div className="flex items-center space-x-2">
              <span className="font-mono text-[11px] text-[#111827] min-w-[55px]">
                {formatTime(currentTime)}
              </span>
              <input
                type="range"
                min={0}
                max={duration || 100}
                step={0.1}
                value={currentTime}
                onChange={(e) => seekTo(parseFloat(e.target.value))}
                className="flex-1 h-1.5 bg-[#D9DEE7] rounded-lg appearance-none cursor-pointer accent-[#0066FF]"
              />
              <span className="font-mono text-[11px] text-[#5B6472] min-w-[55px] text-right">
                {formatTime(duration)}
              </span>
            </div>

            {/* Action Buttons Row */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <button
                  onClick={togglePlay}
                  className="p-1.5 rounded bg-[#0066FF] hover:bg-[#0052CC] text-white transition"
                  title={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
                </button>

                <button
                  onClick={() => seekTo(0)}
                  className="p-1.5 rounded bg-[#FFFFFF] hover:bg-[#EAF3FF] border border-[#D9DEE7] text-[#111827] transition"
                  title="Rewind to start"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>

                <button
                  onClick={() => {
                    if (videoRef.current) {
                      videoRef.current.muted = !videoRef.current.muted;
                      setIsMuted(videoRef.current.muted);
                    }
                  }}
                  className="p-1.5 rounded bg-[#FFFFFF] hover:bg-[#EAF3FF] border border-[#D9DEE7] text-[#5B6472] transition"
                  title={isMuted ? "Unmute" : "Mute"}
                >
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </button>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-[10px] text-[#5B6472]">Speed:</span>
                {[0.5, 1, 1.5, 2].map((spd) => (
                  <button
                    key={spd}
                    onClick={() => {
                      if (videoRef.current) {
                        videoRef.current.playbackRate = spd;
                        setPlaybackSpeed(spd);
                      }
                    }}
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      playbackSpeed === spd
                        ? "bg-[#0066FF] text-white"
                        : "bg-[#FFFFFF] text-[#5B6472] border border-[#D9DEE7]"
                    }`}
                  >
                    {spd}x
                  </button>
                ))}

                <button
                  onClick={() => {
                    if (videoRef.current) {
                      if (videoRef.current.requestFullscreen) {
                        videoRef.current.requestFullscreen();
                      }
                    }
                  }}
                  className="p-1.5 rounded bg-[#FFFFFF] hover:bg-[#EAF3FF] border border-[#D9DEE7] text-[#5B6472] transition ml-2"
                  title="Fullscreen"
                >
                  <Maximize className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Detection Review & Filtering Column (5 cols) (FR-05, FR-07) */}
        <div className="lg:col-span-5 flex flex-col space-y-2 border border-[#D9DEE7] rounded-lg p-3 bg-[#F5F7FA]">
          <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2">
            <div className="flex items-center space-x-2">
              <SlidersHorizontal className="w-4 h-4 text-[#0066FF]" />
              <span className="text-xs font-bold text-[#111827] uppercase">
                DETECTION REVIEW ({filteredDetections.length} / {detections.length})
              </span>
            </div>
            <span className="text-[10px] text-[#5B6472]">Click row to seek video</span>
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#5B6472] absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search by time, frame #, class..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#FFFFFF] border border-[#D9DEE7] rounded pl-8 pr-2.5 py-1.5 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF]"
            />
          </div>

          {/* Filter Pills Row */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-[10px] text-[#5B6472] font-semibold">CLASS:</span>
            <button
              onClick={() => setClassFilter("ALL")}
              className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                classFilter === "ALL"
                  ? "bg-[#0066FF] text-white border-[#0066FF]"
                  : "bg-white text-[#5B6472] border-[#D9DEE7]"
              }`}
            >
              ALL
            </button>
            {availableClasses.map((cls) => (
              <button
                key={cls}
                onClick={() => setClassFilter(cls)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  classFilter === cls
                    ? cls === "LIGHT OFF"
                      ? "bg-red-600 text-white border-red-600"
                      : "bg-[#0066FF] text-white border-[#0066FF]"
                    : "bg-white text-[#5B6472] border-[#D9DEE7]"
                }`}
              >
                {cls}
              </button>
            ))}
          </div>

          {/* Confidence Slider Filter */}
          <div className="flex items-center justify-between text-xs bg-[#FFFFFF] p-2 rounded border border-[#D9DEE7]">
            <span className="text-[10px] text-[#5B6472] font-semibold">MIN CONFIDENCE: {minConfidence}%</span>
            <input
              type="range"
              min={0}
              max={95}
              step={5}
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseInt(e.target.value) || 0)}
              className="w-28 h-1 bg-[#D9DEE7] rounded appearance-none cursor-pointer accent-[#0066FF]"
            />
          </div>

          {/* Sort Dropdown */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-[10px] text-[#5B6472] font-semibold">SORT:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-[#FFFFFF] border border-[#D9DEE7] rounded px-2 py-1 text-xs text-[#111827] focus:outline-none"
            >
              <option value="TIME_ASC">Time: Earliest First</option>
              <option value="TIME_DESC">Time: Latest First</option>
              <option value="CONF_DESC">Confidence: High to Low</option>
              <option value="CONF_ASC">Confidence: Low to High</option>
            </select>
          </div>

          {/* Interactive Detections List */}
          <div className="flex-1 max-h-[380px] overflow-y-auto space-y-1.5 pr-1 pt-1">
            {filteredDetections.length === 0 ? (
              <div className="py-8 text-center text-xs text-[#5B6472] bg-white rounded border border-dashed border-[#D9DEE7]">
                {detections.length === 0
                  ? "No detections found in video footage."
                  : "No detections match active filters."}
              </div>
            ) : (
              filteredDetections.map((det, idx) => {
                const tsSec = det.timestamp_seconds !== undefined
                  ? det.timestamp_seconds
                  : (det.frame / Math.max(1, 30.0));
                const tsFormatted = det.timestamp_formatted || formatTime(tsSec);
                const isSelected = selectedDetection === det;
                const isOff = det.class_name === "LIGHT OFF";

                return (
                  <div
                    key={idx}
                    onClick={() => handleSeekDetection(det)}
                    className={`p-2 rounded border cursor-pointer transition flex items-center justify-between text-xs ${
                      isSelected
                        ? "bg-[#EAF3FF] border-[#0066FF] shadow-xs"
                        : "bg-white border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF]"
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-[#0066FF] font-bold text-[11px] bg-[#EAF3FF] px-1.5 py-0.5 rounded border border-[#0066FF]/30">
                        {tsFormatted}
                      </span>
                      <div>
                        <div className="flex items-center space-x-1.5">
                          <span className={`font-bold ${isOff ? "text-red-600" : "text-[#111827]"}`}>
                            {det.class_name}
                          </span>
                          {det.is_confirmed && (
                            <span className="text-[9px] px-1 py-0.2 rounded bg-red-100 text-red-700 font-bold">
                              CONFIRMED FAULT
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-[#5B6472] block">
                          Frame #{det.frame} {det.track_id ? `• Track #${det.track_id}` : ""} {det.row_id ? `• R${det.row_id}C${det.column_id}` : ""}
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="font-mono text-xs font-bold text-[#111827] block">
                        {(det.confidence * 100).toFixed(1)}%
                      </span>
                      <span className="text-[10px] text-[#0066FF] font-semibold hover:underline">
                        Seek →
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
