import sys
from pathlib import Path

# Automatically inject project root and backend directory into sys.path
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parent.parent
_project_root = _backend_dir.parent

for _p in [str(_backend_dir), str(_project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.database import init_db
from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.drones import router as drones_router
from backend.app.api.missions import router as missions_router
from backend.app.api.detection import router as detection_router
from backend.app.api.telemetry import router as telemetry_router
from backend.app.api.camera import router as camera_router
from backend.app.api.models import router as models_router
from backend.app.api.video import router as video_router
from backend.app.api.sessions import router as sessions_router
from backend.app.api.debug import router as debug_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.command_centre_api import router as command_centre_api_router
from backend.app.api.navigation_api import router as navigation_api_router
from backend.app.api.fod_api import router as fod_api_router
from backend.app.api.runway_light_api import router as runway_light_api_router
from backend.app.api.surveillance_api import router as surveillance_api_router
from backend.app.websocket.detection_ws import router as ws_router
from backend.app.websocket.analysis_ws import router as analysis_ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Drone Navigation AI Backend...")
    init_db()
    logger.info("Database schemas initialized.")
    yield
    logger.info("Shutting down Drone Navigation AI Backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "drone-navigation-api",
        "version": settings.VERSION
    }

# Include Routers
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(drones_router, prefix=f"{settings.API_V1_STR}/drones", tags=["Drones"])
app.include_router(missions_router, prefix=f"{settings.API_V1_STR}/missions", tags=["Missions"])
app.include_router(detection_router, prefix=f"{settings.API_V1_STR}/detection", tags=["Detection"])
app.include_router(telemetry_router, prefix=f"{settings.API_V1_STR}/telemetry", tags=["Telemetry"])
app.include_router(camera_router, prefix=f"{settings.API_V1_STR}/camera", tags=["Camera"])
app.include_router(camera_router, prefix="/api/camera", tags=["Camera"])
app.include_router(models_router, prefix=f"{settings.API_V1_STR}/models", tags=["Models"])
app.include_router(models_router, prefix="/api/models", tags=["Models"])
app.include_router(video_router, prefix=f"{settings.API_V1_STR}", tags=["Video Analysis"])
app.include_router(video_router, prefix="/api", tags=["Video Analysis"])
app.include_router(sessions_router, prefix=f"{settings.API_V1_STR}", tags=["Analysis Sessions"])
app.include_router(sessions_router, prefix="/api", tags=["Analysis Sessions"])
app.include_router(debug_router, prefix=f"{settings.API_V1_STR}", tags=["Pipeline Debugging"])
app.include_router(debug_router, prefix="/api", tags=["Pipeline Debugging"])
app.include_router(analysis_router, prefix=f"{settings.API_V1_STR}", tags=["Media Analysis"])
app.include_router(analysis_router, prefix="/api", tags=["Media Analysis"])
app.include_router(navigation_api_router, prefix=f"{settings.API_V1_STR}", tags=["Navigation Analysis Engine"])
app.include_router(navigation_api_router, prefix="/api", tags=["Navigation Analysis Engine"])
app.include_router(fod_api_router, prefix=f"{settings.API_V1_STR}", tags=["FOD Debris Analysis Engine"])
app.include_router(fod_api_router, prefix="/api", tags=["FOD Debris Analysis Engine"])
app.include_router(runway_light_api_router, prefix=f"{settings.API_V1_STR}", tags=["Runway Light Fault Analysis Engine"])
app.include_router(runway_light_api_router, prefix="/api", tags=["Runway Light Fault Analysis Engine"])
app.include_router(command_centre_api_router, prefix=f"{settings.API_V1_STR}/command-centre", tags=["Garuda Aerospace Command Centre"])
app.include_router(command_centre_api_router, prefix="/api/command-centre", tags=["Garuda Aerospace Command Centre"])
app.include_router(surveillance_api_router, prefix=f"{settings.API_V1_STR}", tags=["Surveillance Engine"])
app.include_router(surveillance_api_router, prefix="/api", tags=["Surveillance Engine"])
app.include_router(ws_router, tags=["WebSockets"])
app.include_router(analysis_ws_router, tags=["Analysis WebSockets"])


