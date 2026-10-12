from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class AlertItem(BaseModel):
    event_type: str = Field(..., description="RUNWAY_LIGHT_FAULT or FOD_DETECTED")
    severity: str = Field("HIGH", description="CRITICAL, HIGH, MEDIUM, INFO")
    class_name: str = Field(..., description="LIGHT OFF or FOD")
    confidence: float
    status: str = Field("POTENTIAL", description="POTENTIAL or CONFIRMED")
    consecutive_frames: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    bbox: Optional[Dict[str, float]] = None
    message: Optional[str] = None

class AlertSummary(BaseModel):
    fod_count: int = 0
    light_on_count: int = 0
    light_off_count: int = 0
    active_alerts: List[AlertItem] = []
