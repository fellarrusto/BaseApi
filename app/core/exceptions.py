class AppError(Exception):
    """
    Base class for expected application errors.

    Services and repositories raise these instead of HTTPException, so they
    stay usable outside an HTTP request. @handle_errors (app/core/decorator.py)
    maps each class to an HTTP status code.
    """


class NotFoundError(AppError):
    """The requested entity does not exist (404)."""


class InvalidInputError(AppError):
    """The input violates a business rule (400)."""


class ExternalServiceError(AppError):
    """An external integration failed or is not configured (502)."""
