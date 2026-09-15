from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.core.exceptions import InvalidInputError, NotFoundError
from app.models.base import utc_now
from app.models.job import JobInDB, JobStatus
from app.repositories.job_repository import job_repository
from app.schemas.auth import AuthUser
from app.schemas.job import JobResponse

ADMIN_ROLE = "admin"

# Retry backoff: 5s, 10s, 20s, ... capped
RETRY_BASE_SECONDS = 5
RETRY_MAX_SECONDS = 300


class JobService:
    """Business logic for background jobs, used by the API and by the worker."""

    # ----- API side -----

    async def enqueue(
        self,
        domain: str,
        job_type: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> JobResponse:
        """Create a pending job: a worker will pick it up."""
        job = await job_repository.create(JobInDB(
            domain=domain,
            type=job_type,
            payload=payload,
            user_id=user_id,
            resource_id=resource_id
        ))
        return self._to_response(job)

    async def get_for_user(self, job_id: str, user: AuthUser) -> JobResponse:
        """Fetch a job. Raises NotFoundError if missing or owned by someone else."""
        return self._to_response(await self._get_visible(job_id, user))

    async def list_for_user(
        self,
        user: AuthUser,
        domain: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[JobResponse]:
        """The user's jobs (every job for admins), newest first."""
        owner = None if ADMIN_ROLE in user.roles else user.id
        jobs = await job_repository.find_visible(owner, domain, job_type, status, limit=limit, skip=skip)
        return [self._to_response(job) for job in jobs]

    async def cancel(self, job_id: str, user: AuthUser) -> JobResponse:
        """
        Cancel a pending job immediately, or ask a running job to stop.

        Raises:
            NotFoundError: If the job is missing or owned by someone else
            InvalidInputError: If the job already finished
        """
        job = await self._get_visible(job_id, user)
        cancelled = (
            await job_repository.cancel_if_pending(job_id, utc_now())
            or await job_repository.request_cancel_if_running(job_id)
        )
        if not cancelled:
            raise InvalidInputError(f"Job is already {job.status}")
        return await self.get_for_user(job_id, user)

    # ----- Worker side -----

    async def claim_next(self, worker_id: str, lock_seconds: float) -> Optional[JobInDB]:
        now = utc_now()
        return await job_repository.claim_next(worker_id, now, now + timedelta(seconds=lock_seconds))

    async def extend_lock(self, job_id: str, worker_id: str, lock_seconds: float) -> bool:
        return await job_repository.extend_lock(job_id, worker_id, utc_now() + timedelta(seconds=lock_seconds))

    async def update_progress(self, job_id: str, worker_id: str, percent: float, message: Optional[str]) -> None:
        await job_repository.set_progress(job_id, worker_id, round(min(max(percent, 0.0), 100.0), 2), message)

    async def save_state(self, job_id: str, worker_id: str, state: Dict[str, Any]) -> None:
        await job_repository.save_state(job_id, worker_id, state)

    async def is_cancel_requested(self, job_id: str) -> bool:
        job = await job_repository.get_by_id(job_id)
        return bool(job and job.cancel_requested)

    async def succeed(self, job_id: str, worker_id: str, result: Dict[str, Any]) -> None:
        await job_repository.finish(job_id, worker_id, JobStatus.SUCCEEDED, utc_now(), result=result)

    async def cancel_running(self, job_id: str, worker_id: str) -> None:
        await job_repository.finish(job_id, worker_id, JobStatus.CANCELLED, utc_now())

    async def fail(self, job_id: str, worker_id: str, error: str, attempts: int, max_attempts: int) -> None:
        """Retry with exponential backoff while attempts remain, then mark the job failed."""
        if attempts < max_attempts:
            delay = min(RETRY_MAX_SECONDS, RETRY_BASE_SECONDS * 2 ** (attempts - 1))
            await job_repository.reschedule(job_id, worker_id, error, utc_now() + timedelta(seconds=delay))
        else:
            await job_repository.finish(job_id, worker_id, JobStatus.FAILED, utc_now(), error=error)

    async def release_expired_locks(self) -> int:
        return await job_repository.release_expired_locks(utc_now())

    # ----- Helpers -----

    async def _get_visible(self, job_id: str, user: AuthUser) -> JobInDB:
        job = await job_repository.get_by_id(job_id)
        if job is None or (ADMIN_ROLE not in user.roles and job.user_id != user.id):
            raise NotFoundError("Job not found")
        return job

    def _to_response(self, job: JobInDB) -> JobResponse:
        return JobResponse(
            id=str(job.id),
            **job.model_dump(exclude={"id", "state", "worker_id", "run_after", "locked_until"})
        )


job_service = JobService()
