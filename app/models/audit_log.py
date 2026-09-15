from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import PyObjectId, utc_now


class AuditLogInDB(BaseModel):
    """Persistence model for the audit_logs collection."""
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=utc_now)
    action: str        # endpoint function name, e.g. "get_audit_logs"
    endpoint: str      # request path, e.g. "/api/v1/audit-logs"
    method: str        # e.g. "GET"
    status: str        # "success" | "error"
    duration_ms: float
    user_id: Optional[str] = None  # set when the endpoint uses @require_auth
    metadata: Dict[str, Any] = Field(default_factory=dict)  # from @audit_log, plus "error" on failure
