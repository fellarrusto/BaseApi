# app/services/search_service.py
from typing import List, Set
from bson import ObjectId
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.db.database import get_database, get_qdrant_client
from app.utils.embedding_utils import generate_embedding
from app.models.search import (
    SearchRequest, KeywordSearchResponse,
    VectorSearchResponse, ChunkSearchResult
)
from app.models.document import DocumentResponse

class SearchService:
    def __init__(self):
        self.content_collection = "document_contents"
        self.documents_collection = "documents"
        self.qdrant_collection = "document_chunks"

    async def keyword_search(self, req: SearchRequest) -> KeywordSearchResponse:
        """Ricerca basata su keyword nel contenuto dei documenti"""
        db = get_database()
        
        # Calcola skip per paginazione
        skip = (req.page - 1) * req.limit
        
        # Query MongoDB con regex per ricerca testuale
        query = {"raw_text": {"$regex": req.query, "$options": "i"}}
        
        # Trova i document_id che matchano
        content_cursor = db[self.content_collection].find(query, {"document_id": 1})
        document_ids = [doc["document_id"] for doc in await content_cursor.to_list(None)]
        
        if not document_ids:
            return KeywordSearchResponse(
                query=req.query,
                search_type="keyword",
                total=0,
                page=req.page,
                limit=req.limit,
                documents=[]
            )
        
        # Trova i documenti corrispondenti
        doc_query = {
            "_id": {"$in": document_ids},
            "is_deleted": False
        }
        
        # Count totale
        total = await db[self.documents_collection].count_documents(doc_query)
        
        # Recupera documenti con paginazione
        docs_cursor = db[self.documents_collection].find(doc_query).skip(skip).limit(req.limit)
        documents = await docs_cursor.to_list(None)
        
        # Converti in response model
        doc_responses = [
            DocumentResponse(
                id=str(doc["_id"]),
                title=doc["title"],
                author=doc.get("author"),
                description=doc.get("description"),
                tags=doc.get("tags", []),
                source_type=doc["source_type"],
                source_filename=doc.get("source_filename"),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"]
            )
            for doc in documents
        ]
        
        return KeywordSearchResponse(
            query=req.query,
            search_type="keyword",
            total=total,
            page=req.page,
            limit=req.limit,
            documents=doc_responses
        )

    async def vector_search(self, req: SearchRequest) -> VectorSearchResponse:
        """Ricerca vettoriale usando Qdrant"""
        client = get_qdrant_client()
        db = get_database()
        
        # Genera embedding per la query
        query_embedding = generate_embedding(req.query)
        
        # Filtro per escludere chunks eliminati
        search_filter = Filter(
            must=[FieldCondition(key="is_deleted", match=MatchValue(value=False))]
        )
        
        try:
            # Ricerca vettoriale in Qdrant - senza offset, usa solo limit
            search_result = await client.search(
                collection_name=self.qdrant_collection,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=req.limit * req.page  # Prende più risultati per simulare paginazione
            )
            
            # Implementa paginazione manualmente
            start_idx = (req.page - 1) * req.limit
            end_idx = start_idx + req.limit
            paginated_results = search_result[start_idx:end_idx]
            
        except Exception as e:
            # Se la collection non esiste o altro errore, ritorna vuoto
            return VectorSearchResponse(
                query=req.query,
                search_type="vector",
                total=0,
                page=req.page,
                limit=req.limit,
                chunks=[],
                documents=[]
            )
        
        # Converti risultati in ChunkSearchResult
        chunks = [
            ChunkSearchResult(
                chunk_id=str(point.id),
                document_id=point.payload["document_id"],
                text=point.payload["text"],
                index=point.payload["index"],
                score=point.score,
                metadata={k: v for k, v in point.payload.items() 
                         if k not in ["document_id", "text", "index", "is_deleted"]}
            )
            for point in paginated_results
        ]
        
        # Estrai document_ids unici
        document_ids = list(set(chunk.document_id for chunk in chunks))
        
        # Recupera documenti correlati
        documents = []
        if document_ids:
            docs_cursor = db[self.documents_collection].find({
                "_id": {"$in": [ObjectId(doc_id) for doc_id in document_ids]},
                "is_deleted": False
            })
            docs = await docs_cursor.to_list(None)
            
            documents = [
                DocumentResponse(
                    id=str(doc["_id"]),
                    title=doc["title"],
                    author=doc.get("author"),
                    description=doc.get("description"),
                    tags=doc.get("tags", []),
                    source_type=doc["source_type"],
                    source_filename=doc.get("source_filename"),
                    created_at=doc["created_at"],
                    updated_at=doc["updated_at"]
                )
                for doc in docs
            ]
        
        return VectorSearchResponse(
            query=req.query,
            search_type="vector",
            total=len(search_result),  # Totale risultati trovati
            page=req.page,
            limit=req.limit,
            chunks=chunks,
            documents=documents
        )

    async def hybrid_search(self, req: SearchRequest):
        """Ricerca ibrida - non implementata"""
        raise NotImplementedError("Hybrid search not implemented")

search_service = SearchService()