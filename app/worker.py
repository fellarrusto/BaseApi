import asyncio
import logging
import signal
import socket
import uuid

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.database import db_connect, db_disconnect
from app.integrations.clients import integrations_connect, integrations_disconnect
from app.jobs.runner import JobRunner  # importing app.jobs registers every @job handler

logger = logging.getLogger("app.worker")


async def main() -> None:
    """Worker entry point: `python -m app.worker`."""
    setup_logging(settings.LOG_LEVEL)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass  # Windows: Ctrl+C stops the process directly

    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    await db_connect()
    await integrations_connect()
    logger.info("Worker %s started (concurrency %d)", worker_id, settings.WORKER_CONCURRENCY)
    try:
        runner = JobRunner(
            worker_id,
            concurrency=settings.WORKER_CONCURRENCY,
            poll_seconds=settings.WORKER_POLL_SECONDS,
            lock_seconds=settings.WORKER_LOCK_SECONDS
        )
        await runner.run(stop)
    finally:
        await integrations_disconnect()
        await db_disconnect()
        logger.info("Worker %s stopped", worker_id)


if __name__ == "__main__":
    asyncio.run(main())
