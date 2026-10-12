import { useState, useCallback } from "react";
import { connectCamera, disconnectCamera, getCameraStatus } from "../lib/api";
import { useDroneStore } from "../stores/droneStore";
import type { CameraConnectParams } from "../types/detection";

export function useCamera() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeCameraId = useDroneStore((s) => s.activeCameraId);
  const cameraStatus = useDroneStore((s) => s.cameraStatus);
  const setActiveCameraId = useDroneStore((s) => s.setActiveCameraId);
  const setCameraStatus = useDroneStore((s) => s.setCameraStatus);

  const connect = useCallback(async (params: CameraConnectParams) => {
    try {
      setIsConnecting(true);
      setError(null);
      const res = await connectCamera(params);
      if (res.success && res.camera_id) {
        setActiveCameraId(res.camera_id);
        setCameraStatus("CONNECTED");
      }
      return res;
    } catch (err: any) {
      setError(err?.message || "Failed to connect to camera");
      setCameraStatus("ERROR");
      throw err;
    } finally {
      setIsConnecting(false);
    }
  }, [setActiveCameraId, setCameraStatus]);

  const disconnect = useCallback(async () => {
    if (!activeCameraId) return;
    try {
      await disconnectCamera(activeCameraId);
      setActiveCameraId(null);
      setCameraStatus("DISCONNECTED");
    } catch (err: any) {
      setError(err?.message || "Failed to disconnect camera");
    }
  }, [activeCameraId, setActiveCameraId, setCameraStatus]);

  return {
    activeCameraId,
    cameraStatus,
    isConnecting,
    error,
    connect,
    disconnect,
  };
}
