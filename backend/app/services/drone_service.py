import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models import Drone, Telemetry
from backend.app.core.logging import logger

class DroneService:
    """
    Manages genuine drone hardware connection states, verified heartbeats,
    and live telemetry caching. Strictly prevents fabricating fake drone data.
    """
    def __init__(self):
        self._connected: bool = False
        self._active_drone_id: Optional[str] = None
        self._last_heartbeat: Optional[float] = None
        self._telemetry_cache: Optional[Dict[str, Any]] = None

    def is_connected(self) -> bool:
        if not self._connected or not self._last_heartbeat:
            return False
        # Heartbeat timeout: 15 seconds without updates = disconnected
        if time.time() - self._last_heartbeat > 15.0:
            self._connected = False
            return False
        return True

    def register_heartbeat(self, drone_id: str, telemetry: Optional[Dict[str, Any]] = None):
        self._connected = True
        self._active_drone_id = drone_id
        self._last_heartbeat = time.time()
        if telemetry:
            self._telemetry_cache = telemetry

    def connect_drone(self, db: Session, drone_id: str) -> Optional[Drone]:
        drone = db.query(Drone).filter(Drone.id == drone_id).first()
        if drone:
            drone.status = "CONNECTED"
            db.commit()
            db.refresh(drone)
            self._connected = True
            self._active_drone_id = drone_id
            self._last_heartbeat = time.time()
            logger.info(f"[DRONE] Connected drone {drone_id} ({drone.name})")
            return drone
        return None

    def disconnect_drone(self, db: Optional[Session] = None):
        self._connected = False
        if self._active_drone_id and db:
            try:
                drone = db.query(Drone).filter(Drone.id == self._active_drone_id).first()
                if drone:
                    drone.status = "DISCONNECTED"
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to update drone status on disconnect: {e}")
        self._active_drone_id = None
        self._last_heartbeat = None
        self._telemetry_cache = None
        logger.info("[DRONE] Drone disconnected.")

    def get_active_drone(self, db: Session) -> Optional[Dict[str, Any]]:
        if not self.is_connected() or not self._active_drone_id:
            return None
        drone = db.query(Drone).filter(Drone.id == self._active_drone_id).first()
        if not drone:
            return None
        return {
            "id": drone.id,
            "name": drone.name,
            "serial_number": drone.serial_number,
            "status": drone.status,
            "battery_percentage": drone.battery_percentage,
            "latitude": drone.latitude,
            "longitude": drone.longitude,
            "altitude": drone.altitude,
            "speed": drone.speed,
            "heading": drone.heading,
            "updated_at": drone.updated_at.isoformat() if drone.updated_at else None,
        }

    def get_telemetry(self, db: Session) -> Optional[Dict[str, Any]]:
        if not self.is_connected():
            return None
        if self._telemetry_cache:
            return self._telemetry_cache
        if self._active_drone_id:
            latest = (
                db.query(Telemetry)
                .filter(Telemetry.drone_id == self._active_drone_id)
                .order_by(Telemetry.id.desc())
                .first()
            )
            if latest:
                return {
                    "drone_id": latest.drone_id,
                    "latitude": latest.latitude,
                    "longitude": latest.longitude,
                    "altitude": latest.altitude,
                    "speed": latest.speed,
                    "heading": latest.heading,
                    "battery": latest.battery,
                    "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
                }
        return None

drone_service = DroneService()
