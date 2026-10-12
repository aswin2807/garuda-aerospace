import { useState, useCallback } from "react";
import { startVideoAnalysis, stopVideoAnalysis, getVideoSessionStatus } from "../lib/api";
import { useDroneStore } from "../stores/droneStore";

export function useVideo() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeSessionId = useDroneStore((s) => s.activeSessionId);
  const setActiveSessionId = useDroneStore((s) => s.setActiveSessionId);

  const startAnalysis = useCallback(async (source: string, loop: boolean = false) => {
    try {
      setIsProcessing(true);
      setError(null);
      const res = await startVideoAnalysis(source, loop);
      if (res.session_id) {
        setActiveSessionId(res.session_id);
      }
      return res;
    } catch (err: any) {
      setError(err?.message || "Failed to start video analysis");
      setIsProcessing(false);
      throw err;
    }
  }, [setActiveSessionId]);

  const stopAnalysis = useCallback(async () => {
    if (!activeSessionId) return null;
    try {
      const res = await stopVideoAnalysis(activeSessionId);
      setIsProcessing(false);
      setActiveSessionId(null);
      return res;
    } catch (err: any) {
      setError(err?.message || "Failed to stop video analysis");
      throw err;
    }
  }, [activeSessionId, setActiveSessionId]);

  return {
    isProcessing,
    activeSessionId,
    error,
    startAnalysis,
    stopAnalysis,
  };
}
