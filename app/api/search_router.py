from fastapi import APIRouter, Query, status
from typing import Optional, List
from app.core.decorator import handle_errors, audit_log
from app.models.search import (
    SearchResponse
)
from app.services.search_service import search_service

router = APIRouter(prefix="/searsh", tags=["search"])

@router.get("/keywords/", response_model=SearchResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="GET", metadata={"service": "books"})
async def search_books(
    q: str = Query(..., description="Search keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
) -> SearchResponse:
    """Ricerca libri per keyword"""
    return await search_service.search_books(keyword=q, page=page, limit=limit)