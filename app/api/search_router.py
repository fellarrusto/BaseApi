from fastapi import APIRouter, HTTPException, status
from app.models.search import (
    SearchRequest, KeywordSearchResponse,
    VectorSearchResponse, HybridSearchResponse
)
from app.services.search_service import search_service
from app.core.decorator import handle_errors, audit_log

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/keyword", response_model=KeywordSearchResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="POST", metadata={"service": "search", "action": "keyword"})
async def keyword_search(request: SearchRequest) -> KeywordSearchResponse:
    return await search_service.keyword_search(request)

@router.post("/vector", response_model=VectorSearchResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="POST", metadata={"service": "search", "action": "vector"})
async def vector_search(request: SearchRequest) -> VectorSearchResponse:
    return await search_service.vector_search(request)

@router.post("/hybrid", response_model=HybridSearchResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
@handle_errors
@audit_log(method="POST", metadata={"service": "search", "action": "hybrid"})
async def hybrid_search(request: SearchRequest) -> HybridSearchResponse:
    return await search_service.hybrid_search(request)
