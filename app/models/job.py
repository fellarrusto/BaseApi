from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import PyObjectId, utc_now


class JobStatus:
    """Job lifecycle: pending → running → succeeded | failed | cancelled."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobInDB(BaseModel):
    """Persistence model for the jobs collection (also the worker queue)."""
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    domain: str                                   # e.g. "demo", "pdf"
    type: str                                     # e.g. "timer", "ingestion"
    status: str = JobStatus.PENDING
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress_percent: float = 0
    progress_message: Optional[str] = None
    state: Dict[str, Any] = Field(default_factory=dict)  # checkpoint saved by the handler
    attempts: int = 0
    cancel_requested: bool = False
    user_id: Optional[str] = None
    resource_id: Optional[str] = None             # entity the job works on, if any
    worker_id: Optional[str] = None
    run_after: datetime = Field(default_factory=utc_now)
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
