from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import v1
from app.api.error_handlers import register_error_handlers
from app.api.middleware import AuditMiddleware
from app.core.config import settings
from app.db.database import db_connect, db_disconnect
from app.integrations.clients import integrations_connect, integrations_disconnect


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_connect()
    await integrations_connect()
    yield
    await integrations_disconnect()
    await db_disconnect()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(AuditMiddleware)
register_error_handlers(app)
app.include_router(v1.api_router)
