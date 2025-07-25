import re
from typing import List, Dict, Any
from app.models.chunk import Chunk

# Configurazione chunking - definita a livello di sistema
CHUNK_WORDS = 100
CHUNK_MERGE = 5
CHUNK_OVERLAP = 2

def clean_text(text: str) -> str:
    # Rimuove i caratteri di nuova linea e li sostituisce con uno spazio singolo
    cleaned_text = text.replace('\n', ' ').replace('\r', ' ')
    # Rimuove i caratteri speciali (mantenendo lettere, numeri, spazi e punteggiatura specificata)
    cleaned_text = re.sub(r'[^\w\s.,!?;]', '', cleaned_text)
    # Rimuove multipli spazi bianchi consecutivi
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = cleaned_text.lower()
    return cleaned_text

def get_chunks(min_gap: int, text: str) -> List[str]:
  text_clean = clean_text(text)
  text_array = text_clean.split(" ")
  eol_idx = []
  last_idx = 0
  for i, w in enumerate(text_array):
    if "." in w and len(w) > 3 and i>last_idx+min_gap:
      last_idx = i+1
      eol_idx.append(i+1)
  chunks = []
  last_idx = 0
  for idx in eol_idx:
    chunks.append(" ".join(text_array[last_idx:idx]))
    last_idx = idx
  return chunks

def get_chunks_overlap(chunks: List[str], chunk_len: int, overlap: int) -> List[str]:
  s_idx = 0
  e_idx = s_idx + chunk_len
  chunks_merge = []
  while e_idx<len(chunks):
    print(s_idx, e_idx-1)
    chunks_merge.append(" ".join(chunks[s_idx:e_idx-1]))
    s_idx = e_idx - overlap
    e_idx = s_idx + chunk_len
  return chunks_merge

def create_chunks(
    text: str, 
    metadata: Dict[str, Any] = {}
) -> List[Chunk]:
    """Divide il testo in chunks con overlap"""
    chunks = get_chunks(CHUNK_WORDS, text)
    chunks_merge = get_chunks_overlap(chunks, CHUNK_MERGE, CHUNK_OVERLAP)
    
    chunks_out = []
    for i, ch in enumerate(chunks_merge):
        chunks_out.append(Chunk(
            text=ch,
            index=i,
            metadata={**metadata, "chunk_size": len(ch)}
        ))
    
    
    
    return chunks_out