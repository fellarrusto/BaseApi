# app/services/vector_service.py
from typing import List, Optional, Dict, Any
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, VectorParams, Distance
import uuid

from app.db.database import get_qdrant_client
from app.models.chunk import ChunkWithEmbedding
from app.utils import embedding_utils

class VectorService:
    def __init__(self):
        self.collection_name = "document_chunks"
    
    async def ensure_collection_exists(self):
        """Crea collection se non esiste"""
        client = get_qdrant_client()
        
        try:
            await client.get_collection(self.collection_name)
        except:
            await client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedding_utils.get_embedding_dimension(),
                    distance=Distance.COSINE
                )
            )
    
    async def insert_chunks(self, chunks: List[ChunkWithEmbedding], document_id: str):
        """Inserisce chunks in Qdrant"""
        await self.ensure_collection_exists()
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
            collection_name=self.collection_name,
            points=points
        )
    
    async def delete_document_chunks(self, document_id: str):
        """Elimina tutti i chunks di un documento"""
        client = get_qdrant_client()
        
        result = await client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        )
        
        if result[0]:
            point_ids = [point.id for point in result[0]]
            await client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids
            )
    
    async def update_chunks_deleted_flag(self, document_id: str, is_deleted: bool):
        """Aggiorna flag deleted sui chunks"""
        client = get_qdrant_client()
        
        result = await client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        )
        
        for point in result[0]:
            point.payload["is_deleted"] = is_deleted
            await client.set_payload(
                collection_name=self.collection_name,
                payload=point.payload,
                points=[point.id]
            )

vector_service = VectorService()