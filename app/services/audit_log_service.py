from datetime import date, datetime, time, timedelta, timezone
from typing import List

from app.core.exceptions import InvalidInputError
from app.models.audit_log import AuditLogInDB
from app.repositories.audit_log_repository import audit_log_repository
from app.schemas.audit_log import AuditLogResponse


class AuditLogService:
    """Business logic for audit logs."""

    async def record(
        self,
        action: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float
    ) -> None:
        """Persist one audit entry for a handled API call."""
        await audit_log_repository.create(AuditLogInDB(
            action=action,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms
        ))

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        limit: int = 100,
        skip: int = 0
    ) -> List[AuditLogResponse]:
        """
        Fetch audit logs between two dates (both inclusive, UTC), newest first.

        Raises:
            InvalidInputError: If end_date is before start_date
        """
        if end_date < start_date:
            raise InvalidInputError("end_date must be on or after start_date")

        start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        logs = await audit_log_repository.find_by_time_range(start, end, limit=limit, skip=skip)
        return [self._to_response(log) for log in logs]

    def _to_response(self, log: AuditLogInDB) -> AuditLogResponse:
        return AuditLogResponse(id=str(log.id), **log.model_dump(exclude={"id"}))


audit_log_service = AuditLogService()
