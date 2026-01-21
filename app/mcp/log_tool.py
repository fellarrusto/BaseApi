from datetime import datetime
from app.mcp.server import mcp
from app.db.database import get_mcp_database
from app.models.log import AuditLogInDB

@mcp.tool()
async def get_audit_logs(start_date: str, end_date: str) -> str:
    """Recupera i log di audit nel range specificato (formato: DD-MM-YYYY)"""
    db = await get_mcp_database()

    start_dt = datetime.strptime(start_date, "%d-%m-%Y")
    end_dt = datetime.strptime(end_date, "%d-%m-%Y").replace(hour=23, minute=59, second=59)

    cursor = db["audit_logs"].find({
        "timestamp": {"$gte": start_dt, "$lte": end_dt}
    }).sort("timestamp", -1)

    logs = await cursor.to_list(length=None)
    audit_logs = [AuditLogInDB(**log) for log in logs]

    if not audit_logs:
        return "Nessun log trovato nel range specificato"
    return "\n".join([f"[{l.timestamp}] {l.action} - {l.status}" for l in audit_logs])