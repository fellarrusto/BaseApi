# app/main.py
from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import connect_to_mongo, close_mongo_connection
from app.api import health_router, log_router
from app.core.mcp import mcp
from mcp.server.sse import SseServerTransport

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

router = APIRouter(prefix="/api/v1")
router.include_router(health_router.router)
router.include_router(log_router.router)
app.include_router(router)

transport = SseServerTransport("/mcp/messages")

class MCPApp:
    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if path == "/mcp/sse" and scope["method"] == "GET":
            async with transport.connect_sse(scope, receive, send) as streams:
                await mcp.run(streams[0], streams[1], mcp.create_initialization_options())
        elif path.startswith("/mcp/messages") and scope["method"] == "POST":
            await transport.handle_post_message(scope, receive, send)

app.mount("/mcp", MCPApp())