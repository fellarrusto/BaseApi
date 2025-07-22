from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.base import PyObjectId

class AuditLogInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str  # es: "health_check", "create_user", ecc.
    endpoint: str  # es: "/health/check"
    method: str  # es: "GET", "POST"
    status: str  # es: "success", "error"
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None  # dati aggiuntivi