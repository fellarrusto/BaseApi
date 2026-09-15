from fastapi import APIRouter, status

from app.decorators import audit_log, handle_errors
from app.schemas.error import ErrorResponse
from app.schemas.health import LivenessResponse, ReadinessResponse
from app.services.health_service import health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(enabled=False)  # probes run every few seconds: keep them out of the audit log
async def liveness() -> LivenessResponse:
    """Liveness probe: the process is running (no dependency checks)."""
    return await health_service.live()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={503: {"model": ErrorResponse}}
)
@handle_errors
@audit_log(enabled=False)
async def readiness() -> ReadinessResponse:
    """Readiness probe: 503 when the database is unreachable."""
    return await health_service.ready()
