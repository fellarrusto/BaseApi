from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TaskTriggerResponse(BaseModel):
    """Response per trigger di task"""
    status: str
    message: str
    total_files: Optional[int] = None
    processed: Optional[int] = None
    errors: Optional[int] = None
    error_details: Optional[List[str]] = None

class TaskStatusResponse(BaseModel):
    """Response per status di task"""
    is_running: bool
    scheduler_active: bool
    last_run: Optional[str] = None

class SchedulerControlResponse(BaseModel):
    """Response per controllo scheduler"""
    status: str
    interval_minutes: Optional[int] = None