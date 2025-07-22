# app/services/reminder_service.py
from typing import Optional, List
from bson import ObjectId
import time
from app.db.database import get_database
from app.models.health import (
    HealthCheckInDB,
    HealthCheckResponse
)

class HealthService:
    def __init__(self):
        self.collection = "healthchecks"
    
    async def check(self, startup_time) -> HealthCheckResponse:
        db = get_database()
        
        health_check = HealthCheckInDB(uptime=time.time() - startup_time)
        
        result = await db[self.collection].insert_one(health_check.dict(by_alias=True))
        created_check = await db[self.collection].find_one({"_id": result.inserted_id})
        
        return HealthCheckResponse(
                status="healthy",
                timestamp=created_check["timestamp"],
                version="1.0.0",
                uptime=created_check["uptime"]
            )
        
health_service = HealthService()