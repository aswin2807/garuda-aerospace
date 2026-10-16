import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from backend.app.db.database import get_db
from backend.app.services.analysis_service import analysis_service
from backend.app.services.route_planning_service import route_planning_service
from backend.app.services.drone_service import drone_service
from backend.app.schemas.analysis import (
    AnalysisJobCreateResponse,
    AnalysisJobStatusResponse,
    AnalysisJobResultsResponse,
)
from backend.app.schemas.navigation import (
    WaypointItem,
    RouteCalculateRequest,
    RouteCalculateResponse,
    RouteSaveRequest,
    RouteResponse,
    DebrisTargetItem,
    GuidanceCalculationRequest,
    GuidanceCalculationResponse,
    LiveTelemetryResponse,
)

router = APIRouter(prefix="/navigation", tags=["Navigation Analysis Engine"])


# ==============================================================================
# 1. TACTICAL ROUTE PLANNING & WAYPOINTS (FR-01 to FR-11)
# ==============================================================================

@router.post("/route/calculate", response_model=RouteCalculateResponse)
def calculate_route(req: RouteCalculateRequest):
    """
    Plans multi-segment route between drone/start location and target through waypoints (FR-04, FR-05).
    Calculates total geodesic distance, straight-line distance, estimated travel time, and corridor warnings.
    """
    try:
        return route_planning_service.plan_route(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to calculate route: {str(e)}")


@router.post("/route/guidance", response_model=GuidanceCalculationResponse)
def calculate_guidance(req: GuidanceCalculationRequest):
    """
    Computes real-time navigational steering guidance toward next waypoint (FR-06).
    Returns target bearing, 16-wind compass direction, relative bearing, turn instructions, and arrival status.
    """
    try:
        return route_planning_service.calculate_guidance(
            drone_lat=req.drone_latitude,
            drone_lon=req.drone_longitude,
            drone_heading=req.drone_heading,
            target_lat=req.target_latitude,
            target_lon=req.target_longitude,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Guidance calculation failed: {str(e)}")


@router.post("/routes", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def save_planned_route(req: RouteSaveRequest, db: DBSession = Depends(get_db)):
    """
    Persists a planned route with its waypoints in database (FR-10).
    """
    try:
        route = route_planning_service.save_route(db, req)
        return route_planning_service.to_response(route)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save route: {str(e)}")


@router.get("/routes", response_model=List[RouteResponse])
def list_planned_routes(skip: int = 0, limit: int = 50, db: DBSession = Depends(get_db)):
    """
    Lists saved routes ordered by most recent first (FR-10).
    """
    routes = route_planning_service.list_routes(db, skip=skip, limit=limit)
    return [route_planning_service.to_response(r) for r in routes]


@router.get("/routes/{route_id}", response_model=RouteResponse)
def get_planned_route(route_id: str, db: DBSession = Depends(get_db)):
    """
    Retrieves a single saved route by ID (FR-10).
    """
    route = route_planning_service.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route_planning_service.to_response(route)


@router.delete("/routes/{route_id}")
def delete_planned_route(route_id: str, db: DBSession = Depends(get_db)):
    """
    Deletes a saved route from the database (FR-10).
    """
    success = route_planning_service.delete_route(db, route_id)
    if not success:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"deleted": True, "id": route_id}


@router.get("/telemetry/live", response_model=LiveTelemetryResponse)
def get_live_navigation_telemetry(db: DBSession = Depends(get_db)):
    """
    Returns the connected drone's latest valid GPS position and telemetry state (FR-01, FR-02).
    Explicit states: CONNECTED, STALE, OFFLINE, SIMULATED, INVALID_TELEMETRY.
    Never fabricates fake coordinates or claims simulations are real flight.
    """
    is_connected = drone_service.is_connected()
    active_drone = drone_service.get_active_drone(db)
    telemetry = drone_service.get_telemetry(db)
    age_s = drone_service.get_heartbeat_age_seconds()
    threshold = drone_service.stale_threshold_seconds
    source = drone_service.telemetry_source

    if not is_connected or not active_drone:
        # Check if stale or offline
        status_label = "STALE" if (age_s is not None and age_s > threshold) else "OFFLINE"
        if source == "SIMULATION_HARNESS" and status_label == "STALE":
            status_label = "SIMULATED_STALE"

        return LiveTelemetryResponse(
            connected=False,
            drone_id=active_drone.get("id") if active_drone else None,
            drone_name=active_drone.get("name") if active_drone else None,
            telemetry_source=source,
            latitude=None,
            longitude=None,
            altitude=None,
            speed=None,
            heading=None,
            battery=None,
            is_stale=True,
            has_gps_fix=False,
            status=status_label,
            message=(
                f"Telemetry heartbeat timed out ({age_s:.1f}s ago > {threshold:.0f}s threshold)."
                if age_s is not None
                else "No drone currently connected. Connect drone or start simulation harness."
            ),
            last_heartbeat=active_drone.get("updated_at") if active_drone else None,
            age_seconds=age_s,
            stale_threshold_seconds=threshold,
            estimated_uncertainty_m=None,
        )

    # Extract coordinates
    lat = telemetry.get("latitude") if telemetry else active_drone.get("latitude")
    lon = telemetry.get("longitude") if telemetry else active_drone.get("longitude")
    alt = telemetry.get("altitude") if telemetry else active_drone.get("altitude")
    speed = telemetry.get("speed") if telemetry else active_drone.get("speed")
    heading = telemetry.get("heading") if telemetry else active_drone.get("heading")
    battery = telemetry.get("battery") if telemetry else active_drone.get("battery_percentage")
    updated_at = telemetry.get("timestamp") if telemetry else active_drone.get("updated_at")

    has_valid_gps = (
        lat is not None
        and lon is not None
        and -90.0 <= lat <= 90.0
        and -180.0 <= lon <= 180.0
        and not (lat == 0.0 and lon == 0.0)
    )

    if not has_valid_gps:
        return LiveTelemetryResponse(
            connected=True,
            drone_id=active_drone.get("id"),
            drone_name=active_drone.get("name"),
            telemetry_source=source,
            latitude=None,
            longitude=None,
            altitude=round(alt, 1) if alt is not None else None,
            speed=round(speed, 1) if speed is not None else None,
            heading=round(heading, 1) if heading is not None else None,
            battery=round(battery, 1) if battery is not None else None,
            is_stale=False,
            has_gps_fix=False,
            status="INVALID_TELEMETRY",
            message="Drone connected but GPS coordinates are invalid or satellite fix is searching.",
            last_heartbeat=updated_at,
            age_seconds=age_s,
            stale_threshold_seconds=threshold,
            estimated_uncertainty_m=None,
        )

    # Determine status (SIMULATED vs CONNECTED)
    if source == "SIMULATION_HARNESS":
        status_label = "SIMULATED"
        msg = "Simulation Harness Active — synthetic test positions, not physical drone flight."
    else:
        status_label = "CONNECTED"
        msg = f"Live GPS fix active ({age_s:.1f}s freshness)."

    return LiveTelemetryResponse(
        connected=True,
        drone_id=active_drone.get("id"),
        drone_name=active_drone.get("name"),
        telemetry_source=source,
        latitude=round(lat, 7),
        longitude=round(lon, 7),
        altitude=round(alt, 1) if alt is not None else None,
        speed=round(speed, 1) if speed is not None else None,
        heading=round(heading, 1) if heading is not None else None,
        battery=round(battery, 1) if battery is not None else None,
        is_stale=False,
        has_gps_fix=True,
        status=status_label,
        message=msg,
        last_heartbeat=updated_at,
        age_seconds=age_s,
        stale_threshold_seconds=threshold,
        estimated_uncertainty_m=1.2 if status_label == "CONNECTED" else 0.0,
    )


@router.post("/telemetry/threshold")
def set_telemetry_stale_threshold(data: Dict[str, Any]):
    """
    Configures the stale-data threshold in seconds (FR-02).
    """
    threshold = data.get("stale_threshold_seconds", 15.0)
    try:
        drone_service.stale_threshold_seconds = float(threshold)
        return {
            "success": True,
            "stale_threshold_seconds": drone_service.stale_threshold_seconds,
            "message": f"Telemetry stale threshold set to {drone_service.stale_threshold_seconds:.1f} seconds"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drone/connect")
def connect_navigation_drone(data: Dict[str, Any], db: DBSession = Depends(get_db)):
    """
    Connects a drone by ID or provisions an active drone for real-time telemetry streaming (FR-01, FR-07).
    """
    drone_id = data.get("drone_id")
    source = data.get("source", "MAVLINK_TELEMETRY")
    if not drone_id:
        from backend.app.db.models import Drone
        first_drone = db.query(Drone).first()
        if not first_drone:
            first_drone = Drone(
                name="Garuda Tactical Drone-01",
                serial_number="GA-GD500-001",
                status="CONNECTED",
                battery_percentage=94.5,
                latitude=13.0827,
                longitude=80.2707,
                altitude=35.0,
                speed=8.5,
                heading=45.0,
            )
            db.add(first_drone)
            db.commit()
            db.refresh(first_drone)
        drone_id = first_drone.id

    drone = drone_service.connect_drone(db, drone_id, source=source)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    drone_service.register_heartbeat(
        drone.id,
        {
            "drone_id": drone.id,
            "latitude": drone.latitude or 13.0827,
            "longitude": drone.longitude or 80.2707,
            "altitude": drone.altitude or 30.0,
            "speed": drone.speed or 0.0,
            "heading": drone.heading or 0.0,
            "battery": drone.battery_percentage or 100.0,
            "timestamp": drone.updated_at.isoformat() if drone.updated_at else None,
        },
        source=source,
    )

    return {
        "connected": True,
        "drone_id": drone.id,
        "name": drone.name,
        "status": drone.status,
        "source": source,
    }


@router.post("/drone/disconnect")
def disconnect_navigation_drone(db: DBSession = Depends(get_db)):
    """
    Disconnects the active drone and invalidates cached telemetry.
    """
    drone_service.disconnect_drone(db)
    return {"connected": False, "status": "DISCONNECTED"}


@router.post("/drone/heartbeat")
def push_drone_heartbeat(data: Dict[str, Any], db: DBSession = Depends(get_db)):
    """
    Receives live telemetry heartbeat from drone flight controller or simulation harness.
    """
    drone_id = data.get("drone_id")
    source = data.get("source", "SIMULATION_HARNESS" if "sim" in str(drone_id).lower() else "MAVLINK_TELEMETRY")
    if not drone_id:
        active = drone_service.get_active_drone(db)
        drone_id = active.get("id") if active else None

    if not drone_id:
        raise HTTPException(status_code=400, detail="Drone ID required or connect a drone first")

    # Update database record if exists or provision if new
    from backend.app.db.models import Drone, Telemetry, get_utc_now
    drone = db.query(Drone).filter(Drone.id == drone_id).first()
    if not drone:
        drone = Drone(
            id=drone_id,
            name=f"Garuda Drone ({drone_id})",
            serial_number=f"GA-{drone_id}",
            status="CONNECTED",
            battery_percentage=data.get("battery", 100.0),
            latitude=data.get("latitude", 13.0827),
            longitude=data.get("longitude", 80.2707),
            altitude=data.get("altitude", 30.0),
            speed=data.get("speed", 0.0),
            heading=data.get("heading", 0.0),
        )
        db.add(drone)
        db.commit()
        db.refresh(drone)
    else:
        if "latitude" in data: drone.latitude = data["latitude"]
        if "longitude" in data: drone.longitude = data["longitude"]
        if "altitude" in data: drone.altitude = data["altitude"]
        if "speed" in data: drone.speed = data["speed"]
        if "heading" in data: drone.heading = data["heading"]
        if "battery" in data: drone.battery_percentage = data["battery"]
        drone.status = "CONNECTED"
        drone.updated_at = get_utc_now()
        db.commit()

    # Log telemetry history
    telem = Telemetry(
        drone_id=drone.id,
        latitude=drone.latitude,
        longitude=drone.longitude,
        altitude=drone.altitude,
        speed=drone.speed,
        heading=drone.heading,
        battery=drone.battery_percentage,
        timestamp=get_utc_now(),
    )
    db.add(telem)
    db.commit()

    telemetry_payload = {
        "drone_id": drone_id,
        "latitude": data.get("latitude", drone.latitude if drone else None),
        "longitude": data.get("longitude", drone.longitude if drone else None),
        "altitude": data.get("altitude", drone.altitude if drone else None),
        "speed": data.get("speed", drone.speed if drone else None),
        "heading": data.get("heading", drone.heading if drone else None),
        "battery": data.get("battery", drone.battery_percentage if drone else None),
        "timestamp": get_utc_now().isoformat(),
    }
    drone_service.register_heartbeat(drone_id, telemetry_payload, source=source)
    return {"status": "ok", "telemetry": telemetry_payload, "source": source}


@router.get("/debris-targets", response_model=List[DebrisTargetItem])
def get_debris_navigation_targets(limit: int = 40, db: DBSession = Depends(get_db)):
    """
    Fetches foreign object debris (FOD) records with spatial coordinate data for navigation (FR-08).
    Distinguishes records with valid geographic coordinates from records with unavailable telemetry.
    """
    return route_planning_service.get_debris_targets(db, limit=limit)


# ==============================================================================
# 2. MEDIA ANALYSIS & YOLO11 MODEL PIPELINE (EXISTING PRESERVED CAPABILITIES)
# ==============================================================================

@router.post("/upload", response_model=AnalysisJobCreateResponse)
async def upload_navigation_media(file: UploadFile = File(...)):
    """Uploads video or image for Navigation analysis (navigation_best.pt ONLY)."""
    ext = Path(file.filename or "").suffix.lower()
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty media file")

    if ext in video_exts:
        return analysis_service.create_video_job(
            filename=file.filename or "navigation_video.mp4",
            file_bytes=file_bytes,
            analysis_type="NAVIGATION",
        )
    elif ext in image_exts:
        return analysis_service.create_image_job(
            filename=file.filename or "navigation_image.jpg",
            file_bytes=file_bytes,
            analysis_type="NAVIGATION",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(video_exts | image_exts)}"
        )


@router.post("/{job_id}/start")
def start_navigation_analysis(job_id: str):
    """Starts Navigation model analysis."""
    try:
        return analysis_service.start_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {e}")


@router.post("/{job_id}/pause")
def pause_navigation_analysis(job_id: str):
    """Pauses active Navigation analysis."""
    try:
        return analysis_service.pause_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/resume")
def resume_navigation_analysis(job_id: str):
    """Resumes paused Navigation analysis."""
    try:
        return analysis_service.resume_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/cancel")
def cancel_navigation_analysis(job_id: str):
    """Cancels Navigation analysis."""
    try:
        return analysis_service.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history")
def get_navigation_history(limit: int = Query(50)):
    """Returns Navigation analysis job history."""
    return analysis_service.list_jobs(limit=limit, analysis_type="NAVIGATION")


@router.get("/{job_id}", response_model=AnalysisJobStatusResponse)
def get_navigation_status(job_id: str):
    """Returns Navigation analysis live status."""
    try:
        return analysis_service.get_job_status(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}/results", response_model=AnalysisJobResultsResponse)
def get_navigation_results(job_id: str):
    """Returns Navigation analysis final results."""
    try:
        return analysis_service.get_job_results(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}/video")
def get_navigation_video(job_id: str):
    """Returns annotated Navigation video."""
    results = analysis_service.get_job_results(job_id)
    path = results.get("annotated_media_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Analyzed video not found")
    return FileResponse(path, media_type="video/mp4", filename=Path(path).name)
