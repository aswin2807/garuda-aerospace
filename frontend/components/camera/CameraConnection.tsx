"use client";

import React, { useState } from "react";
import { Wifi, Radio, X } from "lucide-react";
import { useCamera } from "../../hooks/useCamera";
import { useDroneStore } from "../../stores/droneStore";

export const CameraConnection: React.FC<{ onClose?: () => void }> = ({ onClose }) => {
  const [streamUrl, setStreamUrl] = useState("rtsp://192.168.144.108:554/stream=1");
  const [cameraId, setCameraId] = useState("drone-camera-01");
  const [isSimulated, setIsSimulated] = useState(false);

  const { connect, isConnecting, error } = useCamera();
  const setMode = useDroneStore((s) => s.setActiveCameraId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await connect({
        camera_id: cameraId,
        stream_url: streamUrl,
        is_simulated: isSimulated,
      });
      if (onClose) onClose();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-4 bg-[#FFFFFF] border border-[#D9DEE7] rounded-lg font-mono text-xs text-[#111827] max-w-md w-full shadow-lg">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2 mb-3">
        <span className="font-bold uppercase tracking-wider text-[#0066FF] flex items-center gap-1.5">
          <Wifi className="w-4 h-4" />
          Connect Live Camera / RTSP
        </span>
        {onClose && (
          <button onClick={onClose} className="p-1 text-[#5B6472] hover:text-[#111827]">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-[10px] text-[#5B6472] uppercase mb-1">Camera ID</label>
          <input
            type="text"
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-2.5 py-1.5 text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono text-xs"
            required
          />
        </div>

        <div>
          <label className="block text-[10px] text-[#5B6472] uppercase mb-1">RTSP Stream URL</label>
          <input
            type="text"
            value={streamUrl}
            onChange={(e) => setStreamUrl(e.target.value)}
            className="w-full bg-[#F5F7FA] border border-[#D9DEE7] rounded px-2.5 py-1.5 text-[#111827] focus:outline-none focus:border-[#0066FF] font-mono text-xs"
            required
          />
        </div>

        <div className="flex items-center space-x-2 pt-1">
          <input
            type="checkbox"
            id="simulatedCheck"
            checked={isSimulated}
            onChange={(e) => setIsSimulated(e.target.checked)}
            className="rounded bg-[#FFFFFF] border-[#D9DEE7] accent-[#0066FF]"
          />
          <label htmlFor="simulatedCheck" className="text-[11px] text-[#5B6472]">
            Use simulated local test feed if offline
          </label>
        </div>

        {error && (
          <div className="p-2 rounded bg-red-50 border border-red-200 text-red-600 text-[11px]">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end space-x-2 pt-2 border-t border-[#D9DEE7]">
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-[#FFFFFF] border border-[#D9DEE7] hover:bg-[#F0F6FF] text-[#5B6472] transition"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={isConnecting}
            className="px-4 py-1.5 rounded bg-[#0066FF] hover:bg-[#008CFF] text-white font-bold transition flex items-center gap-1.5 disabled:opacity-50 shadow-sm shadow-[#0066FF]/20"
          >
            {isConnecting ? "Connecting..." : "Connect Stream"}
          </button>
        </div>
      </form>
    </div>
  );
};
