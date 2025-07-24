# app/models/chunk.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class Chunk(BaseModel):
    """Modello interno per processamento chunk"""
    text: str
    index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChunkWithEmbedding(Chunk):
    """Chunk con embedding per inserimento in Qdrant"""
    embedding: List[float]
    document_id: str
    is_deleted: bool = False

class ChunkSearchResult(BaseModel):
    """Risultato di ricerca da Qdrant"""
    chunk_id: str
    document_id: str
    text: str
    index: int
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)