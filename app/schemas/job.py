from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    """API response model for a background job."""
    id: str
    domain: str
    type: str
    status: str                    # pending | running | succeeded | failed | cancelled
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    progress_percent: float
    progress_message: Optional[str]
    attempts: int
    cancel_requested: bool
    user_id: Optional[str]
    resource_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
