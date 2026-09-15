import time

from app.core.config import settings
from app.repositories.health_repository import health_repository
from app.schemas.health import HealthCheckResponse

_STARTED_AT = time.monotonic()


class HealthService:
    """Business logic for the health check."""

    async def check(self) -> HealthCheckResponse:
        """Report API uptime and database reachability."""
        database_up = await health_repository.ping()
        return HealthCheckResponse(
            status="healthy" if database_up else "degraded",
            version=settings.APP_VERSION,
            uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
            database="up" if database_up else "down"
        )


health_service = HealthService()
