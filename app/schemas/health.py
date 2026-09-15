from pydantic import BaseModel


class LivenessResponse(BaseModel):
    """The API process is running."""
    status: str          # "alive"
    version: str
    uptime_seconds: float


class ReadinessResponse(BaseModel):
    """The API can serve requests: its dependencies are reachable."""
    status: str          # "ready"
    database: str        # "up"
