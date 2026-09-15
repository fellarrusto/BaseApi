from fastapi import APIRouter

from app.api.v1 import audit_log_router, health_router, job_router, timer_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router.router)
api_router.include_router(audit_log_router.router)
api_router.include_router(job_router.router)
api_router.include_router(timer_router.router)
