# app/utils/chunking_utils.py
from typing import List, Dict, Any
from app.models.chunk import Chunk

# Configurazione chunking - definita a livello di sistema
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def create_chunks(
    text: str, 
    metadata: Dict[str, Any] = {}
) -> List[Chunk]:
    """Divide il testo in chunks con overlap"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text = text[start:end]
        
        chunks.append(Chunk(
            text=chunk_text,
            index=len(chunks),
            metadata={**metadata, "chunk_size": len(chunk_text)}
        ))
        
        if end >= len(text):
            break
            
        start = end - CHUNK_OVERLAP
    
    return chunks