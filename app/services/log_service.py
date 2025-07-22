from app.db.database import get_database
from app.models.log import AuditLogInDB

class LogService:
    def __init__(self):
        self.collection = "audit_logs"
    
    async def save_log(self, log_data: AuditLogInDB):
        db = get_database()
        await db[self.collection].insert_one(log_data.dict(by_alias=True))

log_service = LogService()