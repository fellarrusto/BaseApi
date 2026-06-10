# app/main.py
from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import db_disconnect, db_connect
from app.api import health_router, log_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_connect()
    yield
    await db_disconnect()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

router = APIRouter(prefix="/api/v1")
router.include_router(health_router.router)
router.include_router(log_router.router)
app.include_router(router)
