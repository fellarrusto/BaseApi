# app/services/vector_service.py
from typing import List, Dict, Any, Optional
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
import uuid
from sentence_transformers import SentenceTransformer
from app.db.database import get_qdrant_client
from app.models.chunk import DocumentChunk

class VectorService:
    def __init__(self):
        self.collection_name = "document_chunks"
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Modello leggero per embeddings
        self.vector_size = 384  # Dimensione dell'embedding del modello
    
    async def _ensure_collection_exists(self):
        """Crea la collection se non esiste"""
        client = get_qdrant_client()
        
        try:
            await client.get_collection(self.collection_name)
        except:
            # Collection non esiste, la creiamo
            await client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
    
    def _get_embedding(self, text: str) -> List[float]:
        """Genera embedding per il testo"""
        return self.model.encode(text).tolist()
    
    async def add_chunk(self, chunk: DocumentChunk, book_id: str) -> str:
        """Aggiunge un chunk alla collection"""
        await self._ensure_collection_exists()
        client = get_qdrant_client()
        
        # Genera embedding
        embedding = self._get_embedding(chunk.chunk_text)
        
        # Genera ID univoco
        point_id = str(uuid.uuid4())
        
        # Prepara metadati
        payload = {
            "book_id": book_id,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.chunk_text,
            "chunk_length": len(chunk.chunk_text),
            **chunk.metadata
        }
        
        # Inserisce il punto
        await client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )]
        )
        
        return point_id
    
    
    async def search_chunks(self, query: str, limit: int = 10, book_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Ricerca semantica nei chunks"""
        await self._ensure_collection_exists()
        client = get_qdrant_client()
        
        # Genera embedding per la query
        query_embedding = self._get_embedding(query)
        
        # Filtro opzionale per libro specifico
        query_filter = None
        if book_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="book_id",
                        match=MatchValue(value=book_id)
                    )
                ]
            )
        
        # Esegue la ricerca
        search_result = await client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit
        )
        
        # Formatta risultati
        results = []
        for hit in search_result:
            results.append({
                "id": hit.id,
                "score": hit.score,
                "book_id": hit.payload.get("book_id"),
                "page_number": hit.payload.get("page_number"),
                "chunk_index": hit.payload.get("chunk_index"),
                "chunk_text": hit.payload.get("chunk_text"),
                "chunk_length": hit.payload.get("chunk_length"),
                "metadata": {k: v for k, v in hit.payload.items() 
                           if k not in ["book_id", "page_number", "chunk_index", "chunk_text", "chunk_length"]}
            })
        
        return results
    
    async def delete_chunks_by_book(self, book_id: str) -> bool:
        """Elimina tutti i chunks di un libro"""
        await self._ensure_collection_exists()
        client = get_qdrant_client()
        
        try:
            # Trova tutti i punti del libro
            search_result = await client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="book_id",
                            match=MatchValue(value=book_id)
                        )
                    ]
                )
            )
            
            # Estrae gli ID
            point_ids = [point.id for point in search_result[0]]
            
            if point_ids:
                # Elimina i punti
                await client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
            
            return True
        except Exception as e:
            print(f"Error deleting chunks for book {book_id}: {str(e)}")
            return False
    
    async def get_chunks_by_book(self, book_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Recupera tutti i chunks di un libro"""
        await self._ensure_collection_exists()
        client = get_qdrant_client()
        
        search_result = await client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="book_id",
                        match=MatchValue(value=book_id)
                    )
                ]
            ),
            limit=limit
        )
        
        results = []
        for point in search_result[0]:
            results.append({
                "id": point.id,
                "book_id": point.payload.get("book_id"),
                "page_number": point.payload.get("page_number"),
                "chunk_index": point.payload.get("chunk_index"),
                "chunk_text": point.payload.get("chunk_text"),
                "chunk_length": point.payload.get("chunk_length"),
                "metadata": {k: v for k, v in point.payload.items() 
                           if k not in ["book_id", "page_number", "chunk_index", "chunk_text", "chunk_length"]}
            })
        
        return results
    
    async def update_chunk(self, point_id: str, chunk: DocumentChunk, book_id: str) -> bool:
        """Aggiorna un chunk esistente"""
        await self._ensure_collection_exists()
        client = get_qdrant_client()
        
        try:
            # Genera nuovo embedding
            embedding = self._get_embedding(chunk.chunk_text)
            
            # Prepara payload aggiornato
            payload = {
                "book_id": book_id,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "chunk_length": len(chunk.chunk_text),
                **chunk.metadata
            }
            
            # Aggiorna il punto
            await client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )]
            )
            
            return True
        except Exception as e:
            print(f"Error updating chunk {point_id}: {str(e)}")
            return False

vector_service = VectorService()