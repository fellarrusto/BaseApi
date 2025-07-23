# app/main.py
from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager
from app.api import health_router, book_router
from app.core.config import settings
from app.db.database import connect_to_mongo, close_mongo_connection, connect_to_qdrant, close_qdrant_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await connect_to_qdrant()
    yield
    # Cleanup al shutdown
    import subprocess
    subprocess.run(["/scripts/cleanup.sh"], check=False)
    await close_mongo_connection()
    await close_qdrant_connection()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

router = APIRouter(prefix="/api/v1")
router.include_router(health_router.router)
router.include_router(book_router.router)

app.include_router(router)