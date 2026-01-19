from app.mcp.server import mcp
from app.mcp import health_tools
from app.mcp import log_tool

def run_mcp():
    mcp.run(transport="sse")