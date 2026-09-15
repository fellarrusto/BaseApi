import logging
from functools import wraps
from typing import Callable

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppError,
    ExternalServiceError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
    UnauthorizedError,
)
from app.schemas.error import ErrorResponse

logger = logging.getLogger(__name__)

# Most specific classes first
_STATUS_CODES = [
    (UnauthorizedError, status.HTTP_401_UNAUTHORIZED),
    (ForbiddenError, status.HTTP_403_FORBIDDEN),
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidInputError, status.HTTP_400_BAD_REQUEST),
    (ExternalServiceError, status.HTTP_502_BAD_GATEWAY),
]


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=error, message=message)
    headers = {"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None
    return JSONResponse(status_code=status_code, content=body.model_dump(), headers=headers)


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
