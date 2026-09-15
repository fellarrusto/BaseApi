import inspect
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError, ExternalServiceError, InvalidInputError, NotFoundError
from app.schemas.error import ErrorResponse
from app.services.audit_log_service import audit_log_service

logger = logging.getLogger(__name__)

# Most specific classes first
_STATUS_CODES = [
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidInputError, status.HTTP_400_BAD_REQUEST),
    (ExternalServiceError, status.HTTP_502_BAD_GATEWAY),
]

# Injected into the endpoint signature by @audit_log, invisible to the endpoint
_REQUEST_PARAM = "_audit_request"


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=error, message=message)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def handle_errors(func: Callable) -> Callable:
    """
    Convert exceptions raised by an endpoint into JSON error responses.

    AppError subclasses map to their status code, HTTPException passes
    through, anything else becomes a generic 500: the traceback is logged,
    never sent to the client.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except AppError as e:
            status_code = next(
                (code for cls, code in _STATUS_CODES if isinstance(e, cls)),
                status.HTTP_400_BAD_REQUEST
            )
            return _error_response(status_code, type(e).__name__, str(e))
        except Exception:
            logger.exception("Unhandled error in %s", func.__name__)
            return _error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "InternalServerError",
                "Internal server error"
            )
    return wrapper


def audit_log(metadata: Optional[Dict[str, Any]] = None) -> Callable:
    """
    Record every call of an endpoint in the audit_logs collection.

    Method and path come from the request, which FastAPI injects through an
    extra parameter added to the endpoint signature. A failure while writing
    the log is logged and never affects the response.
    """
    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)
        request_param = inspect.Parameter(
            _REQUEST_PARAM, inspect.Parameter.KEYWORD_ONLY, annotation=Request
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.pop(_REQUEST_PARAM)
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

        wrapper.__signature__ = signature.replace(
            parameters=[*signature.parameters.values(), request_param]
        )
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
    try:
        await audit_log_service.record(
            action=action,
            endpoint=request.url.path,
            method=request.method,
            status="error" if error else "success",
            duration_ms=duration_ms,
            metadata=log_metadata
        )
    except Exception:
        logger.exception("Failed to write audit log for %s %s", request.method, request.url.path)
