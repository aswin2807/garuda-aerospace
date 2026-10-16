"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import { verifyResetToken, resetPassword } from "../../lib/api";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [verifying, setVerifying] = useState(true);
  const [isTokenValid, setIsTokenValid] = useState(false);
  const [tokenEmail, setTokenEmail] = useState<string | null>(null);
  const [tokenErrorMessage, setTokenErrorMessage] = useState<string | null>(null);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function checkToken() {
      if (!token) {
        if (isMounted) {
          setVerifying(false);
          setIsTokenValid(false);
          setTokenErrorMessage("No password reset token was provided in the link.");
        }
        return;
      }

      try {
        const res = await verifyResetToken(token);
        if (isMounted) {
          setVerifying(false);
          setIsTokenValid(res.valid);
          if (res.valid) {
            setTokenEmail(res.email || null);
          } else {
            setTokenErrorMessage(
              res.message ||
                "This password reset link is invalid, expired, or has already been used."
            );
          }
        }
      } catch {
        if (isMounted) {
          setVerifying(false);
          setIsTokenValid(false);
          setTokenErrorMessage("Unable to verify reset link at this time.");
        }
      }
    }

    checkToken();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const hasNonEmptyPassword = newPassword.length > 0;
  const withinByteLimit = new TextEncoder().encode(newPassword).length <= 72;
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    setSubmitError(null);

    if (!hasNonEmptyPassword) {
      setSubmitError("Please enter a new password.");
      return;
    }

    if (!withinByteLimit) {
      setSubmitError("Password cannot exceed 72 bytes in UTF-8 encoding.");
      return;
    }

    if (!passwordsMatch) {
      setSubmitError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await resetPassword(token, newPassword, confirmPassword);
      if (res.success) {
        setResetSuccess(true);
        setTimeout(() => {
          router.replace("/login?reset=1");
        }, 1200);
      } else {
        setSubmitError(res.message || "Failed to reset password.");
      }
    } catch (err: any) {
      setSubmitError(
        err?.message || "An error occurred while resetting your password."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

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

      {/* RIGHT PANEL — Reset Password Form */}
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

          {verifying && (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-7 h-7 text-[#0A3981] animate-spin" />
              <p className="text-xs font-medium text-[#64748B]">
                Validating password reset token...
              </p>
            </div>
          )}

          {!verifying && !isTokenValid && (
            <div className="space-y-5">
              <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-xs space-y-2">
                <div className="flex items-center space-x-2 text-red-700 font-semibold text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>Invalid or Expired Link</span>
                </div>
                <p className="leading-relaxed text-red-800">
                  {tokenErrorMessage ||
                    "This password reset link is invalid, has expired, or has already been used."}
                </p>
              </div>

              <div className="space-y-3">
                <Link
                  href="/forgot-password"
                  className="w-full h-12 rounded-lg bg-[#0A3981] hover:bg-[#082D66] text-white text-sm font-semibold transition-all flex items-center justify-center space-x-2 shadow-sm"
                >
                  <span>Request New Reset Link</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/login"
                  className="w-full h-11 rounded-lg bg-white hover:bg-[#F1F5F9] border border-[#DCE3EC] text-[#1E293B] text-xs font-semibold transition-all flex items-center justify-center space-x-2"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Return to Sign In</span>
                </Link>
              </div>
            </div>
          )}

          {!verifying && isTokenValid && resetSuccess && (
            <div className="space-y-5">
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs space-y-2">
                <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-sm">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                  <span>Password Reset Complete</span>
                </div>
                <p className="leading-relaxed text-emerald-800">
                  Your password has been updated. Redirecting you to Sign In...
                </p>
              </div>

              <Link
                href="/login?reset=1"
                className="w-full h-12 rounded-lg bg-[#0A3981] hover:bg-[#082D66] text-white text-sm font-semibold transition-all flex items-center justify-center space-x-2 shadow-sm"
              >
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}

          {!verifying && isTokenValid && !resetSuccess && (
            <>
              <div className="mb-7">
                <h1 className="text-2xl sm:text-[28px] font-bold text-[#0F172A] tracking-tight">
                  Set New Password
                </h1>
                <p className="text-sm text-[#64748B] mt-1.5">
                  Create a new password{" "}
                  {tokenEmail && (
                    <span className="font-semibold text-[#0F172A]">
                      for {tokenEmail}
                    </span>
                  )}
                </p>
              </div>

              {submitError && (
                <div
                  role="alert"
                  className="mb-5 p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start space-x-2.5"
                >
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <span className="font-medium leading-relaxed">{submitError}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                <div>
                  <label htmlFor="new-password" className="sr-only">
                    New Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                      <Lock className="w-[18px] h-[18px]" strokeWidth={1.75} />
                    </div>
                    <input
                      id="new-password"
                      type={showNewPassword ? "text" : "password"}
                      required
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(e) => {
                        setNewPassword(e.target.value);
                        if (submitError) setSubmitError(null);
                      }}
                      placeholder="New Password"
                      className="w-full h-12 pl-11 pr-11 bg-[#F3F6F9] border border-[#DCE3EC] rounded-lg text-sm text-[#0F172A] placeholder-[#7B8A9E] focus:outline-none focus:bg-white focus:border-[#0A3981] focus:ring-2 focus:ring-[#0A3981]/15 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#64748B] hover:text-[#0F172A] transition-colors"
                      aria-label={showNewPassword ? "Hide password" : "Show password"}
                    >
                      {showNewPassword ? (
                        <Eye className="w-[18px] h-[18px]" strokeWidth={1.75} />
                      ) : (
                        <EyeOff className="w-[18px] h-[18px]" strokeWidth={1.75} />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="confirm-password" className="sr-only">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#64748B]">
                      <Lock className="w-[18px] h-[18px]" strokeWidth={1.75} />
                    </div>
                    <input
                      id="confirm-password"
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        if (submitError) setSubmitError(null);
                      }}
                      placeholder="Confirm New Password"
                      className="w-full h-12 pl-11 pr-11 bg-[#F3F6F9] border border-[#DCE3EC] rounded-lg text-sm text-[#0F172A] placeholder-[#7B8A9E] focus:outline-none focus:bg-white focus:border-[#0A3981] focus:ring-2 focus:ring-[#0A3981]/15 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#64748B] hover:text-[#0F172A] transition-colors"
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                    >
                      {showConfirmPassword ? (
                        <Eye className="w-[18px] h-[18px]" strokeWidth={1.75} />
                      ) : (
                        <EyeOff className="w-[18px] h-[18px]" strokeWidth={1.75} />
                      )}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-[#F3F6F9] border border-[#DCE3EC] space-y-1.5 text-xs">
                  <div className="flex items-center space-x-2">
                    {passwordsMatch ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-[#94A3B8]" />
                    )}
                    <span className={passwordsMatch ? "text-emerald-700 font-medium" : "text-[#64748B]"}>
                      Passwords match
                    </span>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || !hasNonEmptyPassword || !passwordsMatch}
                  className="w-full h-12 rounded-lg bg-[#0A3981] hover:bg-[#082D66] active:bg-[#06214D] text-white text-sm font-semibold tracking-wide shadow-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Updating Password...</span>
                    </>
                  ) : (
                    <>
                      <span>Reset Password</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                <div className="pt-2 text-center">
                  <Link
                    href="/login"
                    className="inline-flex items-center space-x-1.5 text-xs font-semibold text-[#1E40AF] hover:text-[#0A3981] hover:underline transition-colors"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Back to Sign In</span>
                  </Link>
                </div>
              </form>
            </>
          )}

          <p className="mt-8 text-center text-xs text-[#64748B]">
            For authorized users only. All activities are monitored.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full bg-[#F8FAFC] flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-[#0A3981] animate-spin" />
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
