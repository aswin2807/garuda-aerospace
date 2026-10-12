"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import {
  Camera,
  Settings,
  Square,
  Wifi,
  WifiOff,
  Radio,
  Play,
  RotateCcw,
  Sliders,
} from "lucide-react";
import { DetectionCanvas } from "./DetectionCanvas";
import { IpCameraConnectModal } from "./IpCameraConnectModal";
import { useWebSocket } from "../../hooks/useWebSocket";
import { useDroneStore } from "../../stores/droneStore";
import { detectImageFile, getCameraWsUrl, disconnectCamera, startVideoAnalysis, stopVideoAnalysis } from "../../lib/api";

type FeedMode = "NO_FEED" | "WEBCAM" | "VIDEO_FILE" | "IMAGE_FILE" | "IP_CAMERA";


export const LiveCamera: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraWsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [mode, setMode] = useState<FeedMode>("NO_FEED");

  const [videoDims, setVideoDims] = useState<{ width: number; height: number }>({ width: 640, height: 480 });
  const [containerDims, setContainerDims] = useState<{ width: number; height: number }>({ width: 640, height: 480 });
  const [uploadedImageSrc, setUploadedImageSrc] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(true);

  // IP Camera specific state
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [ipCameraFrame, setIpCameraFrame] = useState<string | null>(null);
  const [cameraReconnectCount, setCameraReconnectCount] = useState<number>(0);

  const drone = useDroneStore((s) => s.drone);
  const confidenceThreshold = useDroneStore((s) => s.confidenceThreshold);
  const setDetections = useDroneStore((s) => s.setDetections);
  const setFps = useDroneStore((s) => s.setFps);

  // Camera store bindings
  const activeCameraId = useDroneStore((s) => s.activeCameraId);
  const cameraStatus = useDroneStore((s) => s.cameraStatus);
  const cameraInfo = useDroneStore((s) => s.cameraInfo);
  const setActiveCameraId = useDroneStore((s) => s.setActiveCameraId);
  const setCameraStatus = useDroneStore((s) => s.setCameraStatus);
  const setCameraInfo = useDroneStore((s) => s.setCameraInfo);
  const detections = useDroneStore((s) => s.detections);
  const imageQuality = useDroneStore((s) => s.imageQuality);
  const setImageQuality = useDroneStore((s) => s.setImageQuality);
  const cameraResolution = useDroneStore((s) => s.cameraResolution);
  const setCameraResolution = useDroneStore((s) => s.setCameraResolution);
  const cameraFps = useDroneStore((s) => s.cameraFps);
  const setCameraFps = useDroneStore((s) => s.setCameraFps);
  const inferenceFps = useDroneStore((s) => s.inferenceFps);
  const setInferenceFps = useDroneStore((s) => s.setInferenceFps);
  const setActiveModel = useDroneStore((s) => s.setActiveModel);
  const counts = useDroneStore((s) => s.counts);
  const videoFrame = useDroneStore((s) => s.videoFrame);
  const activeSessionId = useDroneStore((s) => s.activeSessionId);
  const setActiveSessionId = useDroneStore((s) => s.setActiveSessionId);
  const performance = useDroneStore((s) => s.performance);
  const alerts = useDroneStore((s) => s.alerts);
  const setAlerts = useDroneStore((s) => s.setAlerts);
  const summary = useDroneStore((s) => s.summary);
  const setSummary = useDroneStore((s) => s.setSummary);
  const applyDetectionUpdate = useDroneStore((s) => s.applyDetectionUpdate);

  // Drone client-side frame sending (for webcam / video file)
  const { sendFrame } = useWebSocket(drone?.id || "DR-01");

  // Track container size
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setContainerDims({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // Frame capture loop for video / webcam
  const captureFrame = useCallback(() => {
    if (!videoRef.current || !isStreaming || mode === "IMAGE_FILE" || mode === "IP_CAMERA") return;
    const video = videoRef.current;
    if (video.readyState < 2) return;

    const offscreen = document.createElement("canvas");
    offscreen.width = 512;
    offscreen.height = 512;
    const ctx = offscreen.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, 512, 512);
    const b64 = offscreen.toDataURL("image/jpeg", 0.7);
    sendFrame(b64, confidenceThreshold);
  }, [isStreaming, mode, sendFrame, confidenceThreshold]);

  useEffect(() => {
    if (!isStreaming || mode === "IMAGE_FILE" || mode === "IP_CAMERA") return;
    const interval = setInterval(captureFrame, 100); // 10 FPS frame transmission
    return () => clearInterval(interval);
  }, [captureFrame, isStreaming, mode]);

  // IP Camera WebSocket Stream Handler
  useEffect(() => {
    if (mode !== "IP_CAMERA" || !activeCameraId) {
      if (cameraWsRef.current) {
        cameraWsRef.current.close();
        cameraWsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      return;
    }

    const connectCameraWs = () => {
      const wsUrl = getCameraWsUrl(activeCameraId);
      const ws = new WebSocket(wsUrl);
      cameraWsRef.current = ws;

      ws.onopen = () => {
        setCameraStatus("LIVE");
        setCameraReconnectCount(0);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "camera_frame") {
            if (data.image_base64) {
              setIpCameraFrame(data.image_base64);
            }
            if (Array.isArray(data.detections)) {
              setDetections(data.detections, data.latency_ms);
            }
            if (data.fps !== undefined) {
              setFps(Math.round(data.fps));
            }
            if (data.inference_fps !== undefined) {
              setInferenceFps(data.inference_fps);
            }
            if (data.camera_fps !== undefined) {
              setCameraFps(data.camera_fps);
            }
            if (data.width && data.height) {
              setCameraResolution({ width: data.width, height: data.height });
              setVideoDims({ width: data.width, height: data.height });
            }
            if (data.brightness !== undefined || data.sharpness !== undefined || data.warnings) {
              setImageQuality({
                brightness: data.brightness,
                sharpness: data.sharpness,
                warnings: data.warnings || [],
              });
            }
            if (data.status && data.status !== "DISCONNECTED") {
              setCameraStatus(data.status);
            }
            if (data.model) {
              setActiveModel(data.model);
            }
            if (Array.isArray(data.alerts)) {
              setAlerts(data.alerts);
            }
            if (data.summary) {
              setSummary(data.summary);
            }
            applyDetectionUpdate(data);
          }
        } catch (err) {
          console.error("Error parsing camera WS stream message:", err);
        }
      };

      ws.onclose = () => {
        if (cameraStatus !== "DISCONNECTED") {
          setCameraStatus("RECONNECTING");
          setCameraReconnectCount((c) => c + 1);
          // Reconnect with capped backoff
          reconnectTimerRef.current = setTimeout(connectCameraWs, 3000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectCameraWs();

    return () => {
      if (cameraWsRef.current) {
        cameraWsRef.current.close();
        cameraWsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [mode, activeCameraId, setDetections, setFps, setCameraStatus, cameraStatus]);

  // Mode Handlers
  const handleStartWebcam = async () => {
    setMode("WEBCAM");
    setUploadedImageSrc(null);
    setIpCameraFrame(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch (err) {
      console.warn("Webcam access unavailable or rejected:", err);
    }
  };

  const handleSelectIpCamera = () => {
    setMode("IP_CAMERA");
    setUploadedImageSrc(null);
    if (!activeCameraId) {
      setIsModalOpen(true);
    }
  };

  const handleDisconnectCurrentCamera = async () => {
    if (!activeCameraId) return;
    try {
      await disconnectCamera(activeCameraId);
    } catch (err) {
      console.warn("Disconnect error:", err);
    } finally {
      setActiveCameraId(null);
      setCameraStatus("DISCONNECTED");
      setCameraInfo(null);
      setIpCameraFrame(null);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type.startsWith("image/")) {
      setMode("IMAGE_FILE");
      setIpCameraFrame(null);
      const url = URL.createObjectURL(file);
      setUploadedImageSrc(url);
      try {
        const res = await detectImageFile(file, confidenceThreshold, drone?.id);
        if (res.success && res.detections) {
          setDetections(res.detections, res.processing_time_ms);
        }
      } catch (err) {
        console.error("Image upload inference error:", err);
      }
    } else if (file.type.startsWith("video/")) {
      setMode("VIDEO_FILE");
      setUploadedImageSrc(null);
      setIpCameraFrame(null);
      try {
        const formData = new FormData();
        formData.append("file", file);
        const uploadRes = await fetch("/api/v1/video/upload", {
          method: "POST",
          body: formData,
        });
        const uploadData = await uploadRes.json();
        if (uploadData.path) {
          const startRes = await startVideoAnalysis(uploadData.path, true);
          if (startRes.session_id) {
            setActiveCameraId(startRes.session_id);
          }
        }
      } catch (err) {
        console.error("Video upload error:", err);
      }
    }
  };


  return (
    <div className="relative flex flex-col h-full bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg overflow-hidden shadow-sm">
      {/* Top Source Switcher Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#FFFFFF] border-b border-[#D9DEE7] text-xs text-[#5B6472]">
        <div className="flex items-center space-x-2">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              activeSessionId || cameraStatus === "LIVE"
                ? "bg-[#0066FF] animate-pulse"
                : "bg-[#D9DEE7]"
            }`}
          />
          <span className="font-mono uppercase tracking-wider font-semibold text-[#111827]">
            FEED: {activeSessionId ? "RUNWAY_AI" : mode}
          </span>
          {(activeCameraId || activeSessionId) && (
            <span className="text-[10px] font-mono bg-[#EAF3FF] text-[#0066FF] px-1.5 py-0.5 rounded border border-[#0066FF]/30">
              {activeSessionId || activeCameraId}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">

          {mode !== "NO_FEED" && (
            <button
              onClick={() => {
                setMode("NO_FEED");
                setUploadedImageSrc(null);
                setIpCameraFrame(null);
                if (videoRef.current && videoRef.current.srcObject) {
                  const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
                  tracks.forEach((t) => t.stop());
                  videoRef.current.srcObject = null;
                }
              }}
              className="px-2 py-1 rounded transition text-xs font-medium bg-red-50 hover:bg-red-100 text-red-600 border border-red-200"
            >
              Clear Feed
            </button>
          )}

          <button
            onClick={handleStartWebcam}
            className={`px-2.5 py-1 rounded transition font-medium ${
              mode === "WEBCAM"
                ? "bg-[#0066FF] text-white shadow-sm shadow-[#0066FF]/20"
                : "bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827]"
            }`}
          >
            Webcam
          </button>


          {/* IP Camera button */}
          <button
            onClick={handleSelectIpCamera}
            className={`px-2.5 py-1 rounded transition font-medium flex items-center gap-1.5 ${
              mode === "IP_CAMERA"
                ? "bg-[#0066FF] text-white shadow-sm shadow-[#0066FF]/20"
                : "bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827]"
            }`}
          >
            <Wifi className="w-3.5 h-3.5" />
            IP Camera
          </button>

          {/* Quick config button when in IP camera mode */}
          {mode === "IP_CAMERA" && (
            <>
              <button
                onClick={() => setIsModalOpen(true)}
                title="Camera Settings"
                className="p-1 rounded bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#5B6472] hover:text-[#111827] transition"
              >
                <Settings className="w-3.5 h-3.5" />
              </button>
              {activeCameraId && (
                <button
                  onClick={handleDisconnectCurrentCamera}
                  title="Disconnect Camera"
                  className="p-1 rounded bg-red-50 hover:bg-red-100 text-red-600 border border-red-300 transition"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                </button>
              )}
            </>
          )}

          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-2.5 py-1 rounded bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827] transition font-medium"
          >
            Upload Video/Image
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="image/*,video/*"
            className="hidden"
          />
        </div>
      </div>

      {/* Main Video & Overlay Area */}
      <div ref={containerRef} className="relative flex-1 bg-[#000000] border border-[#D9DEE7] flex items-center justify-center overflow-hidden">
        {mode === "IMAGE_FILE" && uploadedImageSrc ? (
          <img
            src={uploadedImageSrc}
            alt="Drone Capture"
            onLoad={(e) => {
              const target = e.currentTarget;
              setVideoDims({ width: target.naturalWidth, height: target.naturalHeight });
            }}
            className="max-w-full max-h-full object-contain"
          />
        ) : (videoFrame || ipCameraFrame) ? (
          <img
            src={videoFrame || ipCameraFrame || undefined}
            alt="Live Video Feed"
            onLoad={(e) => {
              const target = e.currentTarget;
              setVideoDims({ width: target.naturalWidth, height: target.naturalHeight });
            }}
            className="max-w-full max-h-full object-contain"
          />
        ) : mode === "IP_CAMERA" && !ipCameraFrame ? (
          /* IP Camera Standby / Prompt State */
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#000000] text-center p-6 select-none">
            <div className="w-44 h-44 border border-[#0066FF]/30 rounded-full flex items-center justify-center relative mb-4">
              <div className="w-28 h-28 border border-dashed border-[#0066FF]/50 rounded-full animate-spin-slow"></div>
              <div className="w-12 h-12 bg-[#0066FF]/10 border border-[#0066FF]/40 rounded-full flex items-center justify-center text-[#008CFF]">
                <Wifi className="w-6 h-6 animate-pulse" />
              </div>
              <div className="absolute w-full h-[1px] bg-[#0066FF]/20"></div>
              <div className="absolute h-full w-[1px] bg-[#0066FF]/20"></div>
            </div>

            <div className="font-mono text-[#008CFF] font-bold text-sm tracking-widest uppercase mb-1">
              {activeCameraId ? `CONNECTING TO ${activeCameraId}...` : "IP CAMERA STREAM STANDBY"}
            </div>

            <p className="text-[#EAF3FF] text-xs max-w-sm mb-4">
              {activeCameraId
                ? `Awaiting video frames from ${cameraInfo?.stream_url || "stream endpoint"}. Status: ${cameraStatus}`
                : "No IP camera feed active. Connect via RTSP, HTTP, MJPEG, or run an offline dataset test feed."}
            </p>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#0066FF] hover:bg-[#008CFF] text-white font-mono text-xs font-bold uppercase tracking-wider transition shadow-lg shadow-[#0066FF]/30"
              >
                <Wifi className="w-3.5 h-3.5" />
                {activeCameraId ? "Change Camera" : "Connect IP Camera"}
              </button>
            </div>
          </div>
        ) : mode === "NO_FEED" ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#F5F7FA] text-center p-8 select-none">

            <div className="w-16 h-16 rounded-2xl bg-[#EAF3FF] border border-[#0066FF]/20 flex items-center justify-center mb-4 text-[#0066FF] shadow-sm">
              <Camera className="w-8 h-8" />
            </div>
            <div className="font-mono text-[#111827] font-bold text-sm tracking-wider uppercase mb-2">
              NO LIVE FEED AVAILABLE
            </div>
            <p className="text-[#5B6472] text-xs max-w-md mb-6 leading-relaxed">
              No live feed available. Connect a supported drone or camera to view the live feed, or open Analysis to upload a video for offline processing.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={handleSelectIpCamera}
                className="px-4 py-2 bg-[#0066FF] hover:bg-[#008CFF] text-white text-xs font-semibold rounded-lg shadow-sm transition flex items-center gap-1.5"
              >
                <Wifi className="w-4 h-4" />
                Connect Camera / RTSP
              </button>
              <button
                onClick={handleStartWebcam}
                className="px-4 py-2 bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#111827] text-xs font-semibold rounded-lg transition flex items-center gap-1.5"
              >
                <Camera className="w-4 h-4 text-[#0066FF]" />
                Use Webcam
              </button>
              <a
                href="/analysis"
                className="px-4 py-2 bg-[#FFFFFF] hover:bg-[#F0F6FF] border border-[#D9DEE7] text-[#0066FF] text-xs font-semibold rounded-lg transition"
              >
                Open Analysis Workspace →
              </a>
            </div>
          </div>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            loop
            muted
            playsInline
            onLoadedMetadata={(e) => {
              const v = e.currentTarget;
              setVideoDims({ width: v.videoWidth, height: v.videoHeight });
            }}
            className="w-full h-full object-cover"
          />
        )}


        {/* Dynamic HTML5 Canvas Overlay */}
        <DetectionCanvas
          videoWidth={videoDims.width}
          videoHeight={videoDims.height}
          containerWidth={containerDims.width}
          containerHeight={containerDims.height}
        />

        {/* HUD Image Quality Warnings */}
        {imageQuality?.warnings && imageQuality.warnings.length > 0 && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center space-x-1.5 px-3 py-1 rounded bg-[#000000]/90 border border-amber-500/80 text-amber-300 font-mono text-[11px] font-bold shadow-lg backdrop-blur-sm animate-pulse">
            <span>⚠️</span>
            <span>{imageQuality.warnings.join(" • ")}</span>
          </div>
        )}

        {/* Real-time Image Quality Chip */}
        <div className="absolute top-3 right-3 z-20 flex items-center space-x-2 text-[10px] font-mono select-none">
          {imageQuality?.brightness !== undefined && (
            <div className="px-2 py-0.5 rounded bg-[#000000]/80 border border-white/20 text-[#EAF3FF] backdrop-blur-sm">
              BRIGHTNESS: <span className="text-[#008CFF] font-bold">{Math.round(imageQuality.brightness)}</span>
            </div>
          )}
          {imageQuality?.sharpness !== undefined && (
            <div className="px-2 py-0.5 rounded bg-[#000000]/80 border border-white/20 text-[#EAF3FF] backdrop-blur-sm">
              SHARPNESS: <span className="text-[#008CFF] font-bold">{Math.round(imageQuality.sharpness)}</span>
            </div>
          )}
        </div>

        {/* HUD Runway Ticker & Active Alerts Overlay */}
        <div className="absolute bottom-8 inset-x-0 z-20 px-3 py-1 bg-[#000000]/90 backdrop-blur-md border-t border-white/20 flex flex-col space-y-1 font-mono select-none">
          {/* Ticker Row */}
          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center space-x-4">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#0066FF]" />
                <span className="text-white/80">LIGHT ON:</span>
                <strong className="text-[#008CFF] font-bold">{counts?.light_on ?? summary?.light_on_count ?? 0}</strong>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#008CFF] animate-pulse" />
                <span className="text-white/80">LIGHT OFF:</span>
                <strong className="text-[#008CFF] font-bold">{counts?.light_off ?? summary?.light_off_count ?? 0}</strong>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-pulse" />
                <span className="text-white/80">FOD:</span>
                <strong className="text-[#008CFF] font-bold">{counts?.fod ?? summary?.fod_count ?? 0}</strong>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#0066FF]" />
                <span className="text-white/80">NAV OBJECTS:</span>
                <strong className="text-[#008CFF] font-bold">{counts?.navigation ?? summary?.nav_count ?? 0}</strong>
              </span>
            </div>
            <div className="text-[10px] text-white/70 hidden sm:block">
              TRI-MODEL INFERENCE (NAV + FOD + RUNWAY)
            </div>
          </div>

          {/* Active Alerts Row (if any) */}
          {alerts && alerts.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-0.5 border-t border-white/20">
              {alerts.map((al, idx) => (
                <div
                  key={al.id || idx}
                  className="flex items-center space-x-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-[#000000] border border-white/20 text-white"
                >
                  <span className="text-[#008CFF]">⚠️</span>
                  <span>{al.event_type || (al.class_name === "FOD" ? "FOD DETECTED" : "RUNWAY LIGHT FAULT")}</span>
                  {al.status && <span className="text-[#008CFF] font-normal">[{al.status}]</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom Tactical Status Bar */}
        <div className="absolute bottom-0 inset-x-0 z-20 bg-[#000000]/90 backdrop-blur-sm border-t border-white/20 px-4 py-1.5 flex items-center justify-between text-[11px] font-mono text-[#EAF3FF] select-none">
          <div className="flex items-center space-x-3 truncate">
            <span>
              RESOLUTION:{" "}
              <strong className="text-white">
                {cameraResolution.width} × {cameraResolution.height}
              </strong>
            </span>
            <span className="text-white/30">|</span>
            <span>
              INFERENCE: <strong className="text-[#008CFF]">YOLOv11</strong>
            </span>
            <span className="text-white/30">|</span>
            <span>
              TILED: <strong className="text-[#008CFF]">ON (640px)</strong>
            </span>
            <span className="text-white/30">|</span>
            <span>
              CAMERA: <strong className="text-white">{mode === "IP_CAMERA" ? "RTSP" : mode}</strong>
            </span>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <span className="text-white/80">OBJECTS:</span>
            <span className="px-1.5 py-0.5 rounded bg-[#0066FF]/10 text-[#008CFF] font-bold border border-[#0066FF]/40">
              {detections.length}
            </span>
          </div>
        </div>
      </div>

      {/* Connection Modal */}
      <IpCameraConnectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConnected={(camId) => {
          setMode("IP_CAMERA");
        }}
      />
    </div>
  );
};
