"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Check,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTarget = searchParams.get("redirect") || "/dashboard";
  const isExpiredSession = searchParams.get("expired") === "1";
  const isPasswordReset = searchParams.get("reset") === "1";

  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);

  const isGoogleAuthConfigured =
    process.env.NEXT_PUBLIC_GOOGLE_AUTH_ENABLED === "true";

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(redirectTarget);
    }
  }, [isAuthenticated, router, redirectTarget]);

  const validateEmailFormat = (value: string) => {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    setLocalError(null);
    clearError();

    const trimmedEmail = email.trim();
    if (!trimmedEmail && !password) {
      setLocalError("Please enter your email address and password.");
      return;
    }
    if (!trimmedEmail) {
      setLocalError("Please enter your email address.");
      return;
    }
    if (!validateEmailFormat(trimmedEmail)) {
      setLocalError("Please enter a valid email address.");
      return;
    }
    if (!password) {
      setLocalError("Please enter your password.");
      return;
    }

    const success = await login(trimmedEmail, password, rememberMe);
    if (success) {
      router.replace(redirectTarget);
    }
  };

  const displayError =
    localError ||
    error ||
    (isExpiredSession ? "Your session has expired. Please sign in again." : null);

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#F8FAFC] font-sans overflow-x-hidden select-none">
      {/* LEFT PANEL — Branding, Runway & Drone Imagery, and 5 Feature Modules */}
      <div className="relative w-full lg:w-[52%] xl:w-[53%] min-h-[340px] sm:min-h-[420px] lg:min-h-screen flex flex-col justify-between overflow-hidden bg-[#0A1833]">
        {/* Runway & Drone Background Image */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: "url('/runway_drone_bg.jpg')" }}
          aria-hidden="true"
        />

        {/* Subtle Top & Bottom Legibility Gradients */}
        <div
          className="absolute inset-x-0 top-0 h-44 bg-gradient-to-b from-[#7CA5D6]/30 via-transparent to-transparent pointer-events-none"
          aria-hidden="true"
        />
        <div
          className="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-t from-[#061024]/95 via-[#07142B]/80 to-transparent pointer-events-none"
          aria-hidden="true"
        />

        {/* Subtle Bottom-Left Wing Watermark */}
        <svg
          className="absolute bottom-0 left-0 w-44 h-44 text-white/[0.04] pointer-events-none hidden lg:block"
          viewBox="0 0 200 200"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M0 110 L95 145 L75 162 L0 135 Z M0 145 L125 185 L105 200 L0 168 Z M0 80 L65 105 L50 120 L0 100 Z" />
        </svg>

        {/* Top Branding & Tagline */}
        <div className="relative z-10 pt-8 sm:pt-12 lg:pt-16 px-6 sm:px-10 text-center flex flex-col items-center">
          <div className="flex items-center justify-center space-x-3 sm:space-x-3.5">
            <img
              src="/garuda_logo.png"
              alt="Garuda Aerospace Logo"
              className="w-10 h-10 sm:w-12 sm:h-12 object-contain drop-shadow-sm"
            />
            <span className="text-2xl sm:text-3xl lg:text-[34px] font-bold tracking-tight text-[#0D2658]">
              Garuda Aerospace
            </span>
          </div>

          <p className="mt-3 sm:mt-4 text-xs sm:text-sm lg:text-[15px] font-medium text-[#233B66] tracking-wide">
            Safer Skies <span className="mx-1.5 sm:mx-2.5 text-[#3B5988]">|</span>{" "}
            Smarter Surveillance{" "}
            <span className="mx-1.5 sm:mx-2.5 text-[#3B5988]">|</span> A Safer
            Tomorrow
          </p>
        </div>

        {/* Bottom 4 Feature Labels with Icons */}
        <div className="relative z-10 pb-6 sm:pb-8 lg:pb-10 pt-16 px-3 sm:px-6 lg:px-8">
          <div className="max-w-xl mx-auto grid grid-cols-4 divide-x divide-white/15 text-center">
            {/* 1. Navigation */}
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center text-[#7AB8FF] mb-2">
                <svg
                  className="w-6 h-6 sm:w-7 sm:h-7"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 3L5 19l7-3.5L19 19 12 3z" />
                  <path d="M12 15.5V21" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">
                Navigation
              </span>
            </div>

            {/* 2. Rod Debris Detection */}
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center text-[#7AB8FF] mb-2">
                <svg
                  className="w-6 h-6 sm:w-7 sm:h-7"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 19L17 5l2 2L7 21 5 19z" />
                  <circle cx="17.5" cy="15.5" r="1" />
                  <path d="M14 18h2" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">
                Rod Debris
                <br />
                Detection
              </span>
            </div>

            {/* 3. Runway Lights Detection */}
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center text-[#7AB8FF] mb-2">
                <svg
                  className="w-6 h-6 sm:w-7 sm:h-7"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M9 4L4 20" />
                  <path d="M15 4l5 16" />
                  <path d="M12 5v3" />
                  <path d="M12 11v3" />
                  <path d="M12 17v3" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">
                Runway Lights
                <br />
                Detection
              </span>
            </div>

            {/* 4. Live Surveillance */}
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center text-[#7AB8FF] mb-2">
                <svg
                  className="w-6 h-6 sm:w-7 sm:h-7"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="6" y="7" width="12" height="10" rx="3" />
                  <circle cx="12" cy="12" r="2.5" />
                  <path d="M3 10v4" />
                  <path d="M21 10v4" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">
                Live Surveillance
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT PANEL — Authentication Form */}
      <div className="relative w-full lg:w-[48%] xl:w-[47%] flex-1 flex flex-col justify-center items-center px-6 sm:px-12 lg:px-16 py-10 lg:py-12 bg-[#F8FAFC] overflow-hidden">
        {/* Subtle Top-Right Geometric Wing Accent matching Reference */}
        <svg
          className="absolute top-0 right-0 w-48 sm:w-64 h-40 sm:h-52 text-[#E5E9F0] pointer-events-none"
          viewBox="0 0 260 200"
          fill="currentColor"
          aria-hidden="true"
        >
          <polygon points="90,0 260,0 260,40 45,40" />
          <polygon points="135,55 260,55 260,92 95,92" />
          <polygon points="180,108 260,108 260,142 145,142" />
        </svg>

        <div className="relative z-10 w-full max-w-[400px]">
          {/* Garuda Aerospace Brand Header */}
          <div className="flex items-center space-x-3 mb-8">
            <img
              src="/garuda_logo.png"
              alt="Garuda Aerospace Logo"
              className="w-10 h-10 object-contain"
            />
            <span className="text-2xl sm:text-[26px] font-bold tracking-tight text-[#0A2558]">
              Garuda Aerospace
            </span>
          </div>

          {/* Welcome Back Heading */}
          <div className="mb-7">
            <h1 className="text-2xl sm:text-[28px] font-bold text-[#0F172A] tracking-tight">
              Welcome Back
            </h1>
            <p className="text-sm text-[#64748B] mt-1.5">
              Sign in to your account to continue
            </p>
          </div>

          {/* Password Reset Success Banner */}
          {isPasswordReset && !displayError && (
            <div className="mb-5 p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-start space-x-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <span className="font-medium leading-relaxed">
                Your password has been updated. Please sign in with your new password.
              </span>
            </div>
          )}

          {/* Error / Alert Banner */}
          {displayError && (
            <div
              role="alert"
              className="mb-5 p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start space-x-2.5"
            >
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <span className="font-medium leading-relaxed">{displayError}</span>
            </div>
          )}

          {/* Sign In Form */}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Email Address Field */}
            <div>
              <label htmlFor="login-email" className="sr-only">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                  <Mail className="w-[18px] h-[18px]" strokeWidth={1.75} />
                </div>
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (localError) setLocalError(null);
                    if (error) clearError();
                  }}
                  placeholder="Email Address"
                  className="w-full h-12 pl-11 pr-4 bg-[#F3F6F9] border border-[#DCE3EC] rounded-lg text-sm text-[#0F172A] placeholder-[#7B8A9E] focus:outline-none focus:bg-white focus:border-[#0A3981] focus:ring-2 focus:ring-[#0A3981]/15 transition-all"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="login-password" className="sr-only">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                  <Lock className="w-[18px] h-[18px]" strokeWidth={1.75} />
                </div>
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (localError) setLocalError(null);
                    if (error) clearError();
                  }}
                  placeholder="Password"
                  className="w-full h-12 pl-11 pr-11 bg-[#F3F6F9] border border-[#DCE3EC] rounded-lg text-sm text-[#0F172A] placeholder-[#7B8A9E] focus:outline-none focus:bg-white focus:border-[#0A3981] focus:ring-2 focus:ring-[#0A3981]/15 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#64748B] hover:text-[#0F172A] transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <Eye className="w-[18px] h-[18px]" strokeWidth={1.75} />
                  ) : (
                    <EyeOff className="w-[18px] h-[18px]" strokeWidth={1.75} />
                  )}
                </button>
              </div>
            </div>

            {/* Remember Me & Forgot Password Row */}
            <div className="flex items-center justify-between pt-1 pb-1">
              <label className="inline-flex items-center space-x-2.5 cursor-pointer">
                <span className="relative flex items-center justify-center">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="peer sr-only"
                  />
                  <span className="w-[18px] h-[18px] rounded bg-white border border-[#CBD5E1] peer-checked:bg-[#155EEF] peer-checked:border-[#155EEF] transition-colors flex items-center justify-center">
                    {rememberMe && (
                      <Check className="w-3 h-3 text-white" strokeWidth={3} />
                    )}
                  </span>
                </span>
                <span className="text-xs font-semibold text-[#1E293B]">
                  Remember me
                </span>
              </label>

              <Link
                href="/forgot-password"
                className="text-xs font-semibold text-[#1E40AF] hover:text-[#0A3981] hover:underline transition-colors"
              >
                Forgot Password?
              </Link>
            </div>

            {/* Sign In Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 rounded-lg bg-[#0A3981] hover:bg-[#082D66] active:bg-[#06214D] text-white text-sm font-semibold tracking-wide shadow-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Signing In...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            {/* Create Account Link below Sign In button */}
            <div className="pt-2 text-center">
              <p className="text-xs text-[#475569]">
                Don&apos;t have an account?{" "}
                <Link
                  href="/register"
                  className="font-semibold text-[#1E40AF] hover:text-[#0A3981] hover:underline transition-colors"
                >
                  Create Account
                </Link>
              </p>
            </div>
          </form>

          {/* Optional Google Sign-In (only rendered when configured in environment) */}
          {isGoogleAuthConfigured && (
            <>
              <div className="relative my-6 flex items-center justify-center">
                <div className="border-t border-[#E2E8F0] w-full" />
                <span className="bg-[#F8FAFC] px-3 text-xs font-medium text-[#64748B]">
                  OR
                </span>
                <div className="border-t border-[#E2E8F0] w-full" />
              </div>

              <button
                type="button"
                className="w-full h-11 rounded-lg bg-white hover:bg-[#F1F5F9] border border-[#DCE3EC] text-[#1E293B] text-xs font-semibold transition-all flex items-center justify-center space-x-2.5 shadow-sm"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>
            </>
          )}

          {/* Authorized Users Notice */}
          <p className="mt-8 text-center text-xs text-[#64748B]">
            For authorized users only. All activities are monitored.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full bg-[#F8FAFC] flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-[#0A3981] animate-spin" />
        </div>
      }
    >
      <LoginFormContent />
    </Suspense>
  );
}
