from datetime import datetime
from typing import List
from app.db.base_repository import BaseRepository
from app.db.database import get_repository
from app.models.log import AuditLogInDB

class LogService:
    def __init__(self):
        self._repo = None
    
    @property
    def repo(self) -> BaseRepository:
        if self._repo is None:
            self._repo = get_repository("audit_logs")
        return self._repo
    
    async def save_log(self, log_data: AuditLogInDB):
        await self.repo.insert_one(log_data.model_dump(by_alias=True))
    
    async def get_logs_by_date_range(self, start_date: datetime, end_date: datetime) -> List[AuditLogInDB]:
        docs = await self.repo.find_many(
            filters={"timestamp": {"$gte": start_date, "$lte": end_date}},
            sort=[("timestamp", -1)]
        )
        return [AuditLogInDB(**doc) for doc in docs]

log_service = LogService()