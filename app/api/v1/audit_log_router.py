from datetime import date
from typing import List

from fastapi import APIRouter, Query, status

from app.core.decorator import audit_log, handle_errors
from app.schemas.audit_log import AuditLogResponse
from app.services.audit_log_service import audit_log_service

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get(
    "",
    response_model=List[AuditLogResponse],
    status_code=status.HTTP_200_OK
)
@handle_errors
@audit_log(metadata={"service": "audit-logs"})
async def get_audit_logs(
    start_date: date = Query(..., description="Start date, inclusive (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date, inclusive (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    skip: int = Query(0, ge=0, description="Results to skip")
) -> List[AuditLogResponse]:
    """Fetch audit logs in a date range, newest first."""
    return await audit_log_service.get_by_date_range(start_date, end_date, limit=limit, skip=skip)
