## MongoDB
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.DATABASE_NAME]

async def close_mongo_connection():
    if db.client:
        db.client.close()

def get_database():
    return db.db

## Qdrant

from qdrant_client import AsyncQdrantClient

class QdrantDB:
    client: AsyncQdrantClient = None

qdrant_db = QdrantDB()

async def connect_to_qdrant():
    qdrant_db.client = AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )

async def close_qdrant_connection():
    if qdrant_db.client:
        await qdrant_db.client.close()

def get_qdrant_client():
    return qdrant_db.client