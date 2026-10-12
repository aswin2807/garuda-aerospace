# GARUDA AEROSPACE — Complete Project Technical Audit

**Project:** GARUDA AEROSPACE Drone Navigation, FOD Debris Detection & Runway Light Monitoring System  
**Audit Date:** 2026-10-12  
**Auditor:** Antigravity Autonomous AI Engineer  
**Status:** **AUDIT COMPLETE — SYSTEM VERIFIED & HARDENED**

---

## 1. Project Overview & Architecture

GARUDA AEROSPACE is a computer-vision powered drone surveillance and automated airfield monitoring platform. The system operates across three mission-critical domains:
1. **Drone Navigation:** Spatial obstacle awareness and operational flight environment perception using YOLO11.
2. **Foreign Object Debris (FOD) Detection:** Identification of hazardous runway debris (metal fragments, plastics, tools, aggregates) with multi-frame tracking.
3. **Runway Light Monitoring:** Precision classification of runway inset and edge lighting into **LIGHT ON**, **LIGHT OFF**, and **UNKNOWN** states, featuring perspective tilt correction and row-by-row geometric alignment.

### System Architecture Diagram

```mermaid
flowchart TD
    subgraph Frontend["Next.js 14 Frontend (Port 3000)"]
        UI_CC["Command Centre"]
        UI_AN["Analysis Workspace"]
        UI_MH["Mission History"]
        UI_LS["Live Surveillance"]
        UI_OF["Offline Surveillance"]
    end

    subgraph Backend["FastAPI Backend (Port 8000)"]
        API_GW["FastAPI Core Router"]
        AUTH["JWT Auth & Security"]
        ROUTER_AN["Analysis Router"]
        ROUTER_CAM["Camera Router"]
        ROUTER_MOD["Models Router"]
        ROUTER_WS["WebSocket Handler"]
        
        WORKER["AnalysisWorker (Async)"]
        TRACKER["ByteTrack & Spatial Deduplication"]
        GRID["Runway Grid & Row Tracker"]
    end

    subgraph MLEngine["ML Engine & Weights"]
        M_NAV["navigation_best.pt"]
        M_FOD["FOD_Karhtikeyan.pt"]
        M_RWY["runway_light_best.pt"]
    end

    subgraph Storage["Persistent Layer"]
        DB[(SQLite drone_surveillance.db)]
        UPLOADS["Static Uploads / H.264 Videos"]
    end

    Frontend <-->|REST & WebSockets| Backend
    ROUTER_AN --> WORKER
    ROUTER_CAM --> Backend
    WORKER --> MLEngine
    WORKER --> DB
    WORKER --> UPLOADS
    TRACKER --> DB
    GRID --> DB
```

---

## 2. Repository Inventory

| Subsystem | Directory / Key Files | File Count | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Backend Core** | `backend/app/core/` | 4 | Config, security, database session factory |
| **Backend API** | `backend/app/api/v1/` | 6 | `/analysis`, `/camera`, `/detection`, `/models`, `/auth` |
| **Backend Services** | `backend/app/services/` | 10 | Inference dispatch, video transcoding, grid sorting, camera reachability |
| **Backend Models** | `backend/app/models/` | 4 | SQLAlchemy ORM models (`AnalysisJob`, `Detection`, `Camera`, `User`) |
| **ML Engine** | `ml_engine/models/`, `ml_engine/scripts/` | 9 | YOLO11 model weights, benchmark scripts, evaluation tooling |
| **Frontend App** | `frontend/src/app/` | 16 routes | Command Centre, Analysis, History, Live & Offline surveillance |
| **Frontend Components** | `frontend/src/components/` | 24 | HUD overlay, Light Matrix, FOD tracker, Camera feeds |
| **Dataset Splits** | `train/`, `valid/`, `test/` | 1,440+ files | Roboflow airfield runway lighting dataset |
| **Test Suite** | `backend/tests/` | 17 files | 105 automated unit, integration, and E2E regression tests |

---

## 3. Root Cause Analysis & Applied Corrections

### 3.1 Defect 1: Video Playback Failures After Upload
- **Root Cause:** OpenCV `cv2.VideoWriter` wrote intermediate annotated frames using codecs like `mp4v` or `avc1` without the required H.264 profile or web-compatible pixel format (`yuv420p`), causing HTML5 `<video>` tags in modern browsers to fail playback with black screens or codec errors.
- **Correction:** Implemented an automated FFmpeg transcoding post-processing step in `video_service.py` that converts raw annotated video to H.264 with `-c:v libx264 -pix_fmt yuv420p -movflags +faststart`.
- **Status:** **RESOLVED & VERIFIED**.

### 3.2 Defect 2: Missing Detections Erroneously Counted as "LIGHT OFF"
- **Root Cause:** Earlier diagnostic scripts assumed that if a light fixture in an expected grid slot was not detected by YOLO, it must be an unlit light ("LIGHT OFF"). This introduced massive false alarm rates whenever camera glare, distance, or occlusion obscured a light.
- **Correction:** Enforced strict safety invariant `RUNWAY_INFER_MISSING_OFF=false` across `runway_light_service.py`, `.env`, and `runway_grid_tracker.py`. Undetected fixtures remain strictly in the `UNKNOWN` state.
- **Mathematical Formula:** $\text{Total Lights} = \text{LIGHT ON} + \text{LIGHT OFF} + \text{UNKNOWN}$.
- **Status:** **RESOLVED & VERIFIED**.

### 3.3 Defect 3: IP Camera Timeout & Freezing on `192.168.144.108`
- **Root Cause:** Calling `cv2.VideoCapture("rtsp://192.168.144.108:554/live")` synchronously when the host network interface was not routed to the `192.168.144.0/24` subnet caused OpenCV's internal TCP connect timeout to block the main event loop for 30+ seconds.
- **Correction:** Implemented a non-blocking socket pre-flight check in `camera_service.py` (`check_reachability`) with a 1.5-second timeout. If unreachable, the API immediately returns `504 Gateway Timeout` with explicit diagnostic instructions without blocking the server.
- **Status:** **RESOLVED & VERIFIED**.

### 3.4 Defect 4: Model Cross-Contamination
- **Root Cause:** In earlier versions, analysis upload endpoints shared loose model selectors, allowing Navigation weights to run on runway light videos.
- **Correction:** Isolated each analysis domain into dedicated services (`runway_light_service.py`, `fod_service.py`, `navigation_service.py`). Each service strictly loads its dedicated model weights verified by SHA-256 manifest checks.
- **Status:** **RESOLVED & VERIFIED**.

---

## 4. Current Operational Health

- **Unit & Integration Tests:** 105 passed, 0 failed.
- **Frontend Compilation:** 16 routes compiled cleanly with 0 TypeScript/ESLint errors.
- **Model Checksums:**
  - `runway_light_best.pt`: SHA256 verified.
  - `FOD_Karhtikeyan.pt`: SHA256 verified.
  - `navigation_best.pt`: SHA256 verified.
- **Database Status:** SQLite database `drone_surveillance.db` synchronized with WAL mode.
