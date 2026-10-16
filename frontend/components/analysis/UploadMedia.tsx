"use client";

import React, { useRef, useState, DragEvent, ChangeEvent } from "react";
import { useAnalysisStore } from "../../stores/analysisStore";
import { useAnalysis } from "../../hooks/useAnalysis";

interface UploadMediaProps {
  onUploaded?: () => void;
}

export const UploadMedia: React.FC<UploadMediaProps> = ({ onUploaded }) => {
  const mode = useAnalysisStore((s) => s.mode);
  const isUploading = useAnalysisStore((s) => s.isUploading);
  const { uploadVideo, uploadImage, error } = useAnalysis();

  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [validationError, setValidationError] = useState<string | null>(null);

  const isVideoMode = mode === "VIDEO";
  const acceptedTypes = isVideoMode
    ? ".mp4,.mov,.avi,.mkv,.webm"
    : ".jpg,.jpeg,.png,.webp,.bmp";

  const handleFile = async (file: File) => {
    setValidationError(null);
    const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
    const allowed = isVideoMode
      ? [".mp4", ".mov", ".avi", ".mkv", ".webm"]
      : [".jpg", ".jpeg", ".png", ".webp", ".bmp"];

    if (!allowed.includes(ext)) {
      setValidationError(`Unsupported file format '${ext}'. Allowed formats: ${allowed.join(", ")}`);
      return;
    }

    if (file.size === 0) {
      setValidationError("The selected file is empty (0 bytes). Please upload a valid recorded video.");
      return;
    }

    const maxBytes = 500 * 1024 * 1024; // 500MB limit
    if (file.size > maxBytes) {
      setValidationError(
        `File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the maximum limit of 500 MB.`
      );
      return;
    }

    try {
      if (isVideoMode) {
        await uploadVideo(file);
      } else {
        await uploadImage(file);
      }
      if (onUploaded) onUploaded();
    } catch (e: any) {
      setValidationError(e.message || "Upload failed. Please check the file and try again.");
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFile(file);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      handleFile(file);
    }
  };

  const analysisType = useAnalysisStore((s) => s.analysisType);
  const activeError = validationError || error;

  return (
    <div className="flex flex-col w-full">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 select-none ${
          isDragOver
            ? "border-[#0066FF] bg-[#EAF3FF] shadow-[0_0_25px_rgba(0,102,255,0.15)]"
            : "border-[#D9DEE7] bg-[#FFFFFF] hover:border-[#0066FF] hover:bg-[#F0F6FF]"
        } ${isUploading ? "pointer-events-none opacity-60" : ""}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes}
          onChange={handleChange}
          className="hidden"
          disabled={isUploading}
        />

        {/* Upload Icon */}
        <div className="w-14 h-14 rounded-full bg-[#EAF3FF] border border-[#0066FF]/30 flex items-center justify-center text-[#0066FF] mb-4">
          {isUploading ? (
            <div className="w-6 h-6 border-2 border-[#0066FF] border-t-transparent rounded-full animate-spin" />
          ) : isVideoMode ? (
            <svg
              className="w-7 h-7"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.8}
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          ) : (
            <svg
              className="w-7 h-7"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.8}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          )}
        </div>

        <h3 className="text-base font-semibold text-[#111827] font-mono tracking-wide mb-1">
          {isUploading
            ? isVideoMode
              ? "Reading & Extracting Video Headers..."
              : "Uploading Image..."
            : isVideoMode
            ? `Upload Drone Video for ${analysisType.replace("_", " ")} Analysis`
            : `Upload Drone Image for ${analysisType.replace("_", " ")} Detection`}
        </h3>

        <p className="text-xs text-[#5B6472] font-mono mb-4 max-w-md">
          {isVideoMode
            ? "Drag & drop footage here or click to browse. The video will load in a strictly PAUSED state awaiting analysis."
            : "Drag & drop drone aerial photo or inspection frame. Only the dedicated model for this module will execute."}
        </p>

        <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] font-mono text-[#5B6472] bg-[#F5F7FA] border border-[#D9DEE7] px-3 py-1.5 rounded-md">
          <span className="text-[#0066FF] font-semibold">MODULE:</span>
          <span className="font-bold text-[#111827]">{analysisType.replace("_", " ")}</span>
          <span className="text-[#D9DEE7]">|</span>
          <span className="text-[#0066FF] font-semibold">SUPPORTED:</span>
          <span>{isVideoMode ? "MP4, MOV, AVI, MKV, WEBM" : "JPG, PNG, WEBP, BMP"}</span>
        </div>

        {activeError && (
          <div className="mt-4 p-2.5 bg-red-50 border border-red-200 rounded-lg text-red-600 text-xs font-mono flex items-center justify-between">
            <span>{activeError}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setValidationError(null);
              }}
              className="text-red-700 hover:text-red-900 font-bold ml-2 text-sm"
            >
              ✕
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
