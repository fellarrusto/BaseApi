from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import connect_to_mongo, close_mongo_connection

from app.api import health_router
from app.api import log_router

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