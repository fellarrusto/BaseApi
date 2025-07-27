# app/services/vector_service.py
from typing import List, Optional, Dict, Any
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, VectorParams, Distance, ScoredPoint
import uuid

from app.db.database import get_qdrant_client
from app.models.chunk import ChunkWithEmbedding
from app.models.search import HybridChunk
from app.utils import embedding_utils

class VectorService:
    def __init__(self, collection_name: str = "document_chunks"):
        self.collection_name = collection_name
    
    async def ensure_collection_exists(self, collection_name: Optional[str] = None):
        """Crea collection se non esiste"""
        client = get_qdrant_client()
        collection = collection_name or self.collection_name
        
        try:
            await client.get_collection(collection)
        except:
            await client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=embedding_utils.get_embedding_dimension(),
                    distance=Distance.COSINE
                )
            )
    
    async def insert_chunks(self, chunks: List[ChunkWithEmbedding], document_id: str, collection_name: Optional[str] = None):
        """Inserisce chunks in Qdrant"""
        collection = collection_name or self.collection_name
        await self.ensure_collection_exists(collection)
        client = get_qdrant_client()
        
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=chunk.embedding,
                payload={
                    "document_id": document_id,
                    "text": chunk.text,
                    "index": chunk.index,
                    "is_deleted": chunk.is_deleted,
                    **chunk.metadata
                }
            )
            for chunk in chunks
        ]
        
        await client.upsert(
            collection_name=collection,
            points=points
        )
    
    async def delete_document_chunks(self, document_id: str, collection_name: Optional[str] = None):
        """Elimina tutti i chunks di un documento"""
        client = get_qdrant_client()
        collection = collection_name or self.collection_name
        
        result = await client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        )
        
        if result[0]:
            point_ids = [point.id for point in result[0]]
            await client.delete(
                collection_name=collection,
                points_selector=point_ids
            )
    
    async def update_chunks_deleted_flag(self, document_id: str, is_deleted: bool, collection_name: Optional[str] = None):
        """Aggiorna flag deleted sui chunks"""
        client = get_qdrant_client()
        collection = collection_name or self.collection_name
        
        result = await client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        )
        
        for point in result[0]:
            point.payload["is_deleted"] = is_deleted
            await client.set_payload(
                collection_name=collection,
                payload=point.payload,
                points=[point.id]
            )
    
    async def query(self, 
                   query_vector: List[float], 
                   limit: int = 10,
                   filters: Optional[Filter] = None,
                   collection_name: Optional[str] = None) -> List[ScoredPoint]:
        """Query vettoriale generica"""
        client = get_qdrant_client()
        collection = collection_name or self.collection_name
        
        try:
            return await client.search(
                collection_name=collection,
                query_vector=query_vector,
                query_filter=filters,
                limit=limit
            )
        except Exception:
            # Se la collection non esiste o altro errore, ritorna lista vuota
            return []
        
    @staticmethod
    def normalize(chunks: List[HybridChunk]) -> List[HybridChunk]:
        scores = [chunk.score for chunk in chunks if chunk.score is not None]
        if not scores:
            return chunks
        min_score, max_score = min(scores), max(scores)
        if max_score == min_score:
            for chunk in chunks:
                chunk.score = 0.0
            return chunks
        for chunk in chunks:
            if chunk.score is not None:
                chunk.score = (chunk.score - min_score) / (max_score - min_score)
        return chunks

vector_service = VectorService()