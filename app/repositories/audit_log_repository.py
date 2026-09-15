from datetime import datetime
from typing import List

from app.models.audit_log import AuditLogInDB
from app.repositories.entity_repository import EntityRepository


class AuditLogRepository(EntityRepository[AuditLogInDB]):
    """Data access for audit logs."""

    collection = "audit_logs"
    model = AuditLogInDB

    async def find_by_time_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
        skip: int = 0
    ) -> List[AuditLogInDB]:
        """Logs with start <= timestamp < end, newest first."""
        return await self._find_many(
            {"timestamp": {"$gte": start, "$lt": end}},
            limit=limit,
            skip=skip,
            sort=[("timestamp", -1)]
        )


audit_log_repository = AuditLogRepository()
