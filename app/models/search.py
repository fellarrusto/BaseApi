# app/models/search.py
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from bson import ObjectId
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

class HybridChunk(BaseModel):
    """Risultato unificato per chunk da diverse sorgenti"""
    chunk_id: str
    document_id: str
    text: str
    source_filename: str
    index: int
    score: Optional[float] = None
    origin: Literal["keyword", "vector"]
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_mongodb(cls, mongo_result: Dict[str, Any]) -> "HybridChunk":
        """Crea da risultato MongoDB (keyword search)"""
        return cls(
            chunk_id=str(mongo_result["_id"]),
            document_id=str(mongo_result["document_id"]),
            text=mongo_result["text"],
            source_filename=mongo_result.get("metadata", {}).get("source_filename", ""),
            index=mongo_result["index"],
            score=None,  # MongoDB non ha score
            origin="keyword",
            metadata=mongo_result.get("metadata", {})
        )
    
    @classmethod
    def from_qdrant(cls, qdrant_result) -> "HybridChunk":
        """Crea da risultato Qdrant (vector search)"""
        payload = qdrant_result.payload
        
        # Estrai metadata escludendo campi principali
        metadata = {k: v for k, v in payload.items() 
                   if k not in ["document_id", "text", "index", "is_deleted", "chunk_id"]}
        
        return cls(
            chunk_id=str(qdrant_result.id),
            document_id=payload["document_id"],
            text=payload["text"],
            source_filename=metadata.get("source_filename", ""),
            index=payload["index"],
            score=qdrant_result.score,
            origin="vector",
            metadata=metadata
        )

class KeywordSearchResponse(SearchResponse):
    """Risposta per ricerca keywords"""
    search_type: str = "keyword"
    page: int = 1
    documents: List[DocumentResponse]

class VectorSearchResponse(SearchResponse):
    """Risposta per ricerca vettoriale"""
    search_type: str = "vector"
    page: int = 1
    chunks: List[ChunkSearchResult]
    documents: List[DocumentResponse]

class HybridSearchResponse(SearchResponse):
    """Risposta per ricerca ibrida"""
    search_type: str = "hybrid"
    page: int = 1
    chunks: List[HybridChunk]