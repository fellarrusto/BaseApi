from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Body of every error response produced by @handle_errors."""
    error: str
    message: str
