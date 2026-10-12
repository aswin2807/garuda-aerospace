import math
import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.db.models import Drone, Telemetry, Alert

from backend.app.services.drone_service import drone_service

class TelemetryService:
    @staticmethod
    def record_telemetry(db: Session, drone_id: str, lat: float, lng: float, alt: float, speed: float, heading: float, battery: float):
        record = Telemetry(
            drone_id=drone_id,
            latitude=lat,
            longitude=lng,
            altitude=alt,
            speed=speed,
            heading=heading,
            battery=battery,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(record)
        
        # Update current drone record
        drone = db.query(Drone).filter(Drone.id == drone_id).first()
        if drone:
            drone.latitude = lat
            drone.longitude = lng
            drone.altitude = alt
            drone.speed = speed
            drone.heading = heading
            drone.battery_percentage = battery
            drone.status = "ACTIVE"
            
            # Check for low battery alert
            if battery < 20.0:
                alert = Alert(
                    drone_id=drone_id,
                    type="LOW_BATTERY",
                    severity="CRITICAL",
                    message=f"Drone battery critical: {battery:.1f}% remaining."
                )
                db.add(alert)
                
        db.commit()

        # Register live heartbeat in DroneService
        drone_service.register_heartbeat(
            drone_id,
            {
                "drone_id": drone_id,
                "latitude": lat,
                "longitude": lng,
                "altitude": alt,
                "speed": speed,
                "heading": heading,
                "battery": battery,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None
            }
        )
        return record

    @staticmethod
    def get_latest_telemetry(db: Session, drone_id: str) -> dict:
        drone = db.query(Drone).filter(Drone.id == drone_id).first()
        if not drone:
            return None
        return {
            "id": 1,
            "drone_id": drone.id,
            "latitude": drone.latitude,
            "longitude": drone.longitude,
            "altitude": drone.altitude,
            "speed": drone.speed,
            "heading": drone.heading,
            "battery": drone.battery_percentage,
            "timestamp": drone.updated_at or datetime.now(timezone.utc)
        }

telemetry_service = TelemetryService()

