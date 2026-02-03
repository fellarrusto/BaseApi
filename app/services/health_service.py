import time
from app.db.base_repository import BaseRepository
from app.db.database import get_repository
from app.models.health import HealthCheckInDB, HealthCheckResponse

class HealthService:
    def __init__(self):
        self._repo = None
    
    @property
    def repo(self) -> BaseRepository:
        if self._repo is None:
            self._repo = get_repository("healthchecks")
        return self._repo
    
    async def check(self, startup_time: float) -> HealthCheckResponse:
        health_check = HealthCheckInDB(uptime=time.time() - startup_time)
        await self.repo.insert_one(health_check.model_dump(by_alias=True))
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=health_check.timestamp,
            version="1.0.0",
            uptime=health_check.uptime
        )

health_service = HealthService()