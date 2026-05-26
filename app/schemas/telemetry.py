from datetime import datetime
from pydantic import BaseModel


class TelemetryEventInput(BaseModel):
    match_id: str
    timestamp: datetime
    event_type: str
    player_id: str
    x: float
    y: float
