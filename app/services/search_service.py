# app/services/search_service.py
from typing import List
from bson import ObjectId
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.services.vector_service import vector_service
from app.services.keyword_service import keyword_service
from app.utils.embedding_utils import generate_embedding
from app.models.search import (
    SearchRequest, KeywordSearchResponse,
    VectorSearchResponse, ChunkSearchResult
)
from app.models.document import DocumentResponse

import logging
logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self.content_collection = "document_contents"
        self.documents_collection = "documents"

    async def keyword_search(self, req: SearchRequest) -> KeywordSearchResponse:
        """Ricerca basata su keyword nel contenuto dei documenti"""
        
        # Query usando keyword_service per trovare i document_id che matchano
        content_results = await keyword_service.text_search(
            text=req.query,
            field="raw_text",
            collection_name=self.content_collection
        )
        
        document_ids = [doc["document_id"] for doc in content_results]
        
        if not document_ids:
            return KeywordSearchResponse(
                query=req.query,
                search_type="keyword",
                total=0,
                page=1,
                limit=req.limit,
                documents=[]
            )
        
        # Trova i documenti corrispondenti usando keyword_service
        documents = await keyword_service.query(
            query={
                "_id": {"$in": document_ids},
                "is_deleted": False
            },
            collection_name=self.documents_collection,
            limit=req.limit
        )
        
        # Converti in response model
        doc_responses = [DocumentResponse.from_dict(doc) for doc in documents]
        
        return KeywordSearchResponse(
            query=req.query,
            search_type="keyword",
            total=len(doc_responses),
            page=1,
            limit=req.limit,
            documents=doc_responses
        )

    async def vector_search(self, req: SearchRequest) -> VectorSearchResponse:
        """Ricerca vettoriale usando VectorService"""
        
        # Genera embedding per la query
        query_embedding = generate_embedding(req.query)
        
        # Filtro per escludere chunks eliminati
        search_filter = Filter(
            must=[FieldCondition(key="is_deleted", match=MatchValue(value=False))]
        )
        
        # Ricerca vettoriale usando vector_service
        search_result = await vector_service.query(
            query_vector=query_embedding,
            limit=req.limit,
            filters=search_filter
        )
        
        if not search_result:
            return VectorSearchResponse(
                query=req.query,
                search_type="vector",
                total=0,
                page=1,
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
            for point in search_result
        ]
        
        # Estrai document_ids unici
        document_ids = list(set(chunk.document_id for chunk in chunks))
        
        # Recupera documenti correlati usando keyword_service
        documents = []
        if document_ids:
            docs = await keyword_service.query(
                query={
                    "_id": {"$in": [ObjectId(doc_id) for doc_id in document_ids]},
                    "is_deleted": False
                },
                collection_name=self.documents_collection
            )
            
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
            total=len(chunks),
            page=1,
            limit=req.limit,
            chunks=chunks,
            documents=documents
        )

    async def hybrid_search(self, req: SearchRequest):
        """Ricerca ibrida - combinazione di keyword e vector search"""
        
        # Query MongoDB con ricerca testuale usando keyword_service
        keyword_results = await keyword_service.query(
            query={
                "$or": [
                    {"metadata.title": {"$regex": req.query, "$options": "i"}},
                    {"text": {"$regex": req.query, "$options": "i"}}
                ]
            },
            collection_name=self.content_collection
        )
        
        # Genera embedding e ricerca semantica usando vector_service
        query_embedding = generate_embedding(req.query)
        semantic_results = await vector_service.query(
            query_vector=query_embedding,
            limit=50
        )
        
        print("Keyword results:", len(keyword_results))
        print("Semantic results:", len(semantic_results))
        
        raise NotImplementedError("Hybrid search not implemented")

search_service = SearchService()