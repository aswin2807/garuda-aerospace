from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DroneBase(BaseModel):
    name: str
    serial_number: str
    status: str = "IDLE"
    battery_percentage: float = 100.0
    latitude: float = 12.9012
    longitude: float = 80.2273
    altitude: float = 120.0
    speed: float = 32.0
    heading: float = 184.0

class DroneCreate(DroneBase):
    pass

class DroneUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    battery_percentage: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None

class DroneResponse(DroneBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TelemetryResponse(BaseModel):
    id: Optional[int] = None
    drone_id: str
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float
    battery: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
