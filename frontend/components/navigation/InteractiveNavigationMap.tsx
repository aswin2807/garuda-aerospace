"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import { useNavigationStore } from "../../stores/navigationStore";

// Web Mercator conversions (WGS 84 / EPSG:3857)
function latLonToMeters(lat: number, lon: number): [number, number] {
  const x = (lon * 20037508.34) / 180;
  let y = Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180);
  y = (y * 20037508.34) / 180;
  return [x, y];
}

function metersToLatLon(x: number, y: number): [number, number] {
  const lon = (x / 20037508.34) * 180;
  let lat = (y / 20037508.34) * 180;
  lat = (180 / Math.PI) * (2 * Math.atan(Math.exp((lat * Math.PI) / 180)) - Math.PI / 2);
  return [lat, lon];
}

// Tile coordinate calculation
function lonToTileX(lon: number, zoom: number): number {
  return Math.floor(((lon + 180) / 360) * Math.pow(2, zoom));
}

function latToTileY(lat: number, zoom: number): number {
  const latRad = (lat * Math.PI) / 180;
  return Math.floor(
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * Math.pow(2, zoom)
  );
}

function tileXToLon(x: number, zoom: number): number {
  return (x / Math.pow(2, zoom)) * 360 - 180;
}

function tileYToLat(y: number, zoom: number): number {
  const n = Math.PI - (2 * Math.PI * y) / Math.pow(2, zoom);
  return (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
}

// In-memory tile cache to avoid repeated HTTP requests
const tileImageCache = new Map<string, HTMLImageElement>();

export function InteractiveNavigationMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const {
    telemetry,
    target,
    waypoints,
    calculatedRoute,
    guidance,
    activeWaypointIndex,
    navigationMode,
    mapClickMode,
    mapStyle,
    showAirfieldOverlay,
    setTarget,
    addWaypoint,
    setMapStyle,
    toggleAirfieldOverlay,
  } = useNavigationStore();

  // Map view state: Center (Lat/Lon) and Zoom (standard web Mercator zoom level: 12 - 19)
  const [mapCenter, setMapCenter] = useState<[number, number]>([13.0827, 80.2707]);
  const [zoom, setZoom] = useState<number>(15.5);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lon: number } | null>(null);

  // Keep map centered on drone when first connecting if valid coordinates exist
  useEffect(() => {
    if (telemetry?.connected && telemetry.latitude && telemetry.longitude) {
      setMapCenter([telemetry.latitude, telemetry.longitude]);
    }
  }, [telemetry?.connected]);

  // Screen to Map coordinate conversion (WGS 84)
  const screenToLatLon = useCallback(
    (screenX: number, screenY: number, width: number, height: number): [number, number] => {
      const [centerX, centerY] = latLonToMeters(mapCenter[0], mapCenter[1]);
      const resolution = (20037508.34 * 2) / (256 * Math.pow(2, zoom));
      const deltaX = (screenX - width / 2) * resolution;
      const deltaY = -(screenY - height / 2) * resolution;
      return metersToLatLon(centerX + deltaX, centerY + deltaY);
    },
    [mapCenter, zoom]
  );

  // Map to Screen coordinate conversion (WGS 84)
  const latLonToScreen = useCallback(
    (lat: number, lon: number, width: number, height: number): [number, number] => {
      const [x, y] = latLonToMeters(lat, lon);
      const [centerX, centerY] = latLonToMeters(mapCenter[0], mapCenter[1]);
      const resolution = (20037508.34 * 2) / (256 * Math.pow(2, zoom));
      const screenX = width / 2 + (x - centerX) / resolution;
      const screenY = height / 2 - (y - centerY) / resolution;
      return [screenX, screenY];
    },
    [mapCenter, zoom]
  );

  // Render Map Canvas
  const renderMap = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // 1. Background Grid & Basemap (FR-01)
    if (mapStyle === "TACTICAL") {
      ctx.fillStyle = "#0A0F1D"; // Aerospace dark navy
      ctx.fillRect(0, 0, width, height);

      // Coordinate grid lines
      ctx.strokeStyle = "rgba(148, 163, 184, 0.08)";
      ctx.lineWidth = 1;
      const gridSize = 60;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
    } else {
      // High-contrast clean streets/light style
      ctx.fillStyle = "#0F172A";
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = "rgba(56, 189, 248, 0.06)";
      ctx.lineWidth = 1;
      const gridSize = 50;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
    }

    // Try rendering Web Mercator map tiles if available
    const tileZoom = Math.min(18, Math.max(1, Math.floor(zoom)));
    const tileResolution = (20037508.34 * 2) / (256 * Math.pow(2, zoom));
    const centerTileX = lonToTileX(mapCenter[1], tileZoom);
    const centerTileY = latToTileY(mapCenter[0], tileZoom);
    const tilesRadius = 3;

    for (let dx = -tilesRadius; dx <= tilesRadius; dx++) {
      for (let dy = -tilesRadius; dy <= tilesRadius; dy++) {
        const tx = centerTileX + dx;
        const ty = centerTileY + dy;
        const maxTiles = Math.pow(2, tileZoom);
        if (tx < 0 || tx >= maxTiles || ty < 0 || ty >= maxTiles) continue;

        const tileLon = tileXToLon(tx, tileZoom);
        const tileLat = tileYToLat(ty, tileZoom);
        const [screenX, screenY] = latLonToScreen(tileLat, tileLon, width, height);

        // Tile dimension in screen pixels
        const tileScreenSize = 256 * Math.pow(2, zoom - tileZoom);

        // Subdomain distribution
        const sub = ["a", "b", "c", "d"][(tx + ty) % 4];
        let tileUrl = "";
        if (mapStyle === "STREETS") {
          tileUrl = `https://${sub}.basemaps.cartocdn.com/rastertiles/voyager/${tileZoom}/${tx}/${ty}.png`;
        } else if (mapStyle === "TACTICAL") {
          tileUrl = `https://${sub}.basemaps.cartocdn.com/dark_all/${tileZoom}/${tx}/${ty}.png`;
        } else {
          tileUrl = `https://${sub}.tile.openstreetmap.org/${tileZoom}/${tx}/${ty}.png`;
        }

        let img = tileImageCache.get(tileUrl);
        if (!img) {
          img = new Image();
          img.crossOrigin = "anonymous";
          img.src = tileUrl;
          img.onload = () => {
            renderMap();
          };
          tileImageCache.set(tileUrl, img);
        } else if (img.complete && img.naturalWidth > 0) {
          ctx.drawImage(img, screenX, screenY, tileScreenSize, tileScreenSize);
        }
      }
    }

    // 2. Airfield Runway Schematic Overlay (FR-01: Explicitly toggleable reference)
    if (showAirfieldOverlay) {
      const runwayLat = 13.0827;
      const runwayLon = 80.2707;
      const [rX, rY] = latLonToScreen(runwayLat, runwayLon, width, height);

      // Draw runway schematic if within visible viewport
      if (rX > -300 && rX < width + 300 && rY > -300 && rY < height + 300) {
        ctx.save();
        ctx.translate(rX, rY);
        ctx.rotate((-25 * Math.PI) / 180); // Runway heading 065°/245°
        ctx.fillStyle = "rgba(30, 41, 59, 0.85)";
        ctx.fillRect(-220, -18, 440, 36);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.5)";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(-220, -18, 440, 36);

        // Centerline dashes
        ctx.strokeStyle = "rgba(250, 204, 21, 0.8)";
        ctx.lineWidth = 2;
        ctx.setLineDash([12, 10]);
        ctx.beginPath();
        ctx.moveTo(-200, 0);
        ctx.lineTo(200, 0);
        ctx.stroke();
        ctx.setLineDash([]);

        // Threshold markings
        ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
        ctx.font = "bold 11px monospace";
        ctx.fillText("07", -210, 5);
        ctx.fillText("25", 195, 5);

        ctx.restore();
      }
    }

    // 3. Flight Path Polyline (FR-04, FR-05, FR-11)
    if (calculatedRoute && calculatedRoute.all_points.length > 1) {
      const points = calculatedRoute.all_points.map((pt) =>
        latLonToScreen(pt.lat, pt.lon, width, height)
      );

      // Glow effect based on active navigation mode
      const isLiveGuidance = navigationMode === "LIVE_GUIDANCE";
      const isPreview = navigationMode === "PREVIEW";

      ctx.shadowBlur = isLiveGuidance ? 14 : isPreview ? 8 : 4;
      ctx.shadowColor = isLiveGuidance
        ? "rgba(16, 185, 129, 0.9)"
        : isPreview
        ? "rgba(245, 158, 11, 0.8)"
        : "rgba(6, 182, 212, 0.8)";

      ctx.strokeStyle = isLiveGuidance
        ? "#10B981"
        : isPreview
        ? "#F59E0B"
        : "#06B6D4";

      ctx.lineWidth = isLiveGuidance ? 3.5 : 2.5;

      if (navigationMode === "PLANNING") {
        ctx.setLineDash([8, 6]);
      } else {
        ctx.setLineDash([]);
      }

      ctx.beginPath();
      ctx.moveTo(points[0][0], points[0][1]);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i][0], points[i][1]);
      }
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.shadowBlur = 0;

      // Draw segment distance & bearing badges along the path
      for (let i = 0; i < calculatedRoute.segments.length; i++) {
        const seg = calculatedRoute.segments[i];
        const [x1, y1] = latLonToScreen(seg.from_lat, seg.from_lon, width, height);
        const [x2, y2] = latLonToScreen(seg.to_lat, seg.to_lon, width, height);
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;

        const distLabel =
          seg.distance_m >= 1000
            ? `${(seg.distance_m / 1000).toFixed(2)}km`
            : `${seg.distance_m}m`;
        const label = `${distLabel} · ${seg.initial_bearing_deg}° (${seg.compass_direction})`;

        ctx.fillStyle = "rgba(15, 23, 42, 0.9)";
        ctx.strokeStyle = isLiveGuidance ? "#10B981" : "#38BDF8";
        ctx.lineWidth = 1;
        ctx.font = "bold 10px monospace";
        const metrics = ctx.measureText(label);
        const padX = 6;
        const padY = 4;
        ctx.fillRect(
          midX - metrics.width / 2 - padX,
          midY - 8 - padY,
          metrics.width + padX * 2,
          16 + padY
        );
        ctx.strokeRect(
          midX - metrics.width / 2 - padX,
          midY - 8 - padY,
          metrics.width + padX * 2,
          16 + padY
        );
        ctx.fillStyle = "#E0F2FE";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, midX, midY + 1);
      }
    }

    // 4. Numbered Waypoints Markers (FR-04, FR-05)
    waypoints.forEach((wp) => {
      const [wx, wy] = latLonToScreen(wp.latitude, wp.longitude, width, height);

      // Marker Outer Ring
      ctx.beginPath();
      ctx.arc(wx, wy, 14, 0, Math.PI * 2);
      ctx.fillStyle = "#0284C7";
      ctx.fill();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = "#BAE6FD";
      ctx.stroke();

      // Number
      ctx.fillStyle = "#FFFFFF";
      ctx.font = "bold 11px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(wp.order), wx, wy);

      // Altitude badge
      const altLabel = `${wp.altitude_agl_m || 30}m`;
      ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
      ctx.font = "9px monospace";
      ctx.fillRect(wx - 18, wy + 16, 36, 14);
      ctx.fillStyle = "#38BDF8";
      ctx.fillText(altLabel, wx, wy + 23);
    });

    // 5. Target Location Marker (FR-03)
    if (target) {
      const [tx, ty] = latLonToScreen(target.latitude, target.longitude, width, height);

      // Outer animated reticle
      ctx.beginPath();
      ctx.arc(tx, ty, 22, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(239, 68, 68, 0.4)";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(tx, ty, 14, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
      ctx.fill();
      ctx.strokeStyle = "#EF4444";
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Center crosshairs
      ctx.strokeStyle = "#EF4444";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(tx - 18, ty);
      ctx.lineTo(tx + 18, ty);
      ctx.moveTo(tx, ty - 18);
      ctx.lineTo(tx, ty + 18);
      ctx.stroke();

      // Target Label
      ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
      ctx.font = "bold 11px sans-serif";
      const name = target.name || "TARGET";
      const tMetrics = ctx.measureText(name);
      ctx.fillRect(tx - tMetrics.width / 2 - 8, ty - 34, tMetrics.width + 16, 18);
      ctx.strokeStyle = "#EF4444";
      ctx.strokeRect(tx - tMetrics.width / 2 - 8, ty - 34, tMetrics.width + 16, 18);
      ctx.fillStyle = "#FCA5A5";
      ctx.textAlign = "center";
      ctx.fillText(name, tx, ty - 22);
    }

    // 6. Drone Marker & Heading Vector (FR-02: Never simulate movement silently)
    const isConnected = telemetry?.connected ?? false;
    const isStale = telemetry?.is_stale ?? true;
    const isSimulated = telemetry?.status === "SIMULATED";

    let dLat = telemetry?.latitude;
    let dLon = telemetry?.longitude;
    const hasCoordinates = dLat != null && dLon != null;

    if (hasCoordinates) {
      const [dx, dy] = latLonToScreen(dLat!, dLon!, width, height);
      const heading = telemetry?.heading ?? 0;

      // Heading cone (only if live or simulated active)
      if (isConnected && !isStale) {
        const coneRad = (heading * Math.PI) / 180;
        const coneLength = 50;
        const spread = 0.35;
        ctx.save();
        ctx.translate(dx, dy);
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(
          Math.sin(coneRad - spread) * coneLength,
          -Math.cos(coneRad - spread) * coneLength
        );
        ctx.arc(
          0,
          0,
          coneLength,
          coneRad - Math.PI / 2 - spread,
          coneRad - Math.PI / 2 + spread
        );
        ctx.closePath();
        ctx.fillStyle = isSimulated
          ? "rgba(245, 158, 11, 0.18)"
          : "rgba(16, 185, 129, 0.18)";
        ctx.fill();
        ctx.restore();
      }

      // Drone Outer Ring
      ctx.beginPath();
      ctx.arc(dx, dy, 18, 0, Math.PI * 2);
      ctx.fillStyle = isSimulated
        ? "rgba(245, 158, 11, 0.25)"
        : isConnected && !isStale
        ? "rgba(16, 185, 129, 0.25)"
        : "rgba(100, 116, 139, 0.25)";
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = isSimulated
        ? "#F59E0B"
        : isConnected && !isStale
        ? "#10B981"
        : "#94A3B8";
      ctx.stroke();

      // Drone Body
      ctx.beginPath();
      ctx.arc(dx, dy, 8, 0, Math.PI * 2);
      ctx.fillStyle = isSimulated
        ? "#F59E0B"
        : isConnected && !isStale
        ? "#10B981"
        : "#64748B";
      ctx.fill();

      // Direction needle
      const rad = (heading * Math.PI) / 180;
      ctx.beginPath();
      ctx.moveTo(dx, dy);
      ctx.lineTo(dx + Math.sin(rad) * 22, dy - Math.cos(rad) * 22);
      ctx.strokeStyle = "#FFFFFF";
      ctx.lineWidth = 3;
      ctx.stroke();

      // Drone Status Tag
      const droneTag = isSimulated
        ? "SIMULATED DRONE"
        : isConnected && !isStale
        ? "GARUDA-DRONE (LIVE)"
        : "DRONE (STALE/OFFLINE)";

      ctx.fillStyle = isSimulated ? "#B45309" : isConnected && !isStale ? "#065F46" : "#334155";
      ctx.font = "bold 9px monospace";
      ctx.textAlign = "center";
      ctx.fillText(droneTag, dx, dy + 28);
    }

    // 7. Dynamic Geographic Scale Bar (FR-01: Visual calibration validation)
    const [centerMetersX, centerMetersY] = latLonToMeters(mapCenter[0], mapCenter[1]);
    const metersPerPixel =
      ((20037508.34 * 2) / (256 * Math.pow(2, zoom))) *
      Math.cos((mapCenter[0] * Math.PI) / 180);

    // Pick rounded target bar width (e.g. 50m, 100m, 200m, 500m, 1km, 2km, 5km)
    const desiredBarPixels = 100;
    const targetMeters = desiredBarPixels * metersPerPixel;
    const magnitude = Math.pow(10, Math.floor(Math.log10(targetMeters)));
    let niceMeters = magnitude;
    if (targetMeters / magnitude >= 5) niceMeters = 5 * magnitude;
    else if (targetMeters / magnitude >= 2) niceMeters = 2 * magnitude;

    const actualBarPixels = niceMeters / metersPerPixel;
    const scaleX = 20;
    const scaleY = height - 42;

    ctx.strokeStyle = "rgba(255, 255, 255, 0.8)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(scaleX, scaleY - 5);
    ctx.lineTo(scaleX, scaleY);
    ctx.lineTo(scaleX + actualBarPixels, scaleY);
    ctx.lineTo(scaleX + actualBarPixels, scaleY - 5);
    ctx.stroke();

    const scaleText = niceMeters >= 1000 ? `${(niceMeters / 1000).toFixed(1)} km` : `${niceMeters} m`;
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.font = "10px monospace";
    ctx.textAlign = "center";
    ctx.fillText(scaleText, scaleX + actualBarPixels / 2, scaleY - 7);
  }, [
    mapCenter,
    zoom,
    mapStyle,
    showAirfieldOverlay,
    calculatedRoute,
    waypoints,
    target,
    telemetry,
    navigationMode,
    latLonToScreen,
  ]);

  // Redraw when dependencies change
  useEffect(() => {
    renderMap();
  }, [renderMap]);

  // Handle Canvas Resize
  useEffect(() => {
    const handleResize = () => {
      const container = containerRef.current;
      const canvas = canvasRef.current;
      if (container && canvas) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        renderMap();
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [renderMap]);

  // Mouse interaction: Panning
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;

    // Track cursor coordinates in WGS 84
    const [lat, lon] = screenToLatLon(screenX, screenY, canvas.width, canvas.height);
    setCursorCoords({ lat: Number(lat.toFixed(6)), lon: Number(lon.toFixed(6)) });

    if (!isDragging || !dragStart) return;

    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;

    if (Math.hypot(dx, dy) > 2) {
      const resolution = (20037508.34 * 2) / (256 * Math.pow(2, zoom));
      const [centerX, centerY] = latLonToMeters(mapCenter[0], mapCenter[1]);
      const newMetersX = centerX - dx * resolution;
      const newMetersY = centerY + dy * resolution;
      const newCoords = metersToLatLon(newMetersX, newMetersY);
      setMapCenter(newCoords);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragStart(null);
  };

  // Map Click to Set Target or Add Waypoint (FR-03, FR-04)
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;
    const [lat, lon] = screenToLatLon(screenX, screenY, canvas.width, canvas.height);

    if (mapClickMode === "TARGET") {
      setTarget({
        latitude: Number(lat.toFixed(7)),
        longitude: Number(lon.toFixed(7)),
        name: `Map Target (${lat.toFixed(4)}°, ${lon.toFixed(4)}°)`,
      });
    } else if (mapClickMode === "WAYPOINT") {
      addWaypoint({
        latitude: Number(lat.toFixed(7)),
        longitude: Number(lon.toFixed(7)),
        altitude_agl_m: 30.0,
      });
    }
  };

  // Wheel Zoom
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.35 : -0.35;
    setZoom((z) => Math.min(19, Math.max(12, Number((z + delta).toFixed(2)))));
  };

  // Recenter Drone
  const recenterDrone = () => {
    if (telemetry?.latitude && telemetry?.longitude) {
      setMapCenter([telemetry.latitude, telemetry.longitude]);
      setZoom(16.5);
    } else {
      setMapCenter([13.0827, 80.2707]);
      setZoom(16.0);
    }
  };

  // Fit Route Bounds
  const recenterRoute = () => {
    if (calculatedRoute && calculatedRoute.all_points.length > 0) {
      const lats = calculatedRoute.all_points.map((p) => p.lat);
      const lons = calculatedRoute.all_points.map((p) => p.lon);
      const minLat = Math.min(...lats);
      const maxLat = Math.max(...lats);
      const minLon = Math.min(...lons);
      const maxLon = Math.max(...lons);
      setMapCenter([(minLat + maxLat) / 2, (minLon + maxLon) / 2]);
      setZoom(15.0);
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[500px] flex-1 bg-[#0A0F1D] rounded-xl overflow-hidden border border-[#1E293B] shadow-inner select-none"
    >
      {/* Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleCanvasClick}
        onWheel={handleWheel}
        className="w-full h-full cursor-crosshair block"
      />

      {/* Top Floating Controls Bar */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
        {/* Click Mode Toggle Pill */}
        <div className="pointer-events-auto flex items-center gap-1 bg-[#0F172A]/90 backdrop-blur-md p-1.5 rounded-lg border border-[#334155] shadow-lg text-xs">
          <span className="text-slate-400 font-semibold px-2">CLICK MODE:</span>
          <button
            onClick={() => useNavigationStore.getState().setMapClickMode("TARGET")}
            className={`px-3 py-1 rounded font-medium transition ${
              mapClickMode === "TARGET"
                ? "bg-red-600 text-white shadow-sm"
                : "text-slate-300 hover:bg-[#1E293B]"
            }`}
          >
            🎯 Set Target
          </button>
          <button
            onClick={() => useNavigationStore.getState().setMapClickMode("WAYPOINT")}
            className={`px-3 py-1 rounded font-medium transition ${
              mapClickMode === "WAYPOINT"
                ? "bg-cyan-600 text-white shadow-sm"
                : "text-slate-300 hover:bg-[#1E293B]"
            }`}
          >
            📍 Add Waypoint
          </button>
          <button
            onClick={() => useNavigationStore.getState().setMapClickMode("NONE")}
            className={`px-2.5 py-1 rounded font-medium transition ${
              mapClickMode === "NONE"
                ? "bg-slate-700 text-white"
                : "text-slate-400 hover:bg-[#1E293B]"
            }`}
          >
            🖐 Pan Only
          </button>
        </div>

        {/* View Style, Airfield Overlay & Recenter Controls */}
        <div className="pointer-events-auto flex items-center gap-1.5 bg-[#0F172A]/90 backdrop-blur-md p-1.5 rounded-lg border border-[#334155] shadow-lg text-xs">
          <button
            onClick={recenterDrone}
            title="Recenter on Drone"
            className="flex items-center gap-1 px-2.5 py-1 bg-[#1E293B] hover:bg-[#334155] text-emerald-400 rounded transition font-medium border border-[#334155]"
          >
            🛰 Recenter Drone
          </button>
          <button
            onClick={recenterRoute}
            title="Fit Route Bounds"
            className="flex items-center gap-1 px-2.5 py-1 bg-[#1E293B] hover:bg-[#334155] text-cyan-400 rounded transition font-medium border border-[#334155]"
          >
            📐 Fit Route
          </button>
          <button
            onClick={toggleAirfieldOverlay}
            title="Toggle Schematic Runway Overlay"
            className={`px-2.5 py-1 rounded transition font-medium border border-[#334155] ${
              showAirfieldOverlay
                ? "bg-cyan-950 text-cyan-300 border-cyan-700"
                : "bg-[#1E293B] text-slate-400"
            }`}
          >
            ✈ Airfield Overlay
          </button>
          <button
            onClick={() =>
              setMapStyle(
                mapStyle === "TACTICAL"
                  ? "STREETS"
                  : mapStyle === "STREETS"
                  ? "SATELLITE"
                  : "TACTICAL"
              )
            }
            className="px-2.5 py-1 bg-[#1E293B] hover:bg-[#334155] text-slate-200 rounded transition font-medium border border-[#334155]"
          >
            {mapStyle === "TACTICAL"
              ? "🌌 Dark Tactical"
              : mapStyle === "STREETS"
              ? "🗺 Carto Streets"
              : "🛰 OSM Tiles"}
          </button>
        </div>
      </div>

      {/* Right Side Zoom Controls */}
      <div className="absolute right-3 bottom-14 flex flex-col gap-1.5 pointer-events-auto">
        <button
          onClick={() => setZoom((z) => Math.min(19, z + 1))}
          className="w-9 h-9 flex items-center justify-center bg-[#0F172A]/90 hover:bg-[#1E293B] text-slate-100 rounded-lg border border-[#334155] shadow-lg font-bold text-lg transition active:scale-95"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(12, z - 1))}
          className="w-9 h-9 flex items-center justify-center bg-[#0F172A]/90 hover:bg-[#1E293B] text-slate-100 rounded-lg border border-[#334155] shadow-lg font-bold text-lg transition active:scale-95"
          title="Zoom Out"
        >
          -
        </button>
      </div>

      {/* Bottom Status / Survey Coordinates Bar */}
      <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-[11px] text-slate-400 bg-[#0F172A]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#334155] pointer-events-none">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                telemetry?.status === "SIMULATED"
                  ? "bg-amber-400 animate-pulse"
                  : telemetry?.connected && !telemetry?.is_stale
                  ? "bg-emerald-400 animate-pulse"
                  : "bg-slate-500"
              }`}
            />
            <strong className="text-slate-200">
              {telemetry?.status === "SIMULATED"
                ? "SIMULATED POSITION"
                : telemetry?.connected && !telemetry?.is_stale
                ? "LIVE GPS FIX"
                : telemetry?.status || "OFFLINE"}
            </strong>
          </span>
          <span className="hidden sm:inline">
            CRS: <strong className="text-slate-300">WGS 84 (EPSG:3857)</strong>
          </span>
          <span>Zoom: {zoom.toFixed(1)}x</span>
          {target && (
            <span className="text-red-400 font-mono">
              Target: {target.latitude.toFixed(5)}°, {target.longitude.toFixed(5)}°
            </span>
          )}
        </div>
        <div>
          {cursorCoords ? (
            <span className="font-mono text-cyan-300">
              Cursor: {cursorCoords.lat.toFixed(6)}° N, {cursorCoords.lon.toFixed(6)}° E
            </span>
          ) : (
            <span>Hover on map to survey coordinates</span>
          )}
        </div>
      </div>
    </div>
  );
}
