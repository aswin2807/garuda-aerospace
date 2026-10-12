# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Integrated AI Drone Navigation, FOD & Runway Light Detection Platform

### Version: 2.0 (Integrated Production Architecture)
### Project Type: Real-Time Drone / IP Camera AI Detection & Runway Monitoring Platform

---

## 1. Project Overview & Objective

The system provides a unified real-time AI platform for autonomous drone navigation, runway optical inspection, Foreign Object Debris (FOD) detection, and runway lighting fault monitoring.

The system connects to:
* IP / RTSP cameras (`rtsp://...`)
* Drone optical payloads
* Uploaded video files (`.mp4`, `.mov`, `.avi`)
* Local demonstration video feeds

Every video frame is sequentially ingested, processed through three independent YOLOv11 models, tracked across frames, deduplicated, persisted into SQLite (`drone_nav.db`), broadcast live over WebSockets, and rendered in the Next.js HUD.

---

## 2. Integrated AI Models

```text
VIDEO / RTSP / WEBCAM
         │
         ▼
┌──────────────────┐
│   FRAME READER   │ (LatestFrameReader for low-latency RTSP)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  FRAME PROCESSOR │ (Dynamic scheduling & stride caching)
└────────┬─────────┘
         │
  ┌──────┴──────────────────────────┐
  ▼                                 ▼
┌─────────────────────┐   ┌──────────────────────┐   ┌────────────────────────────────────────┐
│  NAVIGATION MODEL   │   │      FOD MODEL       │   │          RUNWAY LIGHT MODEL            │
│ navigation_best.pt  │   │ FOD_Karhtikeyan.pt   │   │         runway_light_best.pt           │
└─────────┬───────────┘   └──────────┬───────────┘   └───────────────────┬────────────────────┘
          │                          │                                   │
          │ Dynamic classes          │ High-sensitivity                  │ • 52% - 72% scan window
          │ from model.names         │ debris detection                  │ • Adaptive CLAHE/brighten/darken
          │                          │                                   │ • 640x640 tiled inference
          │                          │                                   │ • Non-maximum suppression (NMS)
          │                          │                                   │ • Quality filtering & paint rejection
          │                          │                                   │ • Neighboring light row pattern analysis
          │                          │                                   │ • ByteTrackLite tracking & smoothing
          │                          │                                   │ • OFF-GAP missing beacon inference
          │                          │                                   │ • 5-frame temporal fault confirmation
          └──────────────────────────┼───────────────────────────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │   DETECTION ENGINE     │
                        │ (Deduplication/Tracks) │
                        └────────────┬───────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
         ┌─────────────────────┐           ┌─────────────────────┐
         │  DATABASE SERVICE   │           │  WEBSOCKET SERVICE  │
         │ (drone_nav.db)      │           │ (/ws/v1/detection)  │
         └──────────┬──────────┘           └──────────┬──────────┘
                    │                                 │
                    ▼                                 ▼
         ┌─────────────────────┐           ┌─────────────────────┐
         │   EXPORT SERVICE    │           │     NEXT.JS HUD     │
         │ (CSV / JSON / MP4)  │           │   (Real-Time UI)    │
         └─────────────────────┘           └─────────────────────┘
```

### 2.1 Navigation Model (`navigation_best.pt`)
* **Path**: `ml_engine/models/navigation_best.pt`
* **Stride**: Every 1 frame
* **Classes**: Dynamically read from `model.names` (no hard-coded class names).

### 2.2 FOD Model (`FOD_Karhtikeyan.pt`)
* **Path**: `ml_engine/models/FOD_Karhtikeyan.pt`
* **Stride**: Every 1 frame
* **Role**: Identifies Foreign Object Debris on runways and tarmac with high sensitivity (`conf: 0.18`).

### 2.3 Runway Light Model (`runway_light_best.pt`)
* **Path**: `ml_engine/models/runway_light_best.pt`
* **Stride**: Every 10 frames (with mandatory first-frame execution)
* **Classes**: 0: `LIGHT OFF`, 1: `LIGHT ON`
* **Integrated Jetson Functionality**:
  * **Scan Window**: 52% start, 20% vertical coverage band (`scan_start: 0.52`, `scan_height: 0.20`).
  * **Adaptive Preprocessing**: `auto` (chooses CLAHE, brighten, or darken based on band mean brightness).
  * **Tiled Inference**: `tile_size: 640`, `tile_stride: 480`.
  * **NMS**: Overlap and IoU suppression across overlapping tiles.
  * **Quality Filtering**: Verifies box side lengths (2.5 to 70 px), maximum box area (2600 px²), and aspect ratio (0.25 to 4.0).
  * **Paint Rejection**: Analyzes patch HSV saturation, contrast, and white-pixel fraction to reject painted line markings and runway stains.
  * **Neighbor Pattern Validation**: Correlates OFF lights against adjacent ON light fixtures along the runway axis (`● ON ● ON ● OFF ● ON ● ON`).
  * **Temporal Fault Confirmation**: Requires 5 consecutive OFF observations before escalating from candidate to `CONFIRMED` runway fault.

---

## 3. Data Flow & End-to-End Guarantees

1. **No Client-Side Invention**: Frontend HUD numbers originate strictly from backend inference.
2. **Distinct Performance Display**:
   * **Stream FPS** (e.g. 30 FPS)
   * **Inference FPS** (e.g. 3.1 FPS)
   * **Inference Latency** (e.g. 322 ms)
3. **Database Records**: Every detection is persisted in `detections` and faults in `runway_faults` (`drone_nav.db`).
4. **Session Exporting**: Automatic generation of `session_XXX_detections.csv`, `session_XXX_summary.json`, and `session_XXX_annotated.mp4` in `data/outputs/`.

---

## 4. Frontend HUD Architecture

* `components/hud/NavigationHUD.tsx`: Unified master HUD with Standard and Runway Analytics views.
* `components/detection/DetectionCards.tsx`: 4 dynamic cards (`LIGHT ON`, `LIGHT OFF`, `FOD`, `NAV OBJ`).
* `components/detection/DetectionStats.tsx`: Detailed track and object statistics.
* `components/detection/ClassificationBreakdown.tsx`: Live class confidence bars.
* `components/navigation/NavigationObjects.tsx`: Navigation object list with coordinates and tracks.
* `components/runway/RunwayLightStatus.tsx`: Health meter, operational vs. faulty light percentage, and OFF-gap alerts.
* `components/runway/RunwayAlerts.tsx`: Active runway hazard banner.
* `components/camera/LiveCamera.tsx` & `VideoPlayer.tsx`: RTSP live streaming, video file upload, bounding box canvas, and bottom HUD ticker.
