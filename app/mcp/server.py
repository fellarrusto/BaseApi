from mcp.server.fastmcp import FastMCP
from app.core.config import settings

mcp = FastMCP(
    "Base API MCP",
    host="0.0.0.0",
    port=settings.MCP_PORT,
)