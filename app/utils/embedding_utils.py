# app/utils/embedding_utils.py
from typing import List
from sentence_transformers import SentenceTransformer
import os
from pathlib import Path

MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'
MODEL_CACHE_DIR = './models'  # Directory locale per i modelli

def check_model_exists(model_name: str, cache_dir: str) -> bool:
    """Controlla se il modello esiste già localmente"""
    model_path = Path(cache_dir) / model_name
    # Controlla se esistono i file essenziali del modello
    required_files = ['config.json', 'pytorch_model.bin']
    return model_path.exists() and all((model_path / file).exists() for file in required_files)

def load_model():
    """Carica il modello, scaricandolo solo se necessario"""
    # Crea la directory se non esiste
    os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    
    if check_model_exists(MODEL_NAME, MODEL_CACHE_DIR):
        print(f"Model {MODEL_NAME} found locally, loading from cache...")
        model = SentenceTransformer(f"{MODEL_CACHE_DIR}/{MODEL_NAME}")
    else:
        print(f"Model {MODEL_NAME} not found locally, downloading...")
        model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
        # Salva il modello localmente
        model.save(f"{MODEL_CACHE_DIR}/{MODEL_NAME}")
        print(f"Model saved to {MODEL_CACHE_DIR}/{MODEL_NAME}")
    
    print(f"{MODEL_NAME} ready to use")
    return model

# Carica il modello una sola volta
model = load_model()

def generate_embedding(text: str) -> List[float]:
    return model.encode(text).tolist()

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    return model.encode(texts).tolist()

def get_embedding_dimension() -> int:
    return len(model.encode(""))