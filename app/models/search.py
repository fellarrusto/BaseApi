# app/models/search.py
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal
from app.models.document import DocumentResponse
from app.models.chunk import ChunkSearchResult

class SearchRequest(BaseModel):
    """Richiesta di ricerca"""
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    """Risposta base per ricerca"""
    query: str
    total: int
    limit: int

class KeywordSearchResponse(SearchResponse):
    """Risposta per ricerca keywords"""
    documents: List[DocumentResponse]

class VectorSearchResponse(SearchResponse):
    """Risposta per ricerca vettoriale"""
    chunks: List[ChunkSearchResult]
    documents: List[DocumentResponse]  # Documenti correlati ai chunks

class HybridSearchResponse(SearchResponse):
    """Risposta per ricerca ibrida"""
    documents: List[DocumentResponse]
    chunks: List[ChunkSearchResult]
    keyword_score_weight: float = 0.5
    vector_score_weight: float = 0.5