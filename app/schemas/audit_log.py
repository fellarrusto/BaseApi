from datetime import datetime
from typing import Any, Dict, Optional

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
    user_id: Optional[str]
    metadata: Dict[str, Any]
