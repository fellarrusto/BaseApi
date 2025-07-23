from pydantic import BaseModel
from typing import Dict, Any, Optional

class DocumentChunk(BaseModel):
    """Modello per un chunk di documento"""
    page_number: int
    chunk_text: str
    chunk_index: int  # indice del chunk nella pagina
    metadata: Dict[str, Any]