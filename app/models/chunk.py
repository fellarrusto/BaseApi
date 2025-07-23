from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class DocumentChunk(BaseModel):
    """Modello per un chunk di documento"""
    page_number: int
    chunk_text: str
    chunk_index: int  # indice del chunk nella pagina
    metadata: Dict[str, Any]

class ChunkResponse(BaseModel):
    """Modello di response per i chunk"""
    chunk_index: int
    page_number: int
    chunk_text: str
    chunk_length: int
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }