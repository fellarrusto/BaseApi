import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import v1
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.database import db_connect, db_disconnect
from app.integrations.clients import integrations_connect, integrations_disconnect
from app.repositories.entity_repository import ensure_all_indexes

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTH_MOCK_ENABLED:
        logger.warning("AUTH_MOCK_ENABLED: mock bearer tokens are accepted, never use it in production")
    await db_connect()
    await ensure_all_indexes()
    await integrations_connect()
    yield
    await integrations_disconnect()
    await db_disconnect()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.APP_VERSION, lifespan=lifespan)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        # A wildcard origin must never be combined with credentials
        allow_credentials="*" not in settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"]
    )

app.include_router(v1.api_router)
