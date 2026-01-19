from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.DATABASE_NAME]
    await db.client.admin.command('ping')

async def close_mongo_connection():
    if db.client:
        db.client.close()

def get_database():
    return db.db

# MCP dedicated connection (separate event loop)
class MCPDatabase:
    client: AsyncIOMotorClient = None
    db = None

_mcp_db = MCPDatabase()

async def get_mcp_database():
    if _mcp_db.client is None:
        _mcp_db.client = AsyncIOMotorClient(settings.MONGODB_URL)
        _mcp_db.db = _mcp_db.client[settings.DATABASE_NAME]
    return _mcp_db.db

async def close_mcp_connection():
    if _mcp_db.client:
        _mcp_db.client.close()
        _mcp_db.client = None
        _mcp_db.db = None