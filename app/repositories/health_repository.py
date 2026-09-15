from app.db.database import ping_database


class HealthRepository:
    """Health has no persisted entity: the repository only probes the database."""

    async def ping(self) -> bool:
        return await ping_database()


health_repository = HealthRepository()
