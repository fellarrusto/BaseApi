from app.db.database import get_database
from app.models.log import AuditLogInDB
from datetime import datetime
from typing import List

class LogService:
    def __init__(self):
        self.collection = "audit_logs"
    
    async def save_log(self, log_data: AuditLogInDB):
        db = get_database()
        await db[self.collection].insert_one(log_data.dict(by_alias=True))
    
    async def get_logs_by_date_range(self, start_date: datetime, end_date: datetime) -> List[AuditLogInDB]:
        db = get_database()
        cursor = db[self.collection].find({
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }).sort("timestamp", -1)
        
        logs = await cursor.to_list(length=None)
        return [AuditLogInDB(**log) for log in logs]

log_service = LogService()