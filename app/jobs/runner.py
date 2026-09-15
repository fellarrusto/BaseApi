import asyncio
import logging
import time
from typing import Awaitable, Set

from app.core.exceptions import JobCancelledError
from app.jobs.context import JobContext
from app.jobs.registry import JobDefinition, get_job_definition
from app.models.job import JobInDB
from app.services.job_service import job_service

logger = logging.getLogger(__name__)


class JobRunner:
    """
    Worker loop: claims due jobs from the database and runs their handlers.

    Up to `concurrency` jobs run at once. A running job renews its lock;
    jobs whose lock expired (crashed worker) go back to pending and resume
    from their last checkpoint.
    """

    def __init__(self, worker_id: str, concurrency: int, poll_seconds: float, lock_seconds: float):
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.poll_seconds = poll_seconds
        self.lock_seconds = lock_seconds

    async def run(self, stop: asyncio.Event) -> None:
        """Process jobs until `stop` is set, then wait for the running ones to finish."""
        running: Set[asyncio.Task] = set()
        next_recovery = 0.0

        while not stop.is_set():
            if time.monotonic() >= next_recovery:
                await self._safely(job_service.release_expired_locks(), "release expired locks")
                next_recovery = time.monotonic() + self.lock_seconds

            if len(running) >= self.concurrency:
                await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
                continue

            job = await self._safely(job_service.claim_next(self.worker_id, self.lock_seconds), "claim a job")
            if job is None:
                await self._sleep(stop)
                continue

            task = asyncio.create_task(self._execute(job))
            running.add(task)
            task.add_done_callback(running.discard)

        if running:
            logger.info("Waiting for %d running job(s) to finish", len(running))
            await asyncio.wait(running)

    async def _execute(self, job: JobInDB) -> None:
        job_id = str(job.id)
        name = f"{job.domain}.{job.type}"
        definition = get_job_definition(job.domain, job.type)

        if definition is None:
            await self._safely(
                job_service.fail(job_id, self.worker_id, f"No handler registered for {name}", 1, 1), "fail job"
            )
            return
        if job.attempts > definition.max_attempts:
            await self._fail(job, definition, "Interrupted too many times (worker crash or shutdown)")
            return

        logger.info("Job %s (%s) started, attempt %d", job_id, name, job.attempts)
        ctx = JobContext(job_id, self.worker_id, job.attempts, job.state)
        heartbeat = asyncio.create_task(self._keep_lock(job_id))
        try:
            result = await asyncio.wait_for(definition.handler(job.payload, ctx), definition.timeout_seconds)
        except JobCancelledError:
            logger.info("Job %s (%s) cancelled", job_id, name)
            await self._safely(job_service.cancel_running(job_id, self.worker_id), "cancel job")
        except asyncio.TimeoutError:
            logger.warning("Job %s (%s) timed out", job_id, name)
            await self._fail(job, definition, f"Timed out after {definition.timeout_seconds}s")
        except Exception as e:
            logger.exception("Job %s (%s) failed", job_id, name)
            await self._fail(job, definition, f"{type(e).__name__}: {e}")
        else:
            logger.info("Job %s (%s) succeeded", job_id, name)
            await self._safely(job_service.succeed(job_id, self.worker_id, result or {}), "complete job")
        finally:
            heartbeat.cancel()

    async def _fail(self, job: JobInDB, definition: JobDefinition, error: str) -> None:
        await self._safely(
            job_service.fail(str(job.id), self.worker_id, error, job.attempts, definition.max_attempts),
            "fail job"
        )

    async def _keep_lock(self, job_id: str) -> None:
        while True:
            await asyncio.sleep(self.lock_seconds / 3)
            await self._safely(job_service.extend_lock(job_id, self.worker_id, self.lock_seconds), "extend lock")

    async def _sleep(self, stop: asyncio.Event) -> None:
        try:
            await asyncio.wait_for(stop.wait(), self.poll_seconds)
        except asyncio.TimeoutError:
            pass

    @staticmethod
    async def _safely(operation: Awaitable, action: str):
        # A database hiccup must not kill the worker loop
        try:
            return await operation
        except Exception:
            logger.exception("Worker could not %s", action)
            return None
