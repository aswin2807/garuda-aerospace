"use client";

import React, { useRef, useEffect } from "react";
import { useDroneStore } from "../../stores/droneStore";

interface DetectionCanvasProps {
  videoWidth: number;
  videoHeight: number;
  containerWidth: number;
  containerHeight: number;
}

export const DetectionCanvas: React.FC<DetectionCanvasProps> = ({
  videoWidth,
  videoHeight,
  containerWidth,
  containerHeight,
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

      // Draw Tactical Center Reticle (PRD Section 10)
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      ctx.strokeStyle = "rgba(0, 102, 255, 0.4)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cx - 30, cy);
      ctx.lineTo(cx + 30, cy);
      ctx.moveTo(cx, cy - 30);
      ctx.lineTo(cx, cy + 30);
      ctx.stroke();

      // Small central circle
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Tactical Aviation Corner Brackets (PRD Section 10)
      const bracketLen = 16;
      ctx.strokeStyle = "rgba(0, 140, 255, 0.6)";
      ctx.lineWidth = 1.5;

      // Top-Left
      ctx.beginPath();
      ctx.moveTo(10, 10 + bracketLen);
      ctx.lineTo(10, 10);
      ctx.lineTo(10 + bracketLen, 10);
      ctx.stroke();

      // Top-Right
      ctx.beginPath();
      ctx.moveTo(canvas.width - 10 - bracketLen, 10);
      ctx.lineTo(canvas.width - 10, 10);
      ctx.lineTo(canvas.width - 10, 10 + bracketLen);
      ctx.stroke();

      // Bottom-Left
      ctx.beginPath();
      ctx.moveTo(10, canvas.height - 10 - bracketLen);
      ctx.lineTo(10, canvas.height - 10);
      ctx.lineTo(10 + bracketLen, canvas.height - 10);
      ctx.stroke();

      // Bottom-Right
      ctx.beginPath();
      ctx.moveTo(canvas.width - 10 - bracketLen, canvas.height - 10);
      ctx.lineTo(canvas.width - 10, canvas.height - 10);
      ctx.lineTo(canvas.width - 10, canvas.height - 10 - bracketLen);
      ctx.stroke();

      // 3. Draw Bounding Boxes
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

        // Aviation Black, White & Blue Box Theme (PRD Section 9)
        const primaryColor = "#0066FF";
        const brightColor = "#008CFF";

        // Thin blue bounding box
        ctx.strokeStyle = primaryColor;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(drawX, drawY, drawW, drawH);

        // Aviation corner accents on detection box
        const cornerSize = Math.min(8, Math.min(drawW, drawH) / 3);
        ctx.strokeStyle = brightColor;
        ctx.lineWidth = 2;

        // Top-left
        ctx.beginPath();
        ctx.moveTo(drawX, drawY + cornerSize);
        ctx.lineTo(drawX, drawY);
        ctx.lineTo(drawX + cornerSize, drawY);
        ctx.stroke();

        // Top-right
        ctx.beginPath();
        ctx.moveTo(drawX + drawW - cornerSize, drawY);
        ctx.lineTo(drawX + drawW, drawY);
        ctx.lineTo(drawX + drawW, drawY + cornerSize);
        ctx.stroke();

        // Bottom-left
        ctx.beginPath();
        ctx.moveTo(drawX, drawY + drawH - cornerSize);
        ctx.lineTo(drawX, drawY + drawH);
        ctx.lineTo(drawX + cornerSize, drawY + drawH);
        ctx.stroke();

        // Bottom-right
        ctx.beginPath();
        ctx.moveTo(drawX + drawW - cornerSize, drawY + drawH);
        ctx.lineTo(drawX + drawW, drawY + drawH);
        ctx.lineTo(drawX + drawW, drawY + drawH - cornerSize);
        ctx.stroke();

        // Label Badge
        const className = (det.class_name || "OBJECT").toUpperCase();
        const confPct = Math.round(det.confidence * 100);
        const labelText = det.track_id !== undefined
          ? `${className} #${det.track_id} ${confPct}%`
          : `${className} ${confPct}%`;

        ctx.font = "bold 10px monospace";
        const textMetrics = ctx.measureText(labelText);
        const textWidth = textMetrics.width;
        const badgeHeight = 16;
        const badgeY = Math.max(0, drawY - badgeHeight - 2);

        // Badge background: dark black with thin blue border
        ctx.fillStyle = "rgba(0, 0, 0, 0.85)";
        ctx.fillRect(drawX, badgeY, textWidth + 8, badgeHeight);
        ctx.strokeStyle = primaryColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(drawX, badgeY, textWidth + 8, badgeHeight);

        // Badge text: white with blue highlight
        ctx.fillStyle = "#FFFFFF";
        ctx.fillText(labelText, drawX + 4, badgeY + 12);
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
