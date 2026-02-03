# app/core/mcp.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

mcp = Server("my-mcp-server")
tools = []

def mcp_tool(name: str, description: str):
    def decorator(func):
        tools.append((Tool(name=name, description=description, inputSchema={"type": "object", "properties": {}}), func))
        return func
    return decorator

@mcp.list_tools()
async def list_tools():
    return [t[0] for t in tools]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict):
    for tool, func in tools:
        if tool.name == name:
            result = await func(**arguments)
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            return [TextContent(type="text", text=json.dumps(result, default=str))]