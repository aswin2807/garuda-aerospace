import { useState, useCallback, useEffect } from "react";
import { useAnalysisStore } from "../stores/analysisStore";
import {
  uploadAnalysisVideo,
  uploadAnalysisImage,
  startAnalysis,
  pauseAnalysis,
  resumeAnalysis,
  cancelAnalysis,
  getAnalysisStatus,
  getAnalysisResults,
  getAnalysisJobs,
} from "../lib/api";

export function useAnalysis() {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const activeJob = useAnalysisStore((s) => s.activeJob);
  const analysisType = useAnalysisStore((s) => s.analysisType);
  const setActiveJob = useAnalysisStore((s) => s.setActiveJob);
  const setSelectedFile = useAnalysisStore((s) => s.setSelectedFile);
  const setFilePreviewUrl = useAnalysisStore((s) => s.setFilePreviewUrl);
  const setIsVideoPlaybackPaused = useAnalysisStore((s) => s.setIsVideoPlaybackPaused);
  const setIsUploading = useAnalysisStore((s) => s.setIsUploading);
  const setJobResults = useAnalysisStore((s) => s.setJobResults);
  const setJobHistory = useAnalysisStore((s) => s.setJobHistory);
  const updateProgress = useAnalysisStore((s) => s.updateProgress);
  const resetAnalysis = useAnalysisStore((s) => s.resetAnalysis);

  const handleUploadVideo = useCallback(
    async (file: File, overrideType?: string) => {
      setLoading(true);
      setIsUploading(true);
      setError(null);
      const targetType = (overrideType || analysisType || "NAVIGATION") as any;
      try {
        const previewUrl = URL.createObjectURL(file);
        setSelectedFile(file, targetType);
        setFilePreviewUrl(previewUrl, targetType);
        // Video must strictly remain PAUSED upon upload (PRD Section 7)
        setIsVideoPlaybackPaused(true, targetType);

        const res = await uploadAnalysisVideo(file, targetType);
        const jid = res.job_id || res.id;
        const newJob = {
          id: jid,
          job_id: jid,
          filename: res.filename || res.video_name || file.name,
          video_name: res.video_name || res.filename || file.name,
          media_type: "VIDEO" as const,
          analysis_type: res.analysis_type || targetType,
          status: res.status || "QUEUED",
          total_frames: res.total_frames || res.frames_total || 0,
          frames_total: res.total_frames || res.frames_total || 0,
          processed_frames: 0,
          progress: 0,
          processing_fps: 0,
          video_fps: res.video_fps || 30,
          duration_seconds: res.duration_seconds || 0,
          elapsed_seconds: 0,
          remaining_seconds: 0,
          nav_count: 0,
          fod_count: 0,
          light_on_count: 0,
          light_off_count: 0,
          confirmed_faults: 0,
        };
        setActiveJob(newJob, targetType);
        return newJob;
      } catch (err: any) {
        const msg = err.message || "Failed to upload video";
        setError(msg);
        throw err;
      } finally {
        setLoading(false);
        setIsUploading(false, targetType);
      }
    },
    [analysisType, setActiveJob, setSelectedFile, setFilePreviewUrl, setIsVideoPlaybackPaused, setIsUploading]
  );

  const handleUploadImage = useCallback(
    async (file: File, overrideType?: string) => {
      setLoading(true);
      setIsUploading(true);
      setError(null);
      const targetType = (overrideType || analysisType || "NAVIGATION") as any;
      try {
        const previewUrl = URL.createObjectURL(file);
        setSelectedFile(file, targetType);
        setFilePreviewUrl(previewUrl, targetType);

        const res = await uploadAnalysisImage(file, targetType);
        const jid = res.job_id || res.id;
        const newJob = {
          id: jid,
          job_id: jid,
          filename: res.filename || res.video_name || file.name,
          video_name: res.video_name || res.filename || file.name,
          media_type: "IMAGE" as const,
          analysis_type: res.analysis_type || targetType,
          status: res.status || "QUEUED",
          total_frames: 1,
          frames_total: 1,
          processed_frames: 0,
          progress: 0,
          processing_fps: 0,
          video_fps: 0,
          duration_seconds: 0,
          elapsed_seconds: 0,
          remaining_seconds: 0,
          nav_count: 0,
          fod_count: 0,
          light_on_count: 0,
          light_off_count: 0,
          confirmed_faults: 0,
        };
        setActiveJob(newJob, targetType);
        return newJob;
      } catch (err: any) {
        const msg = err.message || "Failed to upload image";
        setError(msg);
        throw err;
      } finally {
        setLoading(false);
        setIsUploading(false, targetType);
      }
    },
    [analysisType, setActiveJob, setSelectedFile, setFilePreviewUrl, setIsUploading]
  );

  const handleStart = useCallback(
    async (jobId: string) => {
      setError(null);
      try {
        const res = await startAnalysis(jobId);
        updateProgress({ status: res.status || "ANALYZING" });
        return res;
      } catch (err: any) {
        const msg = err.message || "Failed to start analysis";
        setError(msg);
        throw err;
      }
    },
    [updateProgress]
  );

  const handlePause = useCallback(
    async (jobId: string) => {
      setError(null);
      try {
        const res = await pauseAnalysis(jobId);
        updateProgress({ status: "PAUSED" });
        return res;
      } catch (err: any) {
        const msg = err.message || "Failed to pause analysis";
        setError(msg);
        throw err;
      }
    },
    [updateProgress]
  );

  const handleResume = useCallback(
    async (jobId: string) => {
      setError(null);
      try {
        const res = await resumeAnalysis(jobId);
        updateProgress({ status: "ANALYZING" });
        return res;
      } catch (err: any) {
        const msg = err.message || "Failed to resume analysis";
        setError(msg);
        throw err;
      }
    },
    [updateProgress]
  );

  const handleCancel = useCallback(
    async (jobId: string) => {
      setError(null);
      try {
        const res = await cancelAnalysis(jobId);
        updateProgress({ status: "CANCELLED" });
        return res;
      } catch (err: any) {
        const msg = err.message || "Failed to cancel analysis";
        setError(msg);
        throw err;
      }
    },
    [updateProgress]
  );

  const handleFetchResults = useCallback(
    async (jobId: string) => {
      try {
        const results = await getAnalysisResults(jobId);
        setJobResults(results);
        return results;
      } catch (err: any) {
        console.error("Failed to fetch analysis results:", err);
      }
    },
    [setJobResults]
  );

  const handleFetchHistory = useCallback(async (typeFilter?: string) => {
    try {
      const history = await getAnalysisJobs(typeFilter || analysisType);
      setJobHistory(history);
      return history;
    } catch (err: any) {
      console.error("Failed to fetch job history:", err);
    }
  }, [analysisType, setJobHistory]);

  // Polling fallback when analyzing
  useEffect(() => {
    if (!activeJob || activeJob.status !== "ANALYZING") return;
    const jid = activeJob.job_id || activeJob.id;
    if (!jid) return;

    const interval = setInterval(async () => {
      try {
        const status = await getAnalysisStatus(jid);
        updateProgress(status);

        if (status.status === "COMPLETED") {
          const results = await getAnalysisResults(jid);
          setJobResults(results);
        }
      } catch (err) {
        console.debug("Status polling fallback tick error:", err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeJob?.job_id, activeJob?.id, activeJob?.status, updateProgress, setJobResults]);

  return {
    loading,
    error,
    uploadVideo: handleUploadVideo,
    uploadImage: handleUploadImage,
    start: handleStart,
    pause: handlePause,
    resume: handleResume,
    cancel: handleCancel,
    fetchResults: handleFetchResults,
    fetchHistory: handleFetchHistory,
    reset: resetAnalysis,
  };
}
