from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Body of every error response produced by app/api/error_handlers.py."""
    error: str
    message: str
