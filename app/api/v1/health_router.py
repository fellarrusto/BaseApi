from fastapi import APIRouter, status

from app.schemas.health import HealthCheckResponse
from app.services.health_service import health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/check",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK
)
async def health_check() -> HealthCheckResponse:
    """API and database health check."""
    return await health_service.check()
