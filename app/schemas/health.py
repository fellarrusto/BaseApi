from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """API response model for the health check."""
    status: str          # "healthy" | "degraded"
    version: str
    uptime_seconds: float
    database: str        # "up" | "down"
