from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class MissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    drone_id: Optional[str] = None
    status: str = "PLANNED"

class MissionCreate(MissionBase):
    pass

class MissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    drone_id: Optional[str] = None

class MissionResponse(MissionBase):
    id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
