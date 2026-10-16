"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogIn, LogOut, User as UserIcon } from "lucide-react";
import { useDroneStore } from "../../stores/droneStore";
import { useAuthStore } from "../../stores/authStore";

export const TopBar: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();
  const connectionStatus = useDroneStore((s) => s.connectionStatus);

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };


  const drone = useDroneStore((s) => s.drone);
  const mission = useDroneStore((s) => s.mission);
  const activeCameraId = useDroneStore((s) => s.activeCameraId);
  const cameraStatus = useDroneStore((s) => s.cameraStatus);
  const inferenceFps = useDroneStore((s) => s.inferenceFps);
  const activeModel = useDroneStore((s) => s.activeModel);
  const modelStatus = useDroneStore((s) => s.modelStatus);
  const fetchModelStatus = useDroneStore((s) => s.fetchModelStatus);
  const alerts = useDroneStore((s) => s.alerts);
  const [timeStr, setTimeStr] = useState<string>("");

  const hasFodAlert = alerts.some((a) => a.event_type === "FOD_DETECTED");
  const hasLightFaultAlert = alerts.some((a) => a.event_type === "RUNWAY_LIGHT_FAULT");

  useEffect(() => {
    fetchModelStatus();
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toTimeString().split(" ")[0]);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [fetchModelStatus]);



  const isOnline = connectionStatus === "CONNECTED"

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-[#FFFFFF] border-b border-[#D9DEE7] text-[#111827] select-none">
      <div className="flex items-center space-x-4">
        <Link
          href="/"
          className="flex items-center space-x-2.5 group flex-shrink-0"
          title="Garuda Aerospace — Runway Safety"
        >
          <div className="w-9 h-9 sm:w-10 sm:h-10 relative flex items-center justify-center flex-shrink-0">
            <img
              src="/garuda_logo.png"
              alt="Garuda Aerospace Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <div className="flex flex-col justify-center items-start text-left select-none">
            <span className="font-bold text-xs sm:text-[13px] tracking-tight text-[#0A2558] leading-tight">
              Garuda
            </span>
            <span className="font-bold text-xs sm:text-[13px] tracking-tight text-[#0066FF] leading-tight">
              Aerospace
            </span>
            <span className="font-bold text-[8.5px] sm:text-[9px] tracking-[0.16em] uppercase text-[#0A2558] leading-tight mt-0.5">
              RUNWAY SAFETY
            </span>
          </div>
        </Link>


        <span className="text-[#D9DEE7]">|</span>

        {/* System Online Indicator */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#EAF3FF] border border-[#0066FF]/30 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-pulse" />
          <span className="text-[#111827] font-bold tracking-wider text-[11px]">
            SYSTEM <span className="text-[#0066FF]">ONLINE</span>
          </span>
        </div>

        <span className="text-[#D9DEE7]">|</span>

        <div className="text-xs text-[#5B6472] font-mono">
          DRONE:{" "}
          <span className={drone ? "text-[#111827] font-semibold" : "text-[#5B6472] font-semibold"}>
            {drone ? drone.name : "NOT CONNECTED"}
          </span>
        </div>

        <div className="text-xs text-[#5B6472] font-mono">
          MISSION:{" "}
          <span className={mission ? "text-[#0066FF] font-semibold" : "text-[#5B6472] font-semibold"}>
            {mission ? mission.name : "STANDBY"}
          </span>
        </div>


        {activeCameraId && (
          <>
            <span className="text-[#D9DEE7]">|</span>
            <div className="flex items-center space-x-1.5 text-xs text-[#5B6472] font-mono">
              <span className="text-[#5B6472]">CAM:</span>
              <span className="text-[#111827] font-semibold">{activeCameraId}</span>
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  cameraStatus === "LIVE" || cameraStatus === "CONNECTED"
                    ? "bg-[#0066FF] animate-pulse"
                    : cameraStatus === "RECONNECTING" || cameraStatus === "CONNECTING"
                    ? "bg-[#008CFF] animate-ping"
                    : "bg-red-500"
                }`}
              />
            </div>
          </>
        )}
      </div>

      <div className="flex items-center space-x-4">
        {/* Navigation HUD Status Badges */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <div className="flex items-center space-x-1.5 px-2 py-1 rounded bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] transition-colors">
            <span className="text-[#5B6472]">CAMERA:</span>
            <span className={activeCameraId && (cameraStatus === "CONNECTED" || cameraStatus === "LIVE") ? "text-[#0066FF] font-bold" : "text-[#5B6472]"}>
              {activeCameraId ? cameraStatus : "READY"}
            </span>
          </div>

          <div className="flex items-center space-x-1.5 px-2 py-1 rounded bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] transition-colors">
            <span className="text-[#5B6472]">MODEL:</span>
            <span className="text-[#0066FF] font-bold truncate max-w-[150px]" title={activeModel}>
              {activeModel}
            </span>
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                modelStatus === "READY" || modelStatus === "RUNNING"
                  ? "bg-[#0066FF] animate-pulse"
                  : modelStatus === "LOADING"
                  ? "bg-[#008CFF] animate-pulse"
                  : "bg-red-500"
              }`}
            />
            <span className="text-[10px] text-[#5B6472] font-semibold">{modelStatus}</span>
          </div>

          <div className="flex items-center space-x-1.5 px-2 py-1 rounded bg-[#F5F7FA] border border-[#D9DEE7] hover:border-[#0066FF] transition-colors">
            <span className="text-[#5B6472]">FPS:</span>
            <span className="text-[#0066FF] font-bold font-mono">
              {inferenceFps ? Number(inferenceFps).toFixed(1) : "0.0"}
            </span>
          </div>

          {hasFodAlert && (
            <div className="flex items-center space-x-1 px-2 py-1 rounded bg-red-50 border border-red-300 text-red-600 font-bold animate-pulse text-[11px]">
              <span>⚠</span>
              <span>FOD DETECTED</span>
            </div>
          )}

          {hasLightFaultAlert && (
            <div className="flex items-center space-x-1 px-2 py-1 rounded bg-amber-50 border border-amber-300 text-amber-700 font-bold animate-pulse text-[11px]">
              <span>⚠</span>
              <span>RUNWAY LIGHT FAULT</span>
            </div>
          )}
        </div>

        <div className="font-mono text-xs text-[#5B6472] tracking-wider">
          {timeStr} UTC
        </div>

        <span className="text-[#D9DEE7]">|</span>

        {/* Operator Profile / Auth Indicator */}
        {isAuthenticated && user ? (
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#F5F7FA] border border-[#D9DEE7] text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <UserIcon className="w-3.5 h-3.5 text-[#5B6472]" />
              <span className="text-[#111827] font-semibold truncate max-w-[120px]" title={user.email}>
                {user.name || user.email.split("@")[0]}
              </span>
              <span className="text-[10px] text-[#0066FF] font-bold">({user.role})</span>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="px-2 py-1 rounded text-xs font-mono font-semibold text-[#5B6472] hover:text-red-600 hover:bg-red-50 border border-[#D9DEE7] hover:border-red-200 transition-colors flex items-center space-x-1"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>SIGN OUT</span>
            </button>

          </div>
        ) : (
          <Link
            href="/login"
            className="px-2.5 py-1 rounded bg-[#0066FF] hover:bg-[#0052CC] text-white text-xs font-mono font-semibold transition-all flex items-center space-x-1.5 shadow-sm"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>SIGN IN</span>
          </Link>
        )}
      </div>
    </header>
  );
};
