from typing import List, Optional

from fastapi import APIRouter, Query, status

from app.decorators import audit_log, handle_errors, require_auth
from app.schemas.auth import AuthUser
from app.schemas.job import JobResponse
from app.services.job_service import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[JobResponse], status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "jobs"})
@require_auth()
async def list_jobs(
    current_user: AuthUser,
    domain: Optional[str] = Query(None, description="Filter by domain, e.g. demo"),
    job_type: Optional[str] = Query(None, alias="type", description="Filter by type, e.g. timer"),
    job_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    skip: int = Query(0, ge=0, description="Results to skip")
) -> List[JobResponse]:
    """List your jobs (every job for admins), newest first."""
    return await job_service.list_for_user(
        current_user, domain=domain, job_type=job_type, status=job_status, limit=limit, skip=skip
    )


@router.get("/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "jobs"})
@require_auth()
async def get_job(job_id: str, current_user: AuthUser) -> JobResponse:
    """Fetch a job with its status, progress and result."""
    return await job_service.get_for_user(job_id, current_user)


@router.post("/{job_id}/cancel", response_model=JobResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(metadata={"service": "jobs"})
@require_auth()
async def cancel_job(job_id: str, current_user: AuthUser) -> JobResponse:
    """Cancel a pending job, or ask a running job to stop."""
    return await job_service.cancel(job_id, current_user)
