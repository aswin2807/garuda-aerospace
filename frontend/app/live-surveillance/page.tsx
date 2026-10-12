"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { TopBar } from "../../components/hud/TopBar";
import { Sidebar } from "../../components/hud/Sidebar";
import {
  Radio,
  Wifi,
  WifiOff,
  Camera,
  Play,
  Square,
  RefreshCw,
  AlertTriangle,
  Layers,
  Settings,
  Eye,
  Activity,
  CheckCircle2,
  Clock,
  Shield,
  Sliders,
} from "lucide-react";
import {
  startLiveSurveillance,
  stopLiveSurveillance,
  getLiveSurveillanceStatus,
  getLiveSurveillanceFeedUrl,
  listLiveSurveillanceSessions,
} from "../../lib/api";
import { useDroneStore } from "../../stores/droneStore";
import { IpCameraConnectModal } from "../../components/camera/IpCameraConnectModal";

type StreamSourceType = "RTSP" | "IP_CAMERA" | "DRONE_FEED" | "WEBCAM";
type SelectedModelType = "ALL" | "NAVIGATION" | "FOD" | "RUNWAY_LIGHT";

interface LiveSession {
  session_id: string;
  camera_name: string;
  status: string;
  stream_url: string;
  fps: number;
  inference_fps?: number;
  total_detections?: number;
}

export default function LiveSurveillancePage() {
  const [sourceType, setSourceType] = useState<StreamSourceType>("RTSP");
  const [streamUrl, setStreamUrl] = useState<string>("rtsp://192.168.1.120:554/live");
  const [cameraName, setCameraName] = useState<string>("Runway Cam 01");
  const [selectedModel, setSelectedModel] = useState<SelectedModelType>("ALL");
  const [showAnnotations, setShowAnnotations] = useState<boolean>(true);

  // Connection & session state
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<"IDLE" | "CONNECTING" | "CONNECTED" | "ERROR">("IDLE");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeSessions, setActiveSessions] = useState<LiveSession[]>([]);

  // Telemetry & metrics state
  const [streamFps, setStreamFps] = useState<number>(0);
  const [infFps, setInfFps] = useState<number>(0);
  const [latencyMs, setLatencyMs] = useState<number>(0);
  const [resolution, setResolution] = useState<{ width: number; height: number }>({ width: 1920, height: 1080 });
  const [counts, setCounts] = useState<{ navigation: number; fod: number; light_on: number; light_off: number }>({
    navigation: 0,
    fod: 0,
    light_on: 0,
    light_off: 0,
  });
  const [detections, setDetections] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);

  // Modal & Webcam refs
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const statusPollRef = useRef<NodeJS.Timeout | null>(null);

  // Sync with global store if active camera exists
  const globalCameraId = useDroneStore((s) => s.activeCameraId);
  const globalCameraStatus = useDroneStore((s) => s.cameraStatus);

  useEffect(() => {
    fetchActiveSessions();
    const interval = setInterval(fetchActiveSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchActiveSessions = async () => {
    try {
      const sessions = await listLiveSurveillanceSessions();
      if (Array.isArray(sessions)) {
        setActiveSessions(sessions);
        if (sessions.length > 0 && !activeSessionId) {
          setActiveSessionId(sessions[0].session_id);
          setConnectionStatus("CONNECTED");
        }
      }
    } catch {
      // Ignore background poll errors
    }
  };

  // Poll active session status
  useEffect(() => {
    if (!activeSessionId || connectionStatus !== "CONNECTED") {
      if (statusPollRef.current) clearInterval(statusPollRef.current);
      return;
    }

    const pollStatus = async () => {
      try {
        const data = await getLiveSurveillanceStatus(activeSessionId);
        if (data) {
          setStreamFps(Math.round(data.camera_fps || data.fps || 0));
          setInfFps(Math.round(data.inference_fps || 0));
          setLatencyMs(Math.round(data.latency_ms || 0));
          if (data.width && data.height) {
            setResolution({ width: data.width, height: data.height });
          }
          if (data.counts) {
            setCounts({
              navigation: data.counts.navigation || 0,
              fod: data.counts.fod || 0,
              light_on: data.counts.light_on || 0,
              light_off: data.counts.light_off || 0,
            });
          }
          if (Array.isArray(data.detections)) {
            setDetections(data.detections);
          }
          if (Array.isArray(data.alerts)) {
            setAlerts(data.alerts);
          }
          if (data.status === "ERROR") {
            setConnectionStatus("ERROR");
            setErrorMessage(data.error || "Camera feed disconnected");
          }
        }
      } catch (err: any) {
        console.warn("Failed to poll surveillance status:", err);
      }
    };

    pollStatus();
    statusPollRef.current = setInterval(pollStatus, 1000);
    return () => {
      if (statusPollRef.current) clearInterval(statusPollRef.current);
    };
  }, [activeSessionId, connectionStatus]);

  // Handle Start Surveillance
  const handleStartSurveillance = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setConnectionStatus("CONNECTING");

    if (sourceType === "WEBCAM") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 1280, height: 720 },
          audio: false,
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
        setConnectionStatus("CONNECTED");
        setActiveSessionId("local_webcam");
        setStreamFps(30);
      } catch (err: any) {
        setConnectionStatus("ERROR");
        setErrorMessage(err.message || "Failed to access local webcam");
      } finally {
        setIsLoading(false);
      }
      return;
    }

    try {
      const res = await startLiveSurveillance({
        stream_url: streamUrl,
        camera_name: cameraName,
        model_type: selectedModel,
        is_simulated: streamUrl.startsWith("demo://"),
      });

      if (res.success && res.session_id) {
        setActiveSessionId(res.session_id);
        setConnectionStatus("CONNECTED");
        await fetchActiveSessions();
      } else {
        setConnectionStatus("ERROR");
        setErrorMessage(res.message || "Failed to start live surveillance");
      }
    } catch (err: any) {
      setConnectionStatus("ERROR");
      setErrorMessage(err.message || "Connection refused or host unreachable");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Stop Surveillance
  const handleStopSurveillance = async () => {
    if (!activeSessionId) return;

    setIsLoading(true);
    if (activeSessionId === "local_webcam") {
      if (videoRef.current && videoRef.current.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
        tracks.forEach((t) => t.stop());
        videoRef.current.srcObject = null;
      }
      setActiveSessionId(null);
      setConnectionStatus("IDLE");
      setIsLoading(false);
      return;
    }

    try {
      await stopLiveSurveillance(activeSessionId);
    } catch (err) {
      console.warn("Stop surveillance error:", err);
    } finally {
      setActiveSessionId(null);
      setConnectionStatus("IDLE");
      setDetections([]);
      setCounts({ navigation: 0, fod: 0, light_on: 0, light_off: 0 });
      setIsLoading(false);
      await fetchActiveSessions();
    }
  };

  const feedUrl = activeSessionId && activeSessionId !== "local_webcam"
    ? getLiveSurveillanceFeedUrl(activeSessionId, showAnnotations)
    : null;

  return (
    <div className="flex flex-col h-screen w-screen bg-[#FFFFFF] overflow-hidden font-sans select-none">
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 flex flex-col overflow-hidden bg-[#F5F7FA]">
          {/* Top Surveillance Control Bar */}
          <div className="bg-[#FFFFFF] border-b border-[#D9DEE7] px-6 py-3 flex flex-wrap items-center justify-between gap-4 font-mono text-xs shadow-sm">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <span
                  className={`w-3 h-3 rounded-full ${
                    connectionStatus === "CONNECTED"
                      ? "bg-[#0066FF] animate-pulse"
                      : connectionStatus === "CONNECTING"
                      ? "bg-amber-500 animate-ping"
                      : connectionStatus === "ERROR"
                      ? "bg-red-500"
                      : "bg-[#5B6472]"
                  }`}
                />
                <span className="font-bold text-[#111827] uppercase tracking-wider text-sm">
                  Live Surveillance
                </span>
              </div>

              <span className="text-[10px] bg-[#EAF3FF] text-[#0066FF] font-bold px-2 py-0.5 rounded border border-[#0066FF]/30">
                STATUS: {connectionStatus}
              </span>

              {activeSessionId && (
                <span className="text-[10px] text-[#5B6472] px-2 py-0.5 rounded bg-[#F5F7FA] border border-[#D9DEE7]">
                  ID: {activeSessionId}
                </span>
              )}
            </div>

            {/* Source Type Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-[#5B6472] text-[11px] font-bold">SOURCE:</span>
              <div className="flex bg-[#F5F7FA] p-0.5 rounded-lg border border-[#D9DEE7]">
                {(["RTSP", "IP_CAMERA", "DRONE_FEED", "WEBCAM"] as StreamSourceType[]).map((src) => (
                  <button
                    key={src}
                    disabled={connectionStatus === "CONNECTED"}
                    onClick={() => {
                      setSourceType(src);
                      if (src === "RTSP") setStreamUrl("rtsp://192.168.1.120:554/live");
                      if (src === "IP_CAMERA") setIsModalOpen(true);
                      if (src === "DRONE_FEED") setStreamUrl("rtsp://192.168.1.150:554/drone/feed");
                    }}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold transition ${
                      sourceType === src
                        ? "bg-[#0066FF] text-white shadow-sm"
                        : "text-[#5B6472] hover:text-[#111827] disabled:opacity-50"
                    }`}
                  >
                    {src.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>

            {/* Model Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-[#5B6472] text-[11px] font-bold">MODEL:</span>
              <div className="flex bg-[#F5F7FA] p-0.5 rounded-lg border border-[#D9DEE7]">
                {(["ALL", "NAVIGATION", "FOD", "RUNWAY_LIGHT"] as SelectedModelType[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setSelectedModel(m)}
                    className={`px-2 py-1 rounded text-[10px] font-bold transition ${
                      selectedModel === m
                        ? "bg-[#0066FF] text-white shadow-sm"
                        : "text-[#5B6472] hover:text-[#111827]"
                    }`}
                  >
                    {m === "ALL" ? "TRI-MODEL" : m}
                  </button>
                ))}
              </div>
            </div>

            {/* Primary Action Buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowAnnotations(!showAnnotations)}
                className={`px-2.5 py-1.5 rounded border text-xs font-semibold flex items-center gap-1.5 transition ${
                  showAnnotations
                    ? "bg-[#EAF3FF] text-[#0066FF] border-[#0066FF]/40"
                    : "bg-[#FFFFFF] text-[#5B6472] border-[#D9DEE7] hover:bg-[#F5F7FA]"
                }`}
                title="Toggle Real-Time AI Bounding Boxes"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>AI Overlay</span>
              </button>

              {connectionStatus === "CONNECTED" ? (
                <button
                  onClick={handleStopSurveillance}
                  disabled={isLoading}
                  className="px-4 py-1.5 rounded bg-red-600 hover:bg-red-700 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-sm"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop Surveillance</span>
                </button>
              ) : (
                <button
                  onClick={handleStartSurveillance}
                  disabled={isLoading}
                  className="px-4 py-1.5 rounded bg-[#0066FF] hover:bg-[#008CFF] text-white font-bold text-xs flex items-center gap-1.5 transition shadow-sm disabled:opacity-50"
                >
                  {isLoading ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Play className="w-3.5 h-3.5 fill-current" />
                  )}
                  <span>Start Surveillance</span>
                </button>
              )}
            </div>
          </div>

          {/* Quick Stream URL Bar when not connected */}
          {connectionStatus !== "CONNECTED" && sourceType !== "WEBCAM" && (
            <div className="bg-[#FFFFFF] border-b border-[#D9DEE7] px-6 py-2 flex items-center space-x-3 text-xs font-mono">
              <span className="text-[#5B6472] font-semibold whitespace-nowrap">Stream URL:</span>
              <input
                type="text"
                value={streamUrl}
                onChange={(e) => setStreamUrl(e.target.value)}
                placeholder="rtsp://host:port/path or http://host:port/stream"
                className="flex-1 px-3 py-1 bg-[#F5F7FA] border border-[#D9DEE7] rounded text-[#111827] focus:outline-none focus:border-[#0066FF]"
              />
              <span className="text-[#5B6472] font-semibold whitespace-nowrap">Camera Name:</span>
              <input
                type="text"
                value={cameraName}
                onChange={(e) => setCameraName(e.target.value)}
                className="w-48 px-3 py-1 bg-[#F5F7FA] border border-[#D9DEE7] rounded text-[#111827] focus:outline-none focus:border-[#0066FF]"
              />
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-2.5 py-1 bg-[#F5F7FA] border border-[#D9DEE7] rounded hover:border-[#0066FF] hover:text-[#0066FF] text-[#5B6472] flex items-center gap-1"
              >
                <Settings className="w-3.5 h-3.5" />
                <span>Advanced</span>
              </button>
            </div>
          )}

          {/* Error Banner */}
          {errorMessage && (
            <div className="mx-6 mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-red-700 text-xs font-mono">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
              <div className="flex-1">
                <strong>CONNECTION ERROR:</strong> {errorMessage}
              </div>
              <button
                onClick={() => setErrorMessage(null)}
                className="text-red-500 hover:text-red-800 text-xs underline ml-2"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Main Surveillance Display & Metrics Layout */}
          <div className="flex-1 p-4 grid grid-cols-1 lg:grid-cols-4 gap-4 overflow-hidden">
            {/* Live Video Monitor (3 Cols) */}
            <div className="lg:col-span-3 flex flex-col bg-[#000000] border border-[#D9DEE7] rounded-xl overflow-hidden relative shadow-md">
              {/* Top HUD Overlay Info */}
              <div className="absolute top-3 inset-x-3 z-20 flex items-center justify-between text-white font-mono text-[11px] pointer-events-none select-none">
                <div className="flex items-center space-x-2 bg-[#000000]/80 px-2.5 py-1 rounded backdrop-blur-md border border-white/20">
                  <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-pulse" />
                  <span className="font-bold">{cameraName}</span>
                  <span className="text-white/60">[{sourceType}]</span>
                </div>

                <div className="flex items-center space-x-2">
                  <div className="bg-[#000000]/80 px-2.5 py-1 rounded backdrop-blur-md border border-white/20 flex items-center space-x-3">
                    <span>
                      RES: <strong className="text-[#008CFF]">{resolution.width}×{resolution.height}</strong>
                    </span>
                    <span>
                      FPS: <strong className="text-[#008CFF]">{streamFps}</strong>
                    </span>
                    <span>
                      AI FPS: <strong className="text-[#008CFF]">{infFps}</strong>
                    </span>
                    <span>
                      LATENCY: <strong className="text-[#008CFF]">{latencyMs}ms</strong>
                    </span>
                  </div>
                </div>
              </div>

              {/* Video Content Canvas */}
              <div className="flex-1 flex items-center justify-center relative overflow-hidden bg-[#0A0A0A]">
                {connectionStatus === "CONNECTED" && sourceType === "WEBCAM" ? (
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-contain"
                  />
                ) : connectionStatus === "CONNECTED" && feedUrl ? (
                  <img
                    src={feedUrl}
                    alt="Live Surveillance Stream"
                    className="w-full h-full object-contain"
                    onError={() => {
                      setConnectionStatus("ERROR");
                      setErrorMessage("Surveillance feed connection dropped or unreachable");
                    }}
                  />
                ) : connectionStatus === "CONNECTING" ? (
                  <div className="flex flex-col items-center justify-center space-y-4 text-center p-6 select-none">
                    <div className="w-16 h-16 border-4 border-[#0066FF] border-t-transparent rounded-full animate-spin" />
                    <div className="font-mono text-white font-bold text-sm">
                      VERIFYING NETWORK & CONNECTING TO STREAM...
                    </div>
                    <div className="text-white/60 font-mono text-xs max-w-md">
                      Testing TCP handshake at {streamUrl}...
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center space-y-4 text-center p-8 select-none text-white">
                    <div className="w-20 h-20 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-[#0066FF]">
                      <Radio className="w-10 h-10 animate-pulse" />
                    </div>
                    <div className="font-mono font-bold text-base tracking-wider">
                      LIVE SURVEILLANCE STANDBY
                    </div>
                    <p className="text-white/60 font-mono text-xs max-w-md leading-relaxed">
                      Connect a real RTSP camera, IP stream, or drone optical link to begin real-time surveillance and AI detection.
                    </p>
                    <button
                      onClick={handleStartSurveillance}
                      disabled={isLoading}
                      className="px-6 py-2.5 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] text-white font-mono text-xs font-bold uppercase tracking-wider transition shadow-lg shadow-[#0066FF]/30 flex items-center gap-2"
                    >
                      <Play className="w-4 h-4 fill-current" />
                      <span>Start Surveillance</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Bottom HUD Detection Ticker */}
              <div className="bg-[#000000]/90 border-t border-white/20 px-4 py-2 flex items-center justify-between font-mono text-xs text-white select-none">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#0066FF]" />
                    <span className="text-white/70">NAVIGATION:</span>
                    <strong className="text-[#008CFF] font-bold">{counts.navigation}</strong>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-pulse" />
                    <span className="text-white/70">FOD DEBRIS:</span>
                    <strong className="text-[#008CFF] font-bold">{counts.fod}</strong>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#008CFF]" />
                    <span className="text-white/70">LIGHT ON:</span>
                    <strong className="text-[#008CFF] font-bold">{counts.light_on}</strong>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    <span className="text-white/70">LIGHT OFF:</span>
                    <strong className="text-red-400 font-bold">{counts.light_off}</strong>
                  </div>
                </div>

                <div className="text-[10px] text-white/50">
                  REAL-TIME YOLO INFERENCE
                </div>
              </div>
            </div>

            {/* Tactical Sidebar Panels (1 Col) */}
            <div className="flex flex-col space-y-4 overflow-y-auto">
              {/* Surveillance Summary Card */}
              <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-4 font-mono text-xs shadow-sm">
                <div className="flex items-center justify-between pb-2 border-b border-[#D9DEE7]">
                  <span className="font-bold text-[#111827] uppercase">Surveillance Metrics</span>
                  <Activity className="w-4 h-4 text-[#0066FF]" />
                </div>
                <div className="mt-3 space-y-2.5">
                  <div className="flex justify-between">
                    <span className="text-[#5B6472]">Target Camera:</span>
                    <strong className="text-[#111827]">{cameraName}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5B6472]">Stream Protocol:</span>
                    <strong className="text-[#111827]">{sourceType}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5B6472]">Active Model:</span>
                    <strong className="text-[#0066FF]">{selectedModel}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5B6472]">AI Overlays:</span>
                    <strong className={showAnnotations ? "text-emerald-600" : "text-[#5B6472]"}>
                      {showAnnotations ? "ENABLED" : "RAW FEED"}
                    </strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5B6472]">Total Objects:</span>
                    <strong className="text-[#0066FF] font-bold">
                      {counts.navigation + counts.fod + counts.light_on + counts.light_off}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Active Detections Feed */}
              <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-4 font-mono text-xs shadow-sm flex-1 flex flex-col">
                <div className="flex items-center justify-between pb-2 border-b border-[#D9DEE7]">
                  <span className="font-bold text-[#111827] uppercase">
                    Live Detections ({detections.length})
                  </span>
                  <span className="text-[10px] text-[#0066FF] font-bold">CURRENT FRAME</span>
                </div>

                <div className="mt-3 flex-1 overflow-y-auto space-y-2 max-h-[350px]">
                  {detections.length === 0 ? (
                    <div className="text-center py-8 text-[#5B6472] text-[11px]">
                      No objects detected in current frame.
                    </div>
                  ) : (
                    detections.map((det, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded-lg bg-[#F5F7FA] border border-[#D9DEE7] flex items-center justify-between hover:border-[#0066FF] transition"
                      >
                        <div className="flex items-center space-x-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              det.class_name?.includes("LIGHT")
                                ? "bg-amber-500"
                                : det.class_name?.includes("FOD")
                                ? "bg-red-500"
                                : "bg-[#0066FF]"
                            }`}
                          />
                          <div>
                            <div className="font-bold text-[#111827] text-[11px]">
                              {det.class_name || det.name || `Object #${idx + 1}`}
                            </div>
                            <div className="text-[10px] text-[#5B6472]">
                              CONF: {Math.round((det.confidence || 0) * 100)}%
                            </div>
                          </div>
                        </div>
                        <div className="text-[10px] text-[#5B6472] font-mono">
                          {det.box
                            ? `[${Math.round(det.box[0])}, ${Math.round(det.box[1])}]`
                            : "VERIFIED"}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Active Sessions Panel */}
              {activeSessions.length > 0 && (
                <div className="bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl p-3 font-mono text-xs shadow-sm">
                  <div className="font-bold text-[#111827] mb-2 uppercase text-[11px]">
                    Active Sessions ({activeSessions.length})
                  </div>
                  <div className="space-y-1.5">
                    {activeSessions.map((s) => (
                      <button
                        key={s.session_id}
                        onClick={() => {
                          setActiveSessionId(s.session_id);
                          setConnectionStatus("CONNECTED");
                        }}
                        className={`w-full text-left p-2 rounded border transition text-[11px] flex items-center justify-between ${
                          activeSessionId === s.session_id
                            ? "bg-[#EAF3FF] border-[#0066FF] text-[#0066FF] font-bold"
                            : "bg-[#F5F7FA] border-[#D9DEE7] text-[#111827] hover:bg-[#F0F6FF]"
                        }`}
                      >
                        <span className="truncate">{s.camera_name || s.session_id}</span>
                        <span className="text-[10px] text-[#5B6472]">{Math.round(s.fps)} FPS</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Advanced IP Camera Modal */}
      <IpCameraConnectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConnected={(camId) => {
          setActiveSessionId(camId);
          setConnectionStatus("CONNECTED");
        }}
      />
    </div>
  );
}
