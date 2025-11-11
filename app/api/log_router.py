from app.core.decorator import handle_errors, audit_log
from fastapi import APIRouter, status, Query
from datetime import datetime
from typing import List
from app.models.log import AuditLogInDB
from app.services.log_service import log_service

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("/audit", response_model=List[AuditLogInDB], status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="GET", metadata={"service": "logs"})
async def get_audit_logs(
    start_date: str = Query(...),
    end_date: str = Query(...)
) -> List[AuditLogInDB]:
    start_dt = datetime.strptime(start_date, "%d-%m-%Y")
    end_dt = datetime.strptime(end_date, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
    return await log_service.get_logs_by_date_range(start_dt, end_dt)