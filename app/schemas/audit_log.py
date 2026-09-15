from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """API response model for an audit log entry."""
    id: str
    timestamp: datetime
    action: str
    endpoint: str
    method: str
    status: str
    duration_ms: float
    metadata: Dict[str, Any]
