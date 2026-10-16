"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading, error, clearError } = useAuthStore();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, router]);

  const validateEmailFormat = (value: string) => {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    setLocalError(null);
    clearError();

    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim();

    if (!trimmedName) {
      setLocalError("Please enter your full name.");
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
    if (!password || password.length === 0) {
      setLocalError("Please enter a password.");
      return;
    }
    if (new TextEncoder().encode(password).length > 72) {
      setLocalError("Password cannot exceed 72 bytes in UTF-8 encoding.");
      return;
    }
    if (password !== confirmPassword) {
      setLocalError("Passwords do not match.");
      return;
    }

    const success = await register(trimmedName, trimmedEmail, password, confirmPassword);
    if (success) {
      router.replace("/dashboard");
    }
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#F8FAFC] font-sans overflow-x-hidden select-none">
      {/* LEFT PANEL — Branding, Runway & Drone Imagery, and 5 Feature Modules */}
      <div className="relative w-full lg:w-[52%] xl:w-[53%] min-h-[280px] sm:min-h-[360px] lg:min-h-screen flex flex-col justify-between overflow-hidden bg-[#0A1833]">
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: "url('/runway_drone_bg.jpg')" }}
          aria-hidden="true"
        />
        <div
          className="absolute inset-x-0 top-0 h-44 bg-gradient-to-b from-[#7CA5D6]/30 via-transparent to-transparent pointer-events-none"
          aria-hidden="true"
        />
        <div
          className="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-t from-[#061024]/95 via-[#07142B]/80 to-transparent pointer-events-none"
          aria-hidden="true"
        />

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

        <div className="relative z-10 pb-6 sm:pb-8 lg:pb-10 pt-12 px-3 sm:px-6 lg:px-8">
          <div className="max-w-xl mx-auto grid grid-cols-4 divide-x divide-white/15 text-center">
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 flex items-center justify-center text-[#7AB8FF] mb-1.5">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3L5 19l7-3.5L19 19 12 3z" />
                  <path d="M12 15.5V21" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">Navigation</span>
            </div>
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 flex items-center justify-center text-[#7AB8FF] mb-1.5">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 19L17 5l2 2L7 21 5 19z" />
                  <circle cx="17.5" cy="15.5" r="1" />
                  <path d="M14 18h2" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">Rod Debris<br />Detection</span>
            </div>
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 flex items-center justify-center text-[#7AB8FF] mb-1.5">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 4L4 20" />
                  <path d="M15 4l5 16" />
                  <path d="M12 5v3" />
                  <path d="M12 11v3" />
                  <path d="M12 17v3" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">Runway Lights<br />Detection</span>
            </div>
            <div className="px-1.5 sm:px-2.5 flex flex-col items-center">
              <div className="w-8 h-8 flex items-center justify-center text-[#7AB8FF] mb-1.5">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="6" y="7" width="12" height="10" rx="3" />
                  <circle cx="12" cy="12" r="2.5" />
                  <path d="M3 10v4" />
                  <path d="M21 10v4" />
                </svg>
              </div>
              <span className="text-[10px] sm:text-[11px] font-medium text-[#E2E8F0] leading-tight">Live Surveillance</span>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT PANEL — Create Account Form */}
      <div className="relative w-full lg:w-[48%] xl:w-[47%] flex-1 flex flex-col justify-center items-center px-6 sm:px-12 lg:px-16 py-10 lg:py-12 bg-[#F8FAFC] overflow-hidden">
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
          <div className="flex items-center space-x-3 mb-7">
            <img
              src="/garuda_logo.png"
              alt="Garuda Aerospace Logo"
              className="w-10 h-10 object-contain"
            />
            <span className="text-2xl sm:text-[26px] font-bold tracking-tight text-[#0A2558]">
              Garuda Aerospace
            </span>
          </div>

          <div className="mb-6">
            <h1 className="text-2xl sm:text-[28px] font-bold text-[#0F172A] tracking-tight">
              Create Account
            </h1>
            <p className="text-sm text-[#64748B] mt-1.5">
              Create your account to access Garuda Aerospace immediately
            </p>
          </div>

          {displayError && (
            <div
              role="alert"
              className="mb-5 p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start space-x-2.5"
            >
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <span className="font-medium leading-relaxed">{displayError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
            {/* Full Name */}
            <div>
              <label htmlFor="register-name" className="sr-only">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                  <User className="w-[18px] h-[18px]" strokeWidth={1.75} />
                </div>
                <input
                  id="register-name"
                  name="full_name"
                  type="text"
                  required
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => {
                    setFullName(e.target.value);
                    if (localError) setLocalError(null);
                    if (error) clearError();
                  }}
                  placeholder="Full Name"
                  className="w-full h-12 pl-11 pr-4 bg-[#F3F6F9] border border-[#DCE3EC] rounded-lg text-sm text-[#0F172A] placeholder-[#7B8A9E] focus:outline-none focus:bg-white focus:border-[#0A3981] focus:ring-2 focus:ring-[#0A3981]/15 transition-all"
                />
              </div>
            </div>

            {/* Email Address */}
            <div>
              <label htmlFor="register-email" className="sr-only">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                  <Mail className="w-[18px] h-[18px]" strokeWidth={1.75} />
                </div>
                <input
                  id="register-email"
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

            {/* Password */}
            <div>
              <label htmlFor="register-password" className="sr-only">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                  <Lock className="w-[18px] h-[18px]" strokeWidth={1.75} />
                </div>
                <input
                  id="register-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete="new-password"
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

            {/* Confirm Password */}
            <div>
              <label htmlFor="register-confirm-password" className="sr-only">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                  <Lock className="w-[18px] h-[18px]" strokeWidth={1.75} />
                </div>
                <input
                  id="register-confirm-password"
                  name="confirm_password"
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (localError) setLocalError(null);
                    if (error) clearError();
                  }}
                  placeholder="Confirm Password"
                  className="w-full h-12 pl-11 pr-11 bg-[#F3F6F9] border border-[#DCE3EC] rounded-lg text-sm text-[#0F172A] placeholder-[#7B8A9E] focus:outline-none focus:bg-white focus:border-[#0A3981] focus:ring-2 focus:ring-[#0A3981]/15 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#64748B] hover:text-[#0F172A] transition-colors"
                  aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                >
                  {showConfirmPassword ? (
                    <Eye className="w-[18px] h-[18px]" strokeWidth={1.75} />
                  ) : (
                    <EyeOff className="w-[18px] h-[18px]" strokeWidth={1.75} />
                  )}
                </button>
              </div>
            </div>

            {/* Create Account Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 rounded-lg bg-[#0A3981] hover:bg-[#082D66] active:bg-[#06214D] text-white text-sm font-semibold tracking-wide shadow-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            {/* Sign In Link */}
            <div className="pt-2 text-center">
              <p className="text-xs text-[#475569]">
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="font-semibold text-[#1E40AF] hover:text-[#0A3981] hover:underline transition-colors"
                >
                  Sign In
                </Link>
              </p>
            </div>
          </form>

          <p className="mt-7 text-center text-xs text-[#64748B]">
            For authorized users only. All activities are monitored.
          </p>
        </div>
      </div>
    </div>
  );
}
