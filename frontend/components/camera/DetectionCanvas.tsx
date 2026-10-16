"use client";

import React, { useRef, useEffect } from "react";
import { useDroneStore } from "../../stores/droneStore";

interface DetectionCanvasProps {
  videoWidth: number;
  videoHeight: number;
  containerWidth: number;
  containerHeight: number;
  roiPolygon?: number[][];
}

export const DetectionCanvas: React.FC<DetectionCanvasProps> = ({
  videoWidth,
  videoHeight,
  containerWidth,
  containerHeight,
  roiPolygon,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const detections = useDroneStore((s) => s.detections);
  const confidenceThreshold = useDroneStore((s) => s.confidenceThreshold);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;

    const render = () => {
      // 1. Clear Canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (videoWidth <= 0 || videoHeight <= 0) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      // 2. Calculate dynamic scaling factors
      const scaleX = canvas.width / videoWidth;
      const scaleY = canvas.height / videoHeight;

      // 3. Draw Runway Pathway ROI if provided (PRD Section 4.5)
      if (roiPolygon && roiPolygon.length >= 3) {
        ctx.save();
        ctx.beginPath();
        roiPolygon.forEach(([nx, ny], idx) => {
          const px = nx * canvas.width;
          const py = ny * canvas.height;
          if (idx === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.closePath();
        ctx.strokeStyle = "rgba(245, 158, 11, 0.85)"; // Amber / Gold boundary
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.stroke();
        ctx.fillStyle = "rgba(245, 158, 11, 0.06)";
        ctx.fill();

        // Label
        ctx.font = "bold 10px Inter, system-ui, sans-serif";
        ctx.fillStyle = "rgba(245, 158, 11, 0.95)";
        ctx.fillText("RUNWAY PATHWAY ROI", 12, 20);
        ctx.restore();
      }

      // 4. Draw Bounding Boxes (Clean overlay without unnecessary reticles, grid lines, or separators - PRD Section 2.1)
      detections.forEach((det) => {
        if (det.confidence < confidenceThreshold) return;

        let x = 0, y = 0, w = 0, h = 0;
        if (det.bbox_xywh) {
          [x, y, w, h] = det.bbox_xywh;
        } else if (Array.isArray(det.bbox)) {
          const [b0, b1, b2, b3] = det.bbox;
          if (b2 > b0 && b3 > b1 && (b2 > 80 || b3 > 80)) {
            x = b0;
            y = b1;
            w = b2 - b0;
            h = b3 - b1;
          } else {
            [x, y, w, h] = [b0, b1, b2, b3];
          }
        } else if (typeof det.bbox === "object" && det.bbox !== null) {
          const b = det.bbox as any;
          x = b.x1 ?? 0;
          y = b.y1 ?? 0;
          w = (b.x2 ?? 0) - x;
          h = (b.y2 ?? 0) - y;
        }

        // Scale to displayed canvas dimensions
        const drawX = x * scaleX;
        const drawY = y * scaleY;
        const drawW = w * scaleX;
        const drawH = h * scaleY;

        if (drawW <= 0 || drawH <= 0) return;

        // Classify & Color: LIGHT ON (Emerald Green), LIGHT OFF (Crimson Red) (PRD Section 2.3)
        const rawClass = (det.class_name || "OBJECT").toUpperCase();
        const state = (det.state || "").toUpperCase();
        const isLightOn = rawClass.includes("LIGHT ON") || state === "ON";
        const isLightOff = rawClass.includes("LIGHT OFF") || state === "OFF" || state === "OFF-GAP";
        const isFod = rawClass.includes("FOD") || (det as any).model === "fod";

        let primaryColor = "#22C55E"; // Emerald Green (#22C55E)
        let displayName = "LIGHT ON";

        if (isLightOff) {
          primaryColor = "#EF4444"; // Crimson Red (#EF4444)
          displayName = "LIGHT OFF";
        } else if (isLightOn) {
          primaryColor = "#22C55E";
          displayName = "LIGHT ON";
        } else if (isFod) {
          primaryColor = "#DC2626";
          displayName = "FOD";
        } else {
          primaryColor = "#3B82F6";
          displayName = rawClass;
        }

        // Clean bounding box
        ctx.strokeStyle = primaryColor;
        ctx.lineWidth = 2;
        ctx.strokeRect(drawX, drawY, drawW, drawH);

        // Concise, uncluttered label format (PRD Section 2.2): "LIGHT ON · 94%" or "LIGHT OFF · 91%"
        const confPct = Math.round(det.confidence * 100);
        const labelText = `${displayName} · ${confPct}%`;

        ctx.font = "bold 11px Inter, system-ui, sans-serif";
        const textMetrics = ctx.measureText(labelText);
        const textWidth = textMetrics.width;
        const badgeHeight = 18;
        const badgeWidth = textWidth + 10;

        // Smart positioning: above box if space permits, else below box (PRD Section 2.2)
        const badgeY = drawY >= badgeHeight + 4 ? drawY - badgeHeight - 2 : Math.min(canvas.height - badgeHeight - 2, drawY + drawH + 2);
        const badgeX = Math.max(2, Math.min(drawX, canvas.width - badgeWidth - 2));

        // Solid badge background matching bounding box
        ctx.fillStyle = primaryColor;
        ctx.fillRect(badgeX, badgeY, badgeWidth, badgeHeight);
        ctx.strokeStyle = "rgba(18, 18, 18, 0.85)";
        ctx.lineWidth = 1;
        ctx.strokeRect(badgeX, badgeY, badgeWidth, badgeHeight);

        // Badge text: crisp white
        ctx.fillStyle = "#FFFFFF";
        ctx.fillText(labelText, badgeX + 5, badgeY + 13);
      });

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animationFrameId);
  }, [detections, confidenceThreshold, videoWidth, videoHeight]);

  return (
    <canvas
      ref={canvasRef}
      width={containerWidth}
      height={containerHeight}
      className="absolute inset-0 pointer-events-none z-10"
    />
  );
};

export default DetectionCanvas;
