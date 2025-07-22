from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.base import PyObjectId

class HealthCheckInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime: Optional[float] = None

class HealthCheckResponse(BaseModel):
    """Modello di response per l'health check"""
    status: str
    timestamp: datetime
    version: str
    uptime: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }