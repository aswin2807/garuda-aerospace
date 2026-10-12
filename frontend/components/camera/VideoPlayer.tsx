"use client";

import React, { useRef, useState, useEffect } from "react";
import { Play, Square, Upload, Film, AlertCircle } from "lucide-react";
import { useDroneStore } from "../../stores/droneStore";
import { useVideo } from "../../hooks/useVideo";
import { DetectionCanvas } from "./DetectionCanvas";

export const VideoPlayer: React.FC = () => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const videoFrame = useDroneStore((s) => s.videoFrame);
  const activeSessionId = useDroneStore((s) => s.activeSessionId);
  const performance = useDroneStore((s) => s.performance);
  const detections = useDroneStore((s) => s.detections);

  const [containerDims, setContainerDims] = useState<{ width: number; height: number }>({ width: 640, height: 480 });
  const [videoDims, setVideoDims] = useState<{ width: number; height: number }>({ width: 512, height: 512 });
  const [selectedFileName, setSelectedFileName] = useState<string>("data/videos/runway_demo.mp4");

  const { isProcessing, startAnalysis, stopAnalysis, error } = useVideo();

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

  const handleStartDemoVideo = async () => {
    try {
      await startAnalysis(selectedFileName, true);
    } catch (err) {
      console.error("Failed to start video:", err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Upload to backend video endpoint
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/api/v1/video/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.path) {
        setSelectedFileName(data.path);
        await startAnalysis(data.path, true);
      }
    } catch (err) {
      console.error("Upload error:", err);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg overflow-hidden font-mono shadow-sm">
      {/* Top Video Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#FFFFFF] border-b border-[#D9DEE7] text-xs text-[#5B6472]">
        <div className="flex items-center space-x-2">
          <span
            className={`w-2 h-2 rounded-full ${
              activeSessionId ? "bg-[#0066FF] animate-pulse" : "bg-[#D9DEE7]"
            }`}
          />
          <span className="font-bold tracking-wider uppercase text-[#111827]">
            VIDEO ENGINE: {activeSessionId ? "PROCESSING" : "STANDBY"}
          </span>
          {activeSessionId && (
            <span className="text-[10px] bg-[#EAF3FF] text-[#0066FF] px-1.5 py-0.5 rounded border border-[#0066FF]/30">
              {activeSessionId}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {!activeSessionId ? (
            <button
              onClick={handleStartDemoVideo}
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-[#0066FF] hover:bg-[#008CFF] text-white font-bold transition shadow-sm shadow-[#0066FF]/20"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Start Runway Video Analysis
            </button>
          ) : (
            <button
              onClick={stopAnalysis}
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-red-50 hover:bg-red-100 text-red-600 border border-red-300 font-bold transition shadow"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              Stop Analysis
            </button>
          )}

          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:bg-[#F0F6FF] text-[#111827] transition font-medium"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload Video
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="video/*"
            className="hidden"
          />
        </div>
      </div>

      {/* Main Video Viewport */}
      <div
        ref={containerRef}
        className="relative flex-1 bg-[#000000] flex items-center justify-center overflow-hidden min-h-[360px]"
      >
        {videoFrame ? (
          <img
            src={videoFrame}
            alt="AI Annotated Frame"
            onLoad={(e) => {
              const target = e.currentTarget;
              setVideoDims({ width: target.naturalWidth, height: target.naturalHeight });
            }}
            className="max-w-full max-h-full object-contain"
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-center text-[#EAF3FF] space-y-3">
            <div className="w-24 h-24 border border-white/20 rounded-full flex items-center justify-center text-[#EAF3FF]">
              <Film className="w-10 h-10 stroke-[1.5]" />
            </div>
            <div className="font-bold text-sm text-white uppercase tracking-widest">
              Server-Side Frame Inference Ready
            </div>
            <p className="text-xs max-w-sm text-[#EAF3FF]">
              Click &quot;Start Runway Video Analysis&quot; to begin frame-by-frame YOLOv11 inference
              on the runway dataset with persistent object tracking.
            </p>
            <button
              onClick={handleStartDemoVideo}
              className="px-4 py-2 rounded bg-[#0066FF] hover:bg-[#008CFF] text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-[#0066FF]/30"
            >
              Launch Demo Video Analysis
            </button>
          </div>
        )}

        {/* Real-time Bounding Box Overlay if raw frame is rendered without backend annotations */}
        {!videoFrame && detections.length > 0 && (
          <DetectionCanvas
            videoWidth={videoDims.width}
            videoHeight={videoDims.height}
            containerWidth={containerDims.width}
            containerHeight={containerDims.height}
          />
        )}

        {/* Real Performance HUD Overlay */}
        <div className="absolute top-3 left-3 z-20 flex items-center space-x-2 text-[10px] font-mono select-none">
          <div className="px-2 py-1 rounded bg-[#000000]/80 border border-white/20 text-[#EAF3FF] backdrop-blur-sm">
            STREAM FPS: <span className="text-[#008CFF] font-bold">{performance?.stream_fps ?? 30}</span>
          </div>
          <div className="px-2 py-1 rounded bg-[#000000]/80 border border-white/20 text-[#EAF3FF] backdrop-blur-sm">
            INFERENCE FPS: <span className="text-[#008CFF] font-bold">{performance?.inference_fps ?? 3.0}</span>
          </div>
          <div className="px-2 py-1 rounded bg-[#000000]/80 border border-white/20 text-[#EAF3FF] backdrop-blur-sm">
            LATENCY: <span className="text-white font-bold">{Math.round(performance?.inference_ms ?? 327)} ms</span>
          </div>
        </div>

        {error && (
          <div className="absolute bottom-3 left-3 z-20 flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#000000] border border-red-700 text-red-200 text-xs shadow-lg">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoPlayer;
