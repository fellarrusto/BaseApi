from fastapi import APIRouter, Query, status

from app.decorators import audit_log, handle_errors, require_auth
from app.schemas.auth import AuthUser
from app.schemas.job import JobResponse
from app.services.timer_service import timer_service

router = APIRouter(prefix="/timers", tags=["timers"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
@handle_errors
@audit_log(metadata={"service": "timers"})
@require_auth()
async def start_timer(
    current_user: AuthUser,
    seconds: int = Query(10, ge=1, le=3600, description="Timer duration in seconds")
) -> JobResponse:
    """Start a demo timer job; follow it with GET /jobs/{id}."""
    return await timer_service.start(seconds, current_user)
