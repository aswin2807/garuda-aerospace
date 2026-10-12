import { useEffect, useRef, useCallback } from "react";
import { useAnalysisStore } from "../stores/analysisStore";
import { useDroneStore } from "../stores/droneStore";
import { getAnalysisResults } from "../lib/api";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

/**
 * useAnalysisWebSocket
 * Connects to /ws/v1/analysis/{job_id} to receive continuous, real-time
 * progress, dynamic ETA, frame rates, and live detection statistics.
 */
export function useAnalysisWebSocket(jobId?: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const updateProgress = useAnalysisStore((s) => s.updateProgress);
  const setJobResults = useAnalysisStore((s) => s.setJobResults);

  const connect = useCallback(() => {
    if (!jobId) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const wsUrl = `${WS_BASE}/ws/v1/analysis/${encodeURIComponent(jobId)}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      // Heartbeat ping every 5 seconds
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 5000);
    };

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "pong") return;

        // Dispatches real-time frame progress, dynamic ETA, and metrics to analysis store
        updateProgress(data);

        // Synchronize with drone store so detection cards, stats, and alerts update in real-time
        try {
          useDroneStore.getState().applyDetectionUpdate({
            counts: data.counts,
            session_totals: data.counts,
            performance: {
              stream_fps: data.video_fps || 30.0,
              inference_fps: data.processing_fps || data.fps || 0.0,
              inference_ms: data.performance?.inference_ms || 0.0,
            },
            detections: data.recent_detections || [],
          });
        } catch (e) {
          // Ignore sync failure
        }

        // When analysis completes or fails, fetch detailed results
        if (data.status === "COMPLETED") {
          try {
            const results = await getAnalysisResults(jobId);
            setJobResults(results);
          } catch (e) {
            console.error("Failed to load completed job results:", e);
          }
        }
      } catch (err) {
        console.error("Error parsing analysis WebSocket payload:", err);
      }
    };

    ws.onclose = () => {
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      // Reconnect if job is still active
      const currentJob = useAnalysisStore.getState().activeJob;
      const currentId = currentJob?.job_id || currentJob?.id;
      if (
        currentJob &&
        currentId === jobId &&
        (currentJob.status === "ANALYZING" || currentJob.status === "QUEUED")
      ) {
        reconnectTimeoutRef.current = setTimeout(connect, 2000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [jobId, updateProgress, setJobResults]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    };
  }, [connect]);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}
