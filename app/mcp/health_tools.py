from app.mcp.server import mcp
from app.db.database import get_mcp_database
from app.models.health import HealthCheckInDB, HealthCheckResponse
import time

startup_time = time.time()

@mcp.tool()
async def health_check() -> str:
    """Verifica lo stato dell'API"""
    db = await get_mcp_database()

    uptime = time.time() - startup_time
    health_check_data = HealthCheckInDB(uptime=uptime)

    result = await db["healthchecks"].insert_one(health_check_data.dict(by_alias=True))
    created_check = await db["healthchecks"].find_one({"_id": result.inserted_id})

    response = HealthCheckResponse(
        status="healthy",
        timestamp=created_check["timestamp"],
        version="1.0.0",
        uptime=created_check["uptime"]
    )
    return f"Status: {response.status}, Uptime: {response.uptime:.2f}s"