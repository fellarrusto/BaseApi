# app/utils/embedding_utils.py
from typing import List
from sentence_transformers import SentenceTransformer

# Modello di embedding - definito a livello di sistema
MODEL_NAME = 'all-MiniLM-L6-v2'

print("Loading model..")
model = SentenceTransformer(MODEL_NAME)
print(f"{MODEL_NAME} Loaded")

def generate_embedding(text: str) -> List[float]:
    """Genera embedding per una singola stringa"""
    return model.encode(text).tolist()

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Genera embeddings per multiple stringhe"""
    return model.encode(texts).tolist()

def get_embedding_dimension() -> int:
    """Restituisce la dimensione del vettore di embedding"""
    return len(model.encode(""))