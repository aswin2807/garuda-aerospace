"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

const PUBLIC_PATHS = ["/login", "/register", "/verify-email", "/forgot-password", "/reset-password"];

export const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const { isAuthenticated, isCheckingAuth, hasInitialized, initAuth, logout } =
    useAuthStore();

  const isPublicRoute = PUBLIC_PATHS.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  useEffect(() => {
    const handleSessionExpired = async () => {
      await logout();
      router.replace("/login?expired=1");
    };
    window.addEventListener("garuda:session-expired", handleSessionExpired);
    return () => {
      window.removeEventListener("garuda:session-expired", handleSessionExpired);
    };
  }, [logout, router]);

  useEffect(() => {
    if (!hasInitialized || isCheckingAuth) return;

    if (!isPublicRoute && !isAuthenticated) {
      const target =
        pathname !== "/" && pathname !== "/dashboard"
          ? `/login?redirect=${encodeURIComponent(pathname)}`
          : "/login";
      router.replace(target);
    }
  }, [hasInitialized, isCheckingAuth, isPublicRoute, isAuthenticated, pathname, router]);

  if (isPublicRoute) {
    return <>{children}</>;
  }

  if (!hasInitialized || isCheckingAuth || !isAuthenticated) {
    return (
      <div className="min-h-screen w-full bg-[#F8FAFC] flex flex-col items-center justify-center p-6 select-none">
        <div className="flex items-center space-x-3 mb-4">
          <img
            src="/garuda_logo.png"
            alt="Garuda Aerospace"
            className="w-11 h-11 object-contain"
          />
          <div className="flex flex-col justify-center items-start text-left select-none">
            <span className="text-base font-bold tracking-tight text-[#0A2558] leading-tight">
              Garuda
            </span>
            <span className="text-base font-bold tracking-tight text-[#0066FF] leading-tight">
              Aerospace
            </span>
            <span className="text-[9px] font-bold tracking-[0.16em] uppercase text-[#0A2558] leading-tight mt-0.5">
              RUNWAY SAFETY
            </span>
          </div>
        </div>
        <div className="flex items-center space-x-2 text-xs font-medium text-[#64748B]">
          <Loader2 className="w-4 h-4 text-[#0A3981] animate-spin" />
          <span>Verifying security session...</span>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default AuthGuard;
