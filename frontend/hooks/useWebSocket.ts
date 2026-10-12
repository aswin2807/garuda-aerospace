import { useEffect, useRef, useCallback } from "react";
import { useDroneStore } from "../stores/droneStore";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useWebSocket(droneId: string = "DR-01") {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const applyDetectionUpdate = useDroneStore((s) => s.applyDetectionUpdate);
  const setConnectionStatus = useDroneStore((s) => s.setConnectionStatus);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    setConnectionStatus("CONNECTING");
    const ws = new WebSocket(`${WS_BASE}/ws/v1/detection/${droneId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("CONNECTED");
      // Start ping heartbeat
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 5000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "pong") return;
        applyDetectionUpdate(data);
      } catch (err) {
        console.error("Error processing WebSocket frame:", err);
      }
    };

    ws.onclose = () => {
      setConnectionStatus("DISCONNECTED");
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      // Auto reconnect
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [droneId, applyDetectionUpdate, setConnectionStatus]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    };
  }, [connect]);

  const sendFrame = useCallback((base64Image: string, confidenceThreshold?: number) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          image: base64Image,
          confidence_threshold: confidenceThreshold,
        })
      );
    }
  }, []);

  return { sendFrame };
}
