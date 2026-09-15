from typing import Any, Dict, Optional

from app.core.exceptions import JobCancelledError
from app.services.job_service import job_service


class JobContext:
    """What a handler can do besides its work: report progress, checkpoint, stop on cancel."""

    def __init__(self, job_id: str, worker_id: str, attempt: int, state: Dict[str, Any]):
        self.job_id = job_id
        self.attempt = attempt          # 1 on the first run, 2 on the first retry, ...
        self.state = dict(state)        # last checkpoint: resume from here after a crash
        self._worker_id = worker_id

    async def progress(self, percent: float, message: Optional[str] = None) -> None:
        await job_service.update_progress(self.job_id, self._worker_id, percent, message)

    async def save_state(self, state: Dict[str, Any]) -> None:
        self.state = dict(state)
        await job_service.save_state(self.job_id, self._worker_id, self.state)

    async def check_cancelled(self) -> None:
        """Stop here if cancellation was requested: call it between steps."""
        if await job_service.is_cancel_requested(self.job_id):
            raise JobCancelledError(self.job_id)
