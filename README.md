# Drone Navigation AI — YOLOv11 + FastAPI + Next.js 14 HUD

AI-powered drone navigation dashboard that uses a **YOLOv11** object detection model to identify optical beacons, runway lights, and obstacles from drone camera footage in real time.

---

## Architecture Overview

```
                       ┌─────────────────────────┐
                       │  YOLOv11 Navigation DB  │
                       │   (3,462 Images 512x512) │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │        ML ENGINE        │
                       │                         │
                       │ Train / Validate        │
                       │ Evaluate / Export       │
                       └────────────┬────────────┘
                                    │
                                 best.pt
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                               │
│                                                                        │
│ ┌────────────────┐    ┌─────────────────┐    ┌───────────────────────┐ │
│ │ REST APIs      │    │ WebSockets      │    │ YOLOv11 Inference     │ │
│ │ Auth / Drones  │    │ Frame Stream    │    │ Ultralytics / PyTorch │ │
│ │ Missions       │    │ Telemetry       │    │ NMS & Latency Measure │ │
│ └────────────────┘    └────────┬────────┘    └───────────┬───────────┘ │
│                                │                         │             │
│                                └────────────┬────────────┘             │
│                                             │                          │
│                                    PostgreSQL / SQLite                 │
└─────────────────────────────────────────────┬──────────────────────────┘
                                              │ REST / WebSocket
                                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS 14 HUD DASHBOARD                        │
│                                                                        │
│  ┌────────────────┐    ┌─────────────────────────┐    ┌──────────────┐ │
│  │ Telemetry PFD  │    │ Live Camera Feed        │    │ Detections   │ │
│  │                │    │                         │    │              │ │
│  │ GPS & Altitude │    │  ┌───────────────────┐  │    │ Class Counts │ │
│  │ Speed & Heading│    │  │ HTML5 Canvas      │  │    │ Confidence   │ │
│  │ Battery Gauge  │    │  │ Dynamic BBoxes    │  │    │ Threshold    │ │
│  └────────────────┘    │  └───────────────────┘  │    └──────────────┘ │
│                        └─────────────────────────┘                     │
│                             TACTICAL HUD LAYOUT                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
.
├── ml_engine/                      # YOLOv11 model training & validation
│   ├── datasets/                   # Linked dataset (3,462 images) & data.yaml
│   ├── models/trained/best.pt      # Production model weights
│   ├── scripts/                    # train.py, validate.py, predict.py, export.py
│   ├── configs/training.yaml       # Hyperparameters configuration
│   └── requirements.txt
│
├── backend/                        # FastAPI ASGI service
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point & CORS
│   │   ├── api/                    # REST routers: auth, drones, missions, detection
│   │   ├── core/                   # config, security, logging
│   │   ├── db/                     # SQLAlchemy models & migrations
│   │   ├── schemas/                # Pydantic v2 schemas
│   │   ├── services/               # Inference & telemetry services
│   │   └── websocket/              # Real-time frame streaming WS
│   ├── tests/                      # Automated pytest suite
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                       # Next.js 14 Mission Control HUD
│   ├── app/
│   │   ├── page.tsx                # HUD Dashboard root
│   │   ├── dashboard/              # Mission Control page
│   │   ├── detections/             # Detection audit table & filters
│   │   ├── missions/               # Mission planner & lifecycle
│   │   └── settings/               # System health & endpoints
│   ├── components/
│   │   ├── hud/                    # TopBar, DroneStatus, DetectionPanel, Telemetry
│   │   └── camera/                 # LiveCamera, DetectionCanvas overlay
│   ├── hooks/useWebSocket.ts       # Real-time WS frame streaming
│   ├── stores/droneStore.ts        # Zustand reactive state store
│   └── package.json
│
├── docker-compose.yml              # Multi-container orchestration
├── .env.example
├── Makefile
└── README.md
```

---

## Quickstart

### 1. Run Automated Tests
```bash
python3 -m pytest backend/tests
```

### 2. Train / Validate YOLOv11 Model
```bash
python3 ml_engine/scripts/train.py --config ml_engine/configs/training.yaml
python3 ml_engine/scripts/validate.py --model ml_engine/models/trained/best.pt
```

### 3. Run FastAPI Backend
```bash
uvicorn backend.app.main:app --reload --port 8000
```
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run Next.js 14 HUD Frontend
```bash
cd frontend
npm install
npm run dev
```
* **Mission Control HUD:** [http://localhost:3000](http://localhost:3000)

### 5. Run via Docker Compose
```bash
docker compose up --build
```
