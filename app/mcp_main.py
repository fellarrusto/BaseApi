from app.db.database import connect_to_mongo
from app.mcp import run_mcp
import asyncio

asyncio.get_event_loop().run_until_complete(connect_to_mongo())
run_mcp()