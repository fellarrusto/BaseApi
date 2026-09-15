from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

# handler(payload, ctx) -> result dict (or None)
JobHandler = Callable[[Dict[str, Any], Any], Awaitable[Optional[Dict[str, Any]]]]


@dataclass(frozen=True)
class JobDefinition:
    domain: str
    type: str
    handler: JobHandler
    max_attempts: int
    timeout_seconds: float


_definitions: Dict[Tuple[str, str], JobDefinition] = {}


def job(
    domain: str,
    type: str,
    max_attempts: int = 3,
    timeout_seconds: float = 3600
) -> Callable[[JobHandler], JobHandler]:
    """
    Register an async handler for jobs of (domain, type).

    The handler receives the job payload and a JobContext and returns a
    JSON-serializable dict, saved as the job result.
    """
    def decorator(handler: JobHandler) -> JobHandler:
        key = (domain, type)
        if key in _definitions:
            raise ValueError(f"Job {domain}.{type} is already registered")
        _definitions[key] = JobDefinition(domain, type, handler, max_attempts, timeout_seconds)
        return handler
    return decorator


def get_job_definition(domain: str, type: str) -> Optional[JobDefinition]:
    return _definitions.get((domain, type))
