from app.db.base_repository import BaseRepository
from app.db.mongo_repository import MongoRepository
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def db_connect():
    db.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db.db = db.client[settings.MONGO_DB]
    await db.client.admin.command('ping')

async def db_disconnect():
    if db.client:
        db.client.close()

def get_repository(collection: str) -> BaseRepository:
    return MongoRepository(get_database(), collection)

def get_database():
    return db.db
