from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.db.base_storage import Index
from app.models.job import JobInDB, JobStatus
from app.repositories.entity_repository import EntityRepository


class JobRepository(EntityRepository[JobInDB]):
    """Data access for background jobs. Worker updates are guarded by worker_id."""

    collection = "jobs"
    model = JobInDB
    indexes = [
        Index([("status", 1), ("run_after", 1)]),       # worker queue
        Index([("user_id", 1), ("created_at", -1)]),     # job listing
        # Finished jobs are deleted after the retention (0 days = keep forever)
        Index([("finished_at", 1)], expire_after_seconds=settings.JOB_RETENTION_DAYS * 86400 or None),
    ]

    async def find_visible(
        self,
        user_id: Optional[str],
        domain: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[JobInDB]:
        """Jobs of a user (every user if None), optionally filtered, newest first."""
        filters: Dict[str, Any] = {}
        if user_id is not None:
            filters["user_id"] = user_id
        if domain:
            filters["domain"] = domain
        if job_type:
            filters["type"] = job_type
        if status:
            filters["status"] = status
        return await self._find_many(filters, limit=limit, skip=skip, sort=[("created_at", -1)])

    async def claim_next(self, worker_id: str, now: datetime, locked_until: datetime) -> Optional[JobInDB]:
        """Atomically take the oldest due pending job and mark it running for this worker."""
        job = await self._claim_one(
            {"status": JobStatus.PENDING, "run_after": {"$lte": now}},
            # cancel_requested is kept: a cancellation must survive retries and crashes
            {"status": JobStatus.RUNNING, "worker_id": worker_id, "locked_until": locked_until, "started_at": now},
            sort=[("run_after", 1)]
        )
        if job is None:
            return None
        job.attempts += 1
        await self._update(str(job.id), {"attempts": job.attempts}, where=self._owned_by(worker_id))
        return job

    async def extend_lock(self, job_id: str, worker_id: str, locked_until: datetime) -> bool:
        """Returns False if the job is no longer running for this worker."""
        return await self._update(job_id, {"locked_until": locked_until}, where=self._owned_by(worker_id))

    async def set_progress(self, job_id: str, worker_id: str, percent: float, message: Optional[str]) -> bool:
        return await self._update(
            job_id,
            {"progress_percent": percent, "progress_message": message},
            where=self._owned_by(worker_id)
        )

    async def save_state(self, job_id: str, worker_id: str, state: Dict[str, Any]) -> bool:
        return await self._update(job_id, {"state": state}, where=self._owned_by(worker_id))

    async def finish(
        self,
        job_id: str,
        worker_id: str,
        status: str,
        now: datetime,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """Move a running job to a final status."""
        fields: Dict[str, Any] = {"status": status, "finished_at": now, "locked_until": None, "error": error}
        if status == JobStatus.SUCCEEDED:
            fields.update(result=result, progress_percent=100)
        return await self._update(job_id, fields, where=self._owned_by(worker_id))

    async def reschedule(self, job_id: str, worker_id: str, error: str, run_after: datetime) -> bool:
        """Put a running job back in the queue for another attempt."""
        return await self._update(
            job_id,
            {
                "status": JobStatus.PENDING,
                "worker_id": None,
                "locked_until": None,
                "run_after": run_after,
                "error": error,
            },
            where=self._owned_by(worker_id)
        )

    async def cancel_if_pending(self, job_id: str, now: datetime) -> bool:
        return await self._update(
            job_id,
            {"status": JobStatus.CANCELLED, "finished_at": now},
            where={"status": JobStatus.PENDING}
        )

    async def request_cancel_if_running(self, job_id: str) -> bool:
        return await self._update(job_id, {"cancel_requested": True}, where={"status": JobStatus.RUNNING})

    async def release_expired_locks(self, now: datetime) -> int:
        """
        Running jobs whose worker stopped renewing the lock: cancelled if a
        cancellation was requested, otherwise back to pending.
        """
        expired = {"status": JobStatus.RUNNING, "locked_until": {"$lt": now}}
        cancelled = await self._update_many(
            {**expired, "cancel_requested": True},
            {"status": JobStatus.CANCELLED, "finished_at": now, "worker_id": None, "locked_until": None}
        )
        requeued = await self._update_many(
            expired,
            {"status": JobStatus.PENDING, "worker_id": None, "locked_until": None}
        )
        return cancelled + requeued

    @staticmethod
    def _owned_by(worker_id: str) -> Dict[str, Any]:
        return {"status": JobStatus.RUNNING, "worker_id": worker_id}


job_repository = JobRepository()
