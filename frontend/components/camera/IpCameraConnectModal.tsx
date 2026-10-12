"use client";

import React, { useState, useEffect } from "react";
import {
  Camera,
  Radio,
  Wifi,
  WifiOff,
  AlertTriangle,
  CheckCircle2,
  X,
  Play,
  Square,
  RefreshCw,
  Sliders,
  Shield,
  HelpCircle,
  ExternalLink,
} from "lucide-react";
import {
  connectCamera,
  disconnectCamera,
  getCameraStatus,
  getCameras,
} from "../../lib/api";
import { useDroneStore } from "../../stores/droneStore";
import type { CameraStatus, CameraListItem } from "../../types/detection";

interface IpCameraConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnected?: (cameraId: string) => void;
}

export const IpCameraConnectModal: React.FC<IpCameraConnectModalProps> = ({
  isOpen,
  onClose,
  onConnected,
}) => {
  const activeCameraId = useDroneStore((s) => s.activeCameraId);
  const cameraStatus = useDroneStore((s) => s.cameraStatus);
  const setActiveCameraId = useDroneStore((s) => s.setActiveCameraId);
  const setCameraStatus = useDroneStore((s) => s.setCameraStatus);
  const setCameraInfo = useDroneStore((s) => s.setCameraInfo);

  // Form states
  const [tab, setTab] = useState<"IP_CONFIG" | "DIRECT_URL" | "SIMULATION">("IP_CONFIG");
  const [cameraName, setCameraName] = useState("Drone Optical Cam 01");
  const [ipAddress, setIpAddress] = useState("192.168.1.100");
  const [port, setPort] = useState<number>(554);
  const [protocol, setProtocol] = useState<"RTSP" | "HTTP" | "HTTPS" | "MJPEG">("RTSP");
  const [streamPath, setStreamPath] = useState("/stream");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [directUrl, setDirectUrl] = useState("rtsp://192.168.1.100:554/stream");

  // Operational states
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [savedCameras, setSavedCameras] = useState<CameraListItem[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);

  // Fetch saved cameras on open
  useEffect(() => {
    if (isOpen) {
      loadSavedCameras();
    }
  }, [isOpen]);

  const loadSavedCameras = async () => {
    try {
      setIsLoadingList(true);
      const list = await getCameras();
      setSavedCameras(list);
    } catch (err) {
      console.warn("Could not fetch camera list:", err);
    } finally {
      setIsLoadingList(false);
    }
  };

  // Assembled Stream URL preview
  const assembledUrl = React.useMemo(() => {
    let creds = "";
    if (username.trim()) {
      creds = `${encodeURIComponent(username)}:${password ? encodeURIComponent(password) : ""}@`;
    }
    const cleanPath = streamPath.startsWith("/") ? streamPath : `/${streamPath}`;
    return `${protocol.toLowerCase()}://${creds}${ipAddress}:${port}${cleanPath}`;
  }, [protocol, username, password, ipAddress, port, streamPath]);

  // Connect Handler
  const handleConnect = async (isSimulatedOverride = false) => {
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    setCameraStatus("CONNECTING");

    try {
      let params;
      if (tab === "SIMULATION" || isSimulatedOverride) {
        params = {
          camera_name: cameraName || "Simulated Drone Cam",
          is_simulated: true,
          stream_url: "demo://navigation_drone_feed",
        };
      } else if (tab === "DIRECT_URL") {
        if (!directUrl.trim()) {
          throw new Error("RTSP / Stream URL cannot be empty.");
        }
        params = {
          camera_id: "camera_01",
          camera_name: cameraName || "Drone Camera 01",
          rtsp_url: directUrl.trim(),
          stream_url: directUrl.trim(),
        };
      } else {
        // IP config mode
        if (!ipAddress.trim()) {
          throw new Error("IP Address cannot be empty.");
        }
        params = {
          camera_name: cameraName,
          ip: ipAddress.trim(),
          port: Number(port) || 554,
          protocol: protocol,
          path: streamPath.trim(),
          username: username.trim() || undefined,
          password: password || undefined,
        };
      }

      const res = await connectCamera(params);

      if (res.success) {
        setActiveCameraId(res.camera_id);
        setCameraStatus((res.status as CameraStatus) || "LIVE");
        setCameraInfo({
          ip: ipAddress,
          stream_url: res.stream_url,
          fps: res.fps || 30,
          latency_ms: res.latency_ms || 25,
          camera_name: cameraName,
        });
        setSuccessMessage(`Connected successfully to ${res.camera_id}!`);
        if (onConnected) onConnected(res.camera_id);
        await loadSavedCameras();
        setTimeout(() => {
          onClose();
        }, 1200);
      } else {
        throw new Error(res.message || "Failed to establish camera connection.");
      }
    } catch (err: any) {
      setCameraStatus("CONNECTION LOST");
      setErrorMessage(err.message || "Failed to connect to IP camera.");
    } finally {
      setIsLoading(false);
    }
  };

  // Disconnect Handler
  const handleDisconnect = async () => {
    if (!activeCameraId) return;
    setIsLoading(true);
    try {
      await disconnectCamera(activeCameraId);
      setActiveCameraId(null);
      setCameraStatus("DISCONNECTED");
      setCameraInfo(null);
      setSuccessMessage("Camera disconnected.");
      await loadSavedCameras();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to disconnect camera.");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-[#FFFFFF] border border-[#D9DEE7] rounded-xl shadow-2xl overflow-hidden font-sans text-[#111827]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-[#FFFFFF] border-b border-[#D9DEE7]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-[#EAF3FF] border border-[#0066FF]/30 flex items-center justify-center text-[#0066FF]">
              <Camera className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-[#111827] flex items-center gap-2">
                Live Webcam / IP Camera Connection
                <span className="text-[10px] bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30 px-1.5 py-0.5 rounded font-mono">
                  RTSP / HTTP / MJPEG
                </span>
              </h2>
              <p className="text-xs text-[#5B6472]">
                Connect external drone payload camera or IP stream for real-time YOLOv11 inference
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-[#5B6472] hover:text-[#111827] hover:bg-[#F0F6FF] transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Banner */}
        <div className="px-6 py-2.5 bg-[#F5F7FA] border-b border-[#D9DEE7] flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <span className="text-[#5B6472] font-mono">STATUS:</span>
            <span
              className={`inline-flex items-center gap-1.5 font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                cameraStatus === "LIVE"
                  ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/40"
                  : cameraStatus === "CONNECTING" || cameraStatus === "RECONNECTING"
                  ? "bg-[#EAF3FF] text-[#008CFF] border border-[#008CFF]/40 animate-pulse"
                  : cameraStatus === "CONNECTION LOST"
                  ? "bg-red-50 text-red-600 border border-red-200"
                  : "bg-[#FFFFFF] text-[#5B6472] border border-[#D9DEE7]"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  cameraStatus === "LIVE"
                    ? "bg-[#0066FF] animate-ping"
                    : cameraStatus === "CONNECTING" || cameraStatus === "RECONNECTING"
                    ? "bg-[#008CFF]"
                    : "bg-red-500"
                }`}
              />
              {cameraStatus}
            </span>
            {activeCameraId && (
              <span className="text-[#5B6472] font-mono">({activeCameraId})</span>
            )}
          </div>

          {activeCameraId && cameraStatus === "LIVE" && (
            <button
              onClick={handleDisconnect}
              disabled={isLoading}
              className="flex items-center gap-1 text-[11px] font-mono text-red-600 hover:bg-red-50 px-2 py-1 rounded transition border border-red-200"
            >
              <Square className="w-3 h-3 fill-current" />
              Disconnect
            </button>
          )}
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-[#D9DEE7] bg-[#FFFFFF] px-6 pt-3 space-x-4 text-xs font-medium">
          <button
            onClick={() => setTab("IP_CONFIG")}
            className={`pb-2.5 border-b-2 transition flex items-center gap-1.5 ${
              tab === "IP_CONFIG"
                ? "border-[#0066FF] text-[#0066FF] font-bold"
                : "border-transparent text-[#5B6472] hover:text-[#111827]"
            }`}
          >
            <Wifi className="w-3.5 h-3.5" />
            Standard IP & Port
          </button>
          <button
            onClick={() => setTab("DIRECT_URL")}
            className={`pb-2.5 border-b-2 transition flex items-center gap-1.5 ${
              tab === "DIRECT_URL"
                ? "border-[#0066FF] text-[#0066FF] font-bold"
                : "border-transparent text-[#5B6472] hover:text-[#111827]"
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            Direct Stream URL
          </button>
          <button
            onClick={() => setTab("SIMULATION")}
            className={`pb-2.5 border-b-2 transition flex items-center gap-1.5 ${
              tab === "SIMULATION"
                ? "border-[#0066FF] text-[#0066FF] font-bold"
                : "border-transparent text-[#5B6472] hover:text-[#111827]"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            Dataset Simulation (Offline Test)
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-4">
          {tab === "IP_CONFIG" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-[#5B6472] mb-1">
                  Camera Label
                </label>
                <input
                  type="text"
                  value={cameraName}
                  onChange={(e) => setCameraName(e.target.value)}
                  placeholder="e.g. Drone Optical Cam 01"
                  className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                />
              </div>

              <div className="grid grid-cols-12 gap-3">
                <div className="col-span-8">
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-mono uppercase text-[#5B6472]">
                      IP Address
                    </label>
                    <div className="flex gap-1">
                      {["192.168.1.100", "127.0.0.1", "10.0.0.50"].map((ip) => (
                        <button
                          key={ip}
                          type="button"
                          onClick={() => setIpAddress(ip)}
                          className="text-[10px] bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] text-[#5B6472] hover:text-[#0066FF] px-1.5 py-0.5 rounded font-mono"
                        >
                          {ip}
                        </button>
                      ))}
                    </div>
                  </div>
                  <input
                    type="text"
                    value={ipAddress}
                    onChange={(e) => setIpAddress(e.target.value)}
                    placeholder="192.168.1.100"
                    className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                  />
                </div>

                <div className="col-span-4">
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-mono uppercase text-[#5B6472]">
                      Port
                    </label>
                    <div className="flex gap-1">
                      {[554, 8080, 8554].map((p) => (
                        <button
                          key={p}
                          type="button"
                          onClick={() => setPort(p)}
                          className="text-[10px] bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] text-[#5B6472] hover:text-[#0066FF] px-1 py-0.5 rounded font-mono"
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                  <input
                    type="number"
                    value={port}
                    onChange={(e) => setPort(parseInt(e.target.value) || 0)}
                    placeholder="554"
                    className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-12 gap-3">
                <div className="col-span-5">
                  <label className="block text-xs font-mono uppercase text-[#5B6472] mb-1">
                    Protocol
                  </label>
                  <select
                    value={protocol}
                    onChange={(e) => setProtocol(e.target.value as any)}
                    className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                  >
                    <option value="RTSP">RTSP (Port 554)</option>
                    <option value="HTTP">HTTP (Port 80/8080)</option>
                    <option value="HTTPS">HTTPS (Port 443)</option>
                    <option value="MJPEG">MJPEG Stream</option>
                  </select>
                </div>

                <div className="col-span-7">
                  <label className="block text-xs font-mono uppercase text-[#5B6472] mb-1">
                    Stream Path
                  </label>
                  <input
                    type="text"
                    value={streamPath}
                    onChange={(e) => setStreamPath(e.target.value)}
                    placeholder="/stream or /live"
                    className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                  />
                </div>
              </div>

              {/* Optional Credentials */}
              <div className="p-3 bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-mono text-[#5B6472]">
                  <Shield className="w-3.5 h-3.5 text-[#0066FF]" />
                  <span>AUTHENTICATION (OPTIONAL)</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Username (e.g. admin)"
                    className="bg-[#FFFFFF] border border-[#D9DEE7] rounded px-3 py-1.5 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                  />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    className="bg-[#FFFFFF] border border-[#D9DEE7] rounded px-3 py-1.5 text-xs text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                  />
                </div>
              </div>

              {/* URL Preview */}
              <div className="p-2.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded font-mono text-xs">
                <span className="text-[#5B6472] mr-2">Target URL:</span>
                <span className="text-[#0066FF] font-semibold break-all">{assembledUrl}</span>
              </div>
            </div>
          )}

          {tab === "DIRECT_URL" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-[#5B6472] mb-1">
                  Camera Label
                </label>
                <input
                  type="text"
                  value={cameraName}
                  onChange={(e) => setCameraName(e.target.value)}
                  placeholder="e.g. Perimeter IP Camera"
                  className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-mono uppercase text-[#5B6472]">
                    Full Stream URL (RTSP / HTTP / MJPEG)
                  </label>
                  <div className="flex gap-1">
                    {[
                      { label: "PRD RTSP", url: "rtsp://192.168.144.108:554/stream=1" },
                      { label: "Default RTSP", url: "rtsp://192.168.1.100:554/stream" },
                    ].map((preset) => (

                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => setDirectUrl(preset.url)}
                        className="text-[10px] bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] text-[#5B6472] hover:text-[#0066FF] px-1.5 py-0.5 rounded font-mono"
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  type="text"
                  value={directUrl}
                  onChange={(e) => setDirectUrl(e.target.value)}
                  placeholder="rtsp://192.168.144.108:554/stream=1"
                  className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-3 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono"
                />
                <p className="text-[11px] text-[#5B6472] mt-1 font-mono">
                  Supported protocols: rtsp://, http://, https:// (e.g. rtsp://192.168.144.108:554/stream=1)
                </p>
              </div>
            </div>
          )}

          {tab === "SIMULATION" && (
            <div className="p-4 bg-[#F5F7FA] border border-[#D9DEE7] rounded-lg space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded bg-[#EAF3FF] text-[#0066FF] flex items-center justify-center shrink-0">
                  <Play className="w-4 h-4 fill-current" />
                </div>
                <div>
                  <h4 className="text-xs font-bold font-mono uppercase text-[#0066FF]">
                    Onboard Dataset Simulation Feed
                  </h4>
                  <p className="text-xs text-[#5B6472] mt-1 leading-relaxed">
                    Test the full live camera pipeline without requiring external IP hardware.
                    This loops through the official navigation drone dataset test frames (`test/images/*.jpg`),
                    passing each frame through YOLOv11 for beacon/target detection with live FPS and latency telemetry.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Success Banner */}
          {successMessage && (
            <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs font-mono">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Error Diagnostics Banner */}
          {errorMessage && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-xs space-y-1">
              <div className="flex items-center gap-2 font-mono font-bold">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>CONNECTION FAILED:</span>
              </div>
              <p className="text-red-700 font-mono text-[11px] pl-6 break-words">
                {errorMessage}
              </p>
              <div className="pl-6 pt-1 text-[10px] text-[#5B6472] space-y-0.5">
                <div>• Verify drone and IP camera are on the same local subnet.</div>
                <div>• Check that port {port} is open and stream path is valid.</div>
                <div>• If testing locally without hardware, switch to <strong>Dataset Simulation</strong> tab.</div>
              </div>
            </div>
          )}

          {/* Saved / Recent Cameras */}
          {savedCameras.length > 0 && (
            <div className="pt-2 border-t border-[#D9DEE7]">
              <div className="flex items-center justify-between text-xs text-[#5B6472] font-mono mb-2">
                <span>REGISTERED CAMERAS ({savedCameras.length}):</span>
                <button
                  type="button"
                  onClick={loadSavedCameras}
                  className="hover:text-[#111827] flex items-center gap-1 text-[10px]"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoadingList ? "animate-spin" : ""}`} />
                  Refresh
                </button>
              </div>

              <div className="max-h-28 overflow-y-auto space-y-1.5 pr-1">
                {savedCameras.map((cam) => (
                  <div
                    key={cam.camera_id}
                    className="flex items-center justify-between p-2 rounded bg-[#F5F7FA] border border-[#D9DEE7] text-xs"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="font-mono text-[#111827] font-semibold">{cam.camera_name}</span>
                      <span className="text-[10px] text-[#5B6472] font-mono truncate">
                        {cam.stream_url}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                          cam.status === "LIVE"
                            ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30"
                            : "bg-[#FFFFFF] text-[#5B6472] border border-[#D9DEE7]"
                        }`}
                      >
                        {cam.status}
                      </span>
                      {activeCameraId !== cam.camera_id && (
                        <button
                          type="button"
                          onClick={() => {
                            if (cam.ip_address) setIpAddress(cam.ip_address);
                            if (cam.port) setPort(cam.port);
                            setDirectUrl(cam.stream_url);
                            setCameraName(cam.camera_name);
                          }}
                          className="text-[10px] font-mono bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] text-[#111827] px-2 py-0.5 rounded transition"
                        >
                          Use
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 bg-[#FFFFFF] border-t border-[#D9DEE7]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-mono text-[#5B6472] hover:text-[#111827] hover:bg-[#F0F6FF] rounded transition"
          >
            Cancel
          </button>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              disabled={isLoading}
              onClick={() => handleConnect(false)}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] disabled:opacity-50 text-white text-xs font-mono font-bold tracking-wider uppercase transition shadow-sm shadow-[#0066FF]/30"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Connecting to stream...
                </>
              ) : (
                <>
                  <Wifi className="w-3.5 h-3.5" />
                  Connect Camera
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
