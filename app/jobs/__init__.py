# Import every job module here so its @job handlers are registered in the worker
from app.jobs import timer_job  # noqa: F401
