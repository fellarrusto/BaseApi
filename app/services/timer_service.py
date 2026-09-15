from app.schemas.auth import AuthUser
from app.schemas.job import JobResponse
from app.services.job_service import job_service


class TimerService:
    """Business logic for demo timers: the minimal example of a background job."""

    async def start(self, seconds: int, user: AuthUser) -> JobResponse:
        """Start a timer job that counts `seconds` in the worker."""
        return await job_service.enqueue(
            domain="demo",
            job_type="timer",
            payload={"seconds": seconds},
            user_id=user.id
        )


timer_service = TimerService()
