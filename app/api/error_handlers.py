from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError, ExternalServiceError, InvalidInputError, NotFoundError
from app.schemas.error import ErrorResponse

# Most specific classes first
_STATUS_CODES = [
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidInputError, status.HTTP_400_BAD_REQUEST),
    (ExternalServiceError, status.HTTP_502_BAD_GATEWAY),
]


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=error, message=message)
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    status_code = next(
        (code for cls, code in _STATUS_CODES if isinstance(exc, cls)),
        status.HTTP_400_BAD_REQUEST
    )
    return _error_response(status_code, type(exc).__name__, str(exc))


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # No internals in the response: Starlette re-raises the exception after
    # sending it, so the traceback still reaches the server log.
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "InternalServerError",
        "Internal server error"
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
