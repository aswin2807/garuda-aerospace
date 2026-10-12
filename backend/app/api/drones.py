from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models import Drone
from backend.app.schemas.drone import DroneCreate, DroneUpdate, DroneResponse, TelemetryResponse
from backend.app.services.telemetry_service import telemetry_service

router = APIRouter()

@router.get("", response_model=List[DroneResponse])
def get_drones(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    drones = db.query(Drone).offset(skip).limit(limit).all()
    return drones


@router.post("", response_model=DroneResponse)
def create_drone(drone_in: DroneCreate, db: Session = Depends(get_db)):
    existing = db.query(Drone).filter(Drone.serial_number == drone_in.serial_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Drone with this serial number already exists")
    drone = Drone(**drone_in.model_dump())
    db.add(drone)
    db.commit()
    db.refresh(drone)
    return drone

@router.get("/{id}", response_model=DroneResponse)
def get_drone(id: str, db: Session = Depends(get_db)):
    drone = db.query(Drone).filter(Drone.id == id).first()
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    return drone

@router.put("/{id}", response_model=DroneResponse)
def update_drone(id: str, drone_in: DroneUpdate, db: Session = Depends(get_db)):
    drone = db.query(Drone).filter(Drone.id == id).first()
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    for field, value in drone_in.model_dump(exclude_unset=True).items():
        setattr(drone, field, value)
    db.commit()
    db.refresh(drone)
    return drone

@router.delete("/{id}")
def delete_drone(id: str, db: Session = Depends(get_db)):
    drone = db.query(Drone).filter(Drone.id == id).first()
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    db.delete(drone)
    db.commit()
    return {"success": True, "message": "Drone deleted"}

@router.get("/{id}/telemetry", response_model=TelemetryResponse)
def get_drone_telemetry(id: str, db: Session = Depends(get_db)):
    data = telemetry_service.get_latest_telemetry(db, id)
    if not data:
        raise HTTPException(status_code=404, detail="Drone telemetry not found")
    return data

