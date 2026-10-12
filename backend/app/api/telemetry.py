from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.drone import TelemetryResponse
from backend.app.services.telemetry_service import telemetry_service

router = APIRouter()

@router.get("/drones/{id}", response_model=TelemetryResponse)
def get_telemetry(id: str, db: Session = Depends(get_db)):
    data = telemetry_service.get_latest_telemetry(db, id)
    if not data:
        raise HTTPException(status_code=404, detail="Drone telemetry not found")
    return data


@router.post("/drones/{id}", response_model=TelemetryResponse)
def post_telemetry(
    id: str,
    latitude: float,
    longitude: float,
    altitude: float,
    speed: float,
    heading: float,
    battery: float,
    db: Session = Depends(get_db)
):
    rec = telemetry_service.record_telemetry(db, id, latitude, longitude, altitude, speed, heading, battery)
    return {
        "id": rec.id,
        "drone_id": rec.drone_id,
        "latitude": rec.latitude,
        "longitude": rec.longitude,
        "altitude": rec.altitude,
        "speed": rec.speed,
        "heading": rec.heading,
        "battery": rec.battery,
        "timestamp": rec.timestamp
    }
