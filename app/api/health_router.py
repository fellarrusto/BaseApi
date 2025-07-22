from app.core.decorator import handle_errors, audit_log
from fastapi import APIRouter, status
from datetime import datetime
import time
from app.models.health import HealthCheckResponse
from app.services.health_service import health_service

router = APIRouter(prefix="/health", tags=["health"])

# Timestamp di avvio dell'applicazione
startup_time = time.time()

@router.get("/check",response_model=HealthCheckResponse,status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="GET", metadata={"service": "health"})
async def health_check() -> HealthCheckResponse:
    """Endpoint di health check base"""
    return await health_service.check(startup_time=startup_time)