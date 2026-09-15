from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import PyObjectId, utc_now


class AuditLogInDB(BaseModel):
    """Persistence model for the audit_logs collection."""
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=utc_now)
    action: str        # route function name, e.g. "get_audit_logs"
    endpoint: str      # request path, e.g. "/api/v1/audit-logs"
    method: str        # e.g. "GET"
    status_code: int
    duration_ms: float
