from typing import List

from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    """Authenticated caller, produced by auth_service.authenticate()."""
    id: str
    roles: List[str] = Field(default_factory=list)
