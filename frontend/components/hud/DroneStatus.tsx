"use client";

import React, { useEffect, useState } from "react";
import { useDroneStore } from "../../stores/droneStore";

export const DroneStatus: React.FC = () => {
  const drone = useDroneStore((s) => s.drone);
  const telemetry = useDroneStore((s) => s.telemetry);
  const connectionStatus = useDroneStore((s) => s.connectionStatus);
  const activeCameraId = useDroneStore((s) => s.activeCameraId);
  const cameraStatus = useDroneStore((s) => s.cameraStatus);
  const cameraInfo = useDroneStore((s) => s.cameraInfo);
  const fetchCommandCentreStatus = useDroneStore((s) => s.fetchCommandCentreStatus);
  const connectDroneAction = useDroneStore((s) => s.connectDroneAction);
  const disconnectDroneAction = useDroneStore((s) => s.disconnectDroneAction);

  // Model State & Actions
  const activeModel = useDroneStore((s) => s.activeModel);
  const modelStatus = useDroneStore((s) => s.modelStatus);
  const modelClasses = useDroneStore((s) => s.modelClasses);
  const modelDevice = useDroneStore((s) => s.modelDevice);
  const modelError = useDroneStore((s) => s.modelError);
  const availableModels = useDroneStore((s) => s.availableModels);
  const fetchAvailableModels = useDroneStore((s) => s.fetchAvailableModels);
  const fetchModelStatus = useDroneStore((s) => s.fetchModelStatus);
  const switchModel = useDroneStore((s) => s.switchModel);

  const [isSwitching, setIsSwitching] = useState<boolean>(false);

  useEffect(() => {
    fetchModelStatus();
    fetchAvailableModels();
    fetchCommandCentreStatus();
    const interval = setInterval(() => {
      fetchCommandCentreStatus();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchModelStatus, fetchAvailableModels, fetchCommandCentreStatus]);

  const handleModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = e.target.value;
    if (!selected || selected === activeModel) return;
    setIsSwitching(true);
    await switchModel(selected);
    setIsSwitching(false);
  };

  const isConnected = connectionStatus === "CONNECTED" && drone !== null;
  const battery = isConnected && telemetry?.battery !== undefined ? telemetry.battery : null;
  const isBatteryLow = battery !== null && battery < 25;

  return (
    <div className="flex flex-col space-y-4 p-4 bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] hover:shadow-[0_2px_8px_rgba(0,102,255,0.15)] rounded-lg text-[#111827] font-mono text-xs select-none transition-all">
      <div className="flex items-center justify-between border-b border-[#D9DEE7] pb-2">
        <span className="font-bold tracking-wider text-[#111827]">DRONE STATUS</span>
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
            isConnected
              ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30"
              : "bg-[#F5F7FA] text-[#5B6472] border border-[#D9DEE7]"
          }`}
        >
          {isConnected ? drone.status || "CONNECTED" : "DISCONNECTED"}
        </span>
      </div>

      {/* Disconnected Notice Banner */}
      {!isConnected ? (
        <div className="p-2.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded text-[11px] flex items-center justify-between">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#5B6472]" />
            <span className="font-bold text-[#5B6472]">DRONE NOT CONNECTED</span>
          </div>
          <button
            onClick={() => connectDroneAction()}
            className="px-2 py-0.5 bg-[#0066FF] text-white text-[10px] font-bold rounded hover:bg-[#008CFF] transition"
          >
            Connect
          </button>
        </div>
      ) : (
        <div className="flex justify-between items-center text-[11px] bg-[#EAF3FF] p-2 rounded border border-[#0066FF]/20">
          <span className="text-[#0066FF] font-bold">{drone.name}</span>
          <button
            onClick={() => disconnectDroneAction()}
            className="text-[10px] text-red-600 hover:underline"
          >
            Disconnect
          </button>
        </div>
      )}

      {/* Battery Gauge */}
      <div className="space-y-1">
        <div className="flex justify-between items-center text-[#5B6472]">
          <span>BATTERY</span>
          <span className={`font-bold ${battery === null ? "text-[#5B6472]" : isBatteryLow ? "text-red-500 animate-pulse" : "text-[#0066FF]"}`}>
            {battery !== null ? `${battery.toFixed(0)}%` : "N/A"}
          </span>
        </div>
        <div className="w-full h-2 bg-[#E5E7EB] border border-[#D9DEE7] rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              battery === null ? "bg-transparent" : isBatteryLow ? "bg-red-500" : "bg-[#0066FF]"
            }`}
            style={{ width: battery !== null ? `${Math.min(100, Math.max(0, battery))}%` : "0%" }}
          />
        </div>
      </div>

      {/* Telemetry Grid */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">Altitude</div>
          <div className="text-sm font-bold text-[#111827]">
            {isConnected && telemetry?.altitude !== undefined ? (
              <>
                {telemetry.altitude.toFixed(0)} <span className="text-[10px] font-normal text-[#5B6472]">m</span>
              </>
            ) : (
              <span className="text-[#5B6472] font-normal">N/A</span>
            )}
          </div>
        </div>

        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">Speed</div>
          <div className="text-sm font-bold text-[#111827]">
            {isConnected && telemetry?.speed !== undefined ? (
              <>
                {telemetry.speed.toFixed(0)} <span className="text-[10px] font-normal text-[#5B6472]">km/h</span>
              </>
            ) : (
              <span className="text-[#5B6472] font-normal">N/A</span>
            )}
          </div>
        </div>

        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">Heading</div>
          <div className="text-sm font-bold text-[#111827]">
            {isConnected && telemetry?.heading !== undefined ? (
              `${telemetry.heading.toFixed(0)}°`
            ) : (
              <span className="text-[#5B6472] font-normal">N/A</span>
            )}
          </div>
        </div>

        <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded">
          <div className="text-[10px] text-[#5B6472] uppercase">GPS Lock</div>
          <div className={`text-sm font-bold ${isConnected ? "text-[#0066FF]" : "text-[#5B6472] font-normal"}`}>
            {isConnected ? "3D FIX (18 SV)" : "NO FIX"}
          </div>
        </div>
      </div>

      {/* Coordinates */}
      <div className="p-2 bg-[#F5F7FA] border border-[#D9DEE7] rounded text-[11px] space-y-1">
        <div className="flex justify-between">
          <span className="text-[#5B6472]">LAT:</span>
          <span className="text-[#111827]">
            {isConnected && telemetry?.latitude !== undefined ? `${telemetry.latitude.toFixed(4)}° N` : "N/A"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#5B6472]">LNG:</span>
          <span className="text-[#111827]">
            {isConnected && telemetry?.longitude !== undefined ? `${telemetry.longitude.toFixed(4)}° E` : "N/A"}
          </span>
        </div>
      </div>


      {/* Payload Camera Status */}
      <div className="p-2.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded text-[11px] space-y-1.5">
        <div className="flex justify-between items-center">
          <span className="text-[10px] text-[#5B6472] uppercase tracking-wider font-bold">Payload Camera</span>
          <span
            className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
              cameraStatus === "LIVE" || cameraStatus === "CONNECTED"
                ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30"
                : cameraStatus === "RECONNECTING" || cameraStatus === "CONNECTING"
                ? "bg-[#EAF3FF] text-[#008CFF] border border-[#008CFF]/30"
                : "bg-[#FFFFFF] text-[#5B6472] border border-[#D9DEE7]"
            }`}
          >
            {cameraStatus}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#5B6472]">DEVICE:</span>
          <span className="text-[#111827] truncate max-w-[130px] font-mono">
            {activeCameraId || "None"}
          </span>
        </div>
        {cameraInfo?.stream_url && (
          <div className="flex justify-between">
            <span className="text-[#5B6472]">URL:</span>
            <span className="text-[#5B6472] truncate max-w-[130px] text-[10px] font-mono">
              {cameraInfo.stream_url}
            </span>
          </div>
        )}
      </div>

      {/* AI Model Management */}
      <div className="p-2.5 bg-[#F5F7FA] border border-[#D9DEE7] rounded text-[11px] space-y-2">
        <div className="flex justify-between items-center border-b border-[#D9DEE7] pb-1.5">
          <div className="flex items-center space-x-1.5">
            <span className="text-[10px] text-[#111827] uppercase tracking-wider font-bold">MODEL STATUS</span>
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                modelStatus === "READY" || modelStatus === "RUNNING"
                  ? "bg-[#0066FF] animate-pulse"
                  : modelStatus === "LOADING"
                  ? "bg-[#008CFF] animate-ping"
                  : "bg-red-500"
              }`}
            />
          </div>
          <span
            className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
              modelStatus === "READY" || modelStatus === "RUNNING"
                ? "bg-[#EAF3FF] text-[#0066FF] border border-[#0066FF]/30"
                : modelStatus === "LOADING"
                ? "bg-[#EAF3FF] text-[#008CFF] border border-[#008CFF]/30"
                : "bg-red-50 text-red-600 border border-red-200"
            }`}
          >
            {isSwitching ? "SWITCHING..." : modelStatus}
          </span>
        </div>

        {/* Model Selector Dropdown */}
        <div className="space-y-1">
          <div className="flex justify-between items-center text-[10px] text-[#5B6472]">
            <span>ACTIVE MODEL:</span>
            <span className="text-[#111827] font-mono">{modelDevice}</span>
          </div>
          <div className="relative">
            <select
              value={activeModel}
              onChange={handleModelChange}
              disabled={isSwitching}
              className="w-full bg-[#FFFFFF] border border-[#D9DEE7] hover:border-[#0066FF] focus:border-[#0066FF] rounded px-2 py-1 text-xs text-[#0066FF] font-mono focus:outline-none cursor-pointer disabled:opacity-50"
            >
              {availableModels.length > 0 ? (
                availableModels.map((m) => (
                  <option key={m.model_name} value={m.model_name}>
                    {m.model_name} {m.is_active ? "★ (Active)" : `(${m.size_mb.toFixed(1)}MB)`}
                  </option>
                ))
              ) : (
                <>
                  <option value="FOD_Karhtikeyan.pt">FOD_Karhtikeyan.pt (Default)</option>
                  <option value="best.pt">best.pt</option>
                  <option value="yolo11n.pt">yolo11n.pt</option>
                </>
              )}
            </select>
          </div>
        </div>

        {/* Dynamic Model Classes */}
        <div className="space-y-1">
          <span className="text-[10px] text-[#5B6472] uppercase font-semibold">Trained Classes:</span>
          <div className="flex flex-wrap gap-1">
            {Object.entries(modelClasses).length > 0 ? (
              Object.entries(modelClasses).map(([idx, name]) => (
                <span
                  key={idx}
                  className="px-1.5 py-0.5 rounded text-[9px] bg-[#FFFFFF] border border-[#D9DEE7] text-[#111827] font-mono"
                >
                  {name}
                </span>
              ))
            ) : (
              <span className="text-[#5B6472] text-[10px]">None loaded</span>
            )}
          </div>
        </div>

        {modelError && (
          <div className="p-1.5 bg-red-50 border border-red-200 rounded text-[10px] text-red-600">
            {modelError}
          </div>
        )}
      </div>
    </div>
  );
};

export default DroneStatus;
