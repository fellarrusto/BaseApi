import time

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.repositories.health_repository import health_repository
from app.schemas.health import LivenessResponse, ReadinessResponse

_STARTED_AT = time.monotonic()


class HealthService:
    """Business logic for liveness and readiness probes."""

    async def live(self) -> LivenessResponse:
        """The process is up: no dependency is checked."""
        return LivenessResponse(
            status="alive",
            version=settings.APP_VERSION,
            uptime_seconds=round(time.monotonic() - _STARTED_AT, 3)
        )

    async def ready(self) -> ReadinessResponse:
        """
        The API can serve requests.

        Raises:
            ServiceUnavailableError: If the database is unreachable
        """
        if not await health_repository.ping():
            raise ServiceUnavailableError("Database unreachable")
        return ReadinessResponse(status="ready", database="up")


health_service = HealthService()
