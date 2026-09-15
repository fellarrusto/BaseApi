import asyncio
from typing import Optional

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings
from app.db.base_storage import BaseStorage
from app.db.mongo_storage import MongoStorage

PING_TIMEOUT_SECONDS = 3


class Database:
    client: Optional[AsyncMongoClient] = None
    db: Optional[AsyncDatabase] = None


db = Database()


async def db_connect() -> None:
    # tz_aware: datetimes are read back as UTC-aware, matching what we store
    db.client = AsyncMongoClient(settings.MONGODB_URI, tz_aware=True)
    db.db = db.client[settings.MONGO_DB]
    await db.client.admin.command("ping")


async def db_disconnect() -> None:
    if db.client:
        await db.client.close()


async def ping_database() -> bool:
    """Return True if the database answers within PING_TIMEOUT_SECONDS."""
    try:
        await asyncio.wait_for(db.client.admin.command("ping"), PING_TIMEOUT_SECONDS)
        return True
    except Exception:
        return False


def get_storage(collection: str) -> BaseStorage:
    """Storage factory: the only place that knows which backend is active."""
    return MongoStorage(db.db, collection)
