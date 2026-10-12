from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models import Mission
from backend.app.schemas.mission import MissionCreate, MissionUpdate, MissionResponse

router = APIRouter()

@router.get("", response_model=List[MissionResponse])
def get_missions(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    missions = db.query(Mission).offset(skip).limit(limit).all()
    return missions


@router.post("", response_model=MissionResponse)
def create_mission(mission_in: MissionCreate, db: Session = Depends(get_db)):
    mission = Mission(**mission_in.model_dump())
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission

@router.get("/{id}", response_model=MissionResponse)
def get_mission(id: str, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission

@router.post("/{id}/start", response_model=MissionResponse)
def start_mission(id: str, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    mission.status = "ACTIVE"
    if not mission.start_time:
        mission.start_time = datetime.now(timezone.utc)
    db.commit()
    db.refresh(mission)
    return mission

@router.post("/{id}/pause", response_model=MissionResponse)
def pause_mission(id: str, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    mission.status = "PAUSED"
    db.commit()
    db.refresh(mission)
    return mission

@router.post("/{id}/stop", response_model=MissionResponse)
def stop_mission(id: str, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    mission.status = "COMPLETED"
    mission.end_time = datetime.now(timezone.utc)
    db.commit()
    db.refresh(mission)
    return mission

@router.get("/{id}/report")
def get_mission_report(id: str, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {
        "mission_id": mission.id,
        "name": mission.name,
        "description": mission.description,
        "status": mission.status,
        "drone_id": mission.drone_id,
        "start_time": mission.start_time.isoformat() if mission.start_time else None,
        "end_time": mission.end_time.isoformat() if mission.end_time else None,
        "created_at": mission.created_at.isoformat() if mission.created_at else None,
    }

