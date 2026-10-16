"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Navigation,
  AlertTriangle,
  Lightbulb,
  Settings,
  Compass,
  FileText,
  Layers,
  History,
  Radio,
  Database,
  LogOut,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

export type SidebarFocusMode = "all" | "navigation" | "fod" | "runway";

interface SidebarProps {
  currentFocus?: SidebarFocusMode;
  onSelectFocus?: (mode: SidebarFocusMode) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentFocus = "all",
  onSelectFocus,
}) => {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);

  const isHome = pathname === "/" || pathname === "/dashboard";


  const handleNavClick = (mode: SidebarFocusMode) => {
    if (onSelectFocus) {
      onSelectFocus(mode);
    }
  };

  return (
    <aside className="w-52 bg-[#FFFFFF] border-r border-[#D9DEE7] flex flex-col justify-between select-none font-mono text-xs z-20 shrink-0">
      <div className="flex flex-col py-3">
        {/* Navigation Category Header */}
        <div className="px-4 pb-2 text-[10px] text-[#5B6472] font-bold tracking-wider uppercase">
          Command Panel
        </div>

        {/* 1. Command Centre */}
        <Link
          href="/"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all text-left w-full ${
            isHome && currentFocus === "all"
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <LayoutDashboard
            className={`w-4 h-4 ${
              isHome && currentFocus === "all" ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Command Centre</span>
        </Link>

        {/* 2. Live Surveillance */}
        <Link
          href="/live-surveillance"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all text-left w-full ${
            pathname === "/live-surveillance"
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <Radio
            className={`w-4 h-4 ${
              pathname === "/live-surveillance" ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Live Surveillance</span>
        </Link>

        {/* 3. Navigation Module */}
        <Link
          href="/navigation"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all text-left w-full ${
            pathname === "/navigation" || (isHome && currentFocus === "navigation")
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <Navigation
            className={`w-4 h-4 ${
              pathname === "/navigation" || (isHome && currentFocus === "navigation") ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Navigation</span>
        </Link>

        {/* 4. FOD Debris Module */}
        <Link
          href="/fod"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all text-left w-full ${
            pathname === "/fod" || (isHome && currentFocus === "fod")
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <AlertTriangle
            className={`w-4 h-4 ${
              pathname === "/fod" || (isHome && currentFocus === "fod") ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">FOD Debris</span>
        </Link>

        {/* 5. Runway Light Module */}
        <Link
          href="/runway-light"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all text-left w-full ${
            pathname === "/runway-light" || (isHome && currentFocus === "runway")
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <Lightbulb
            className={`w-4 h-4 ${
              pathname === "/runway-light" || (isHome && currentFocus === "runway") ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Runway Light</span>
        </Link>

        {/* 6. Analysis History */}
        <Link
          href="/history"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all text-left w-full ${
            pathname === "/history" || pathname.startsWith("/history/") || pathname === "/mission-history"
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <History
            className={`w-4 h-4 ${
              pathname === "/history" || pathname.startsWith("/history/") || pathname === "/mission-history"
                ? "text-[#0066FF]"
                : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Analysis History</span>
        </Link>

        {/* 7. Central Database Results */}
        <Link
          href="/results"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all text-left w-full ${
            pathname === "/results"
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <Database
            className={`w-4 h-4 ${
              pathname === "/results" ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Central Results</span>
        </Link>

        {/* Divider */}
        <div className="my-3 border-t border-[#D9DEE7]" />

        <div className="px-4 pb-2 text-[10px] text-[#5B6472] font-bold tracking-wider uppercase">
          Operations
        </div>

        {/* Missions Link */}
        <Link
          href="/missions"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all ${
            pathname === "/missions"
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <Compass
            className={`w-4 h-4 ${
              pathname === "/missions" ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Flight Missions</span>
        </Link>

        {/* Detections Audit History */}
        <Link
          href="/detections"
          className={`flex items-center space-x-2.5 px-4 py-2.5 transition-all ${
            pathname === "/detections"
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF] border-l-2 border-transparent"
          }`}
        >
          <FileText
            className={`w-4 h-4 ${
              pathname === "/detections" ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Detection Audit</span>
        </Link>
      </div>


      {/* Bottom Settings & Auth Links */}
      <div className="p-3 border-t border-[#D9DEE7] space-y-1">
        <Link
          href="/settings"
          className={`flex items-center space-x-2.5 px-3 py-2 rounded transition-all ${
            pathname === "/settings"
              ? "bg-[#EAF3FF] text-[#0066FF] border-l-2 border-[#0066FF]"
              : "text-[#111827] hover:text-[#0066FF] hover:bg-[#F0F6FF]"
          }`}
        >
          <Settings
            className={`w-4 h-4 ${
              pathname === "/settings" ? "text-[#0066FF]" : "text-[#5B6472]"
            }`}
          />
          <span className="font-semibold">Settings</span>
        </Link>

        <button
          type="button"
          onClick={async () => {
            await logout();
            router.replace("/login");
          }}
          className="flex items-center space-x-2.5 px-3 py-2 rounded transition-all w-full text-left text-[#111827] hover:text-red-600 hover:bg-red-50"
        >
          <LogOut className="w-4 h-4 text-[#5B6472]" />
          <span className="font-semibold">Sign Out</span>
        </button>
      </div>
    </aside>
  );
};


export default Sidebar;
