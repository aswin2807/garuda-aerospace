# ROD — Runway Observation and Detection Platform
### Garuda Aerospace Autonomous AI Surveillance, Drone Navigation & Safety Engine

ROD (Runway Observation and Detection) is an enterprise aviation safety platform integrating real-time drone navigation, YOLO11-based runway-lighting inspection, Foreign Object Debris (FOD) coordinate prediction, and tactical route planning.

---

## 1. System Architecture

```
                       ┌──────────────────────────────────────┐
                       │  Garuda Aerospace Drone Video / RTSP  │
                       │     (Live RTSP / Offline Upload)     │
                       └──────────────────┬───────────────────┘
                                          │
                                          ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                   ISOLATED TRI-MODEL ML ENGINE                         │
 │                                                                        │
 │  ┌───────────────────────┐ ┌──────────────────┐ ┌───────────────────┐  │
 │  │ runway_light_best.pt  │ │ FOD_Karhtikeyan  │ │ navigation_best   │  │
 │  │ (LIGHT OFF, LIGHT ON) │ │ (FOD Debris)     │ │ (80 Obstacle Cls) │  │
 │  │ Scan-Window & Matrix  │ │ Raycast Coords   │ │ Tactical Guidance │  │
 │  └───────────┬───────────┘ └────────┬─────────┘ └─────────┬─────────┘  │
 └──────────────┼──────────────────────┼─────────────────────┼────────────┘
                │                      │                     │
                └──────────────────────┼─────────────────────┘
                                       │
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                           FASTAPI BACKEND                              │
 │                                                                        │
 │ ┌──────────────────┐ ┌────────────────────┐ ┌────────────────────────┐ │
 │ │ REST API Routers │ │ WebSocket Server   │ │ SQLite / PostgreSQL    │ │
 │ │ Auth / Users     │ │ Live Telemetry     │ │ Detections, Missions   │ │
 │ │ Navigation Route │ │ Frame Streamer     │ │ Debris Coordinates     │ │
 │ │ Central Results  │ │ Alert Notification │ │ Audit Job History      │ │
 │ └──────────────────┘ └────────────────────┘ └────────────────────────┘ │
 └─────────────────────────────────────┬──────────────────────────────────┘
                                       │ REST / WebSocket
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                       NEXT.JS 14 HUD DASHBOARD                         │
 │                                                                        │
 │  ┌────────────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
 │  │ Tactical Navigation    │  │ Live Video HUD  │  │ Central Results │  │
 │  │ Interactive Geo Map    │  │ Emerald / Coral │  │ Debris Coords   │  │
 │  │ Waypoint Route Planner │  │ Clean Overlays  │  │ Light Matrix    │  │
 │  │ Telemetry PFD Indicator│  │ 0 Row Line Noise│  │ Audit Exports   │  │
 │  └────────────────────────┘  └─────────────────┘  └─────────────────┘  │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Model Specifications & Manifest

The system enforces strict model isolation across three specialized neural network models located in `ml_engine/models/`:

| Model File | Checksum (MD5) | Size | Verified Classes | Primary Application |
| :--- | :--- | :--- | :--- | :--- |
| **`runway_light_best.pt`** | `feffc665b9626ec084a935a108091d56` | 5.25 MB | `0: LIGHT OFF`<br>`1: LIGHT ON` | Runway lighting inspection, fault detection, and row/column grid tracking. |
| **`FOD_Karhtikeyan.pt`** | `748abf494500c9ee55aea8fc3c3b83a8` | 54.41 MB | `0: FOD` | Foreign Object Debris detection and bottom-center contact raycasting. |
| **`navigation_best.pt`** | `261474e91b15f5ef14a63c21ce6c0cbb` | 5.35 MB | 80 dynamic classes | Airfield obstacle detection, vehicle avoidance, and tactical guidance. |

---

## 3. Installation & Quickstart

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+ or 20+
- **macOS / Linux / Windows** (MPS hardware acceleration supported on Apple Silicon)

### Step 1: Backend Setup
```bash
# Navigate to project root
cd "$HOME/Desktop/navigation drone.v2i.yolov11"
source backend/venv/bin/activate

# Create or activate virtual environment
python3.11 -m venv backend/venv
source backend/venv/bin/activate

# Install Python dependencies
pip install -r backend/requirements.txt

python -m uvicorn app.main:app --reload --app-dir backend
```

### Step 2: Frontend Setup
```bash
cd frontend
npm install
npm run build   # Verify 22/22 routes compile cleanly
```

---

## 4. Running the Application

### Launch Backend Server
```bash
# From project root with venv activated
source backend/venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **Model Status:** [http://localhost:8000/api/v1/models/status](http://localhost:8000/api/v1/models/status)

### Launch Frontend Dashboard
```bash
# In another terminal
cd frontend
npm run dev
```
- **Web Dashboard:** [http://localhost:3000](http://localhost:3000)

---

## 5. Automated Testing & Verification

Run the full pytest suite (157 unit, integration, and security tests):
```bash
./backend/venv/bin/pytest backend/tests/ -v
```

Run the deep model audit & benchmark script:
```bash
./backend/venv/bin/python scripts/audit_models_deep.py
```

Run the labelled test-split accuracy benchmark:
```bash
./backend/venv/bin/python scripts/validate_test_dataset.py
```

Run the video overlay and clean prediction benchmark:
```bash
./backend/venv/bin/python ml_engine/scripts/evaluate_runway_detection_enhancement.py
```

---

## 6. Environment Variables Guide

Copy `.env.example` to `.env` to customize settings:
```bash
cp .env.example .env
```

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./drone_nav.db` | Database connection string (SQLite or PostgreSQL) |
| `JWT_SECRET` | *(auto-generated)* | Key for signing operator authentication tokens |
| `RTSP_URL` | `rtsp://192.168.144.108:554/stream=1` | Default camera video stream URL |
| `RUNWAY_SHOW_SCAN_WINDOW` | `false` | When false, eliminates horizontal row lines on video |
| `RUNWAY_SHOW_TRACK_IDS` | `false` | When false, keeps bounding box labels clean and concise |
| `RUNWAY_BOX_STYLE` | `full` | Bounding box rendering mode (`full` or `corner`) |
| `LIGHT_FAULT_CONFIRM_FRAMES` | `5` | Temporal frame threshold to confirm persistent light faults |

---

## 7. Troubleshooting

- **MPS / GPU Out of Memory:**
  If running on a device with limited unified memory, set `RUNWAY_IMGSZ=512` in `.env` to lower memory allocation during inference.
- **RTSP Camera Disconnected:**
  If an RTSP stream is unavailable, the UI will report `CONNECTING` or `DISCONNECTED` without freezing. To test offline, use the built-in demo feed: `demo://navigation_drone_feed`.
- **Port Conflict (8000 or 3000):**
  Change `API_PORT` in `.env` and `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.
