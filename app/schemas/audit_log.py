from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """API response model for an audit log entry."""
    id: str
    timestamp: datetime
    action: str
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
