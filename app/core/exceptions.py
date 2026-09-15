class AppError(Exception):
    """
    Base class for expected application errors.

    Services and repositories raise these instead of HTTPException, so they
    stay usable outside an HTTP request. @handle_errors
    (app/decorators/error_handler.py) maps each class to an HTTP status code.
    """


class UnauthorizedError(AppError):
    """Missing or invalid credentials (401)."""


class ForbiddenError(AppError):
    """Authenticated, but not allowed to do this (403)."""


class NotFoundError(AppError):
    """The requested entity does not exist (404)."""


class InvalidInputError(AppError):
    """The input violates a business rule (400)."""


class ExternalServiceError(AppError):
    """An external integration failed or is not configured (502)."""


class JobCancelledError(Exception):
    """Raised inside a job handler when cancellation was requested (worker only, not HTTP)."""
