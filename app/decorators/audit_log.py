import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import Request

from app.decorators._signature import (
    expose_signature,
    hidden_request_parameter,
    request_parameter,
    take_request,
)
from app.services.audit_log_service import audit_log_service

logger = logging.getLogger(__name__)


def audit_log(metadata: Optional[Dict[str, Any]] = None, enabled: bool = True) -> Callable:
    """
    Record every call of an endpoint in the audit_logs collection.

    Method and path come from the request, the user from @require_auth
    (when used). A failure while writing the log is logged and never
    affects the response. `enabled=False` records nothing: use it only for
    very frequent technical calls such as health probes.
    """
    def decorator(func: Callable) -> Callable:
        if not enabled:
            return func
        request_name, forward_request = request_parameter(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = take_request(kwargs, request_name, forward_request)
            started = time.perf_counter()
            error: Optional[Exception] = None
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error = e
                raise
            finally:
                duration_ms = (time.perf_counter() - started) * 1000
                await _record(func.__name__, request, duration_ms, metadata, error)

        expose_signature(wrapper, func, add=[] if forward_request else [hidden_request_parameter()])
        return wrapper
    return decorator


async def _record(
    action: str,
    request: Request,
    duration_ms: float,
    metadata: Optional[Dict[str, Any]],
    error: Optional[Exception]
) -> None:
    log_metadata = dict(metadata or {})  # copy: the decorator's dict is shared by every call
    if error is not None:
        log_metadata["error"] = f"{type(error).__name__}: {error}"
    user = getattr(request.state, "user", None)  # set by @require_auth
    try:
        await audit_log_service.record(
            action=action,
            endpoint=request.url.path,
            method=request.method,
            status="error" if error else "success",
            duration_ms=duration_ms,
            user_id=user.id if user else None,
            metadata=log_metadata
        )
    except Exception:
        logger.exception("Failed to write audit log for %s %s", request.method, request.url.path)
