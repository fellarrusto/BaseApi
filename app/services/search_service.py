# app/services/search_service.py
from typing import List
from bson import ObjectId
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.services.vector_service import vector_service
from app.services.keyword_service import keyword_service
from app.utils.embedding_utils import generate_embedding
from app.utils.text_utils import clean_text
from app.models.search import (
    HybridChunk, HybridSearchResponse, SearchRequest, KeywordSearchResponse,
    VectorSearchResponse, ChunkSearchResult
)
from app.models.document import DocumentResponse


import logging
logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self.chunks_collection = "document_chunks"
        self.content_collection = "document_contents"
        self.documents_collection = "documents"

    async def keyword_search(self, req: SearchRequest) -> KeywordSearchResponse:
        """Ricerca basata su keyword nel contenuto dei documenti"""
        
        # Query usando keyword_service per trovare i document_id che matchano
        content_results = await keyword_service.text_search(
            text=clean_text(req.query),
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
        query_embedding = generate_embedding(clean_text(req.query))
        
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
        
        
        return VectorSearchResponse(
            query=req.query,
            total=len(chunks),
            limit=req.limit,
            chunks=chunks
        )

    async def hybrid_search(self, req: SearchRequest):
        """Ricerca ibrida - combinazione di keyword e vector search"""
        
        query = clean_text(req.query)
        
        # Query MongoDB con ricerca testuale usando keyword_service
        keyword_results = await keyword_service.text_search(
            text=query,
            field="text",
            collection_name=self.chunks_collection
        )
        
        # Genera embedding e ricerca semantica usando vector_service
        query_embedding = generate_embedding(query)
        semantic_results = await vector_service.query(
            query_vector=query_embedding,
            limit=req.limit
        )
        
        # Converti risultati MongoDB
        keyword_unified = [HybridChunk.from_mongodb(r) for r in keyword_results]

        # Converti risultati Qdrant  
        vector_unified = [HybridChunk.from_qdrant(r) for r in semantic_results]
        
        keyword_unified = keyword_service.get_scores(query, keyword_unified)[:req.limit]
        vector_unified = vector_service.normalize(vector_unified)
        
        print("Keyword results:", len(keyword_unified))
        print("Vector results:", len(vector_unified))
        

        # Unisci e ordina
        all_chunks = keyword_unified + vector_unified
        all_chunks.sort(key=lambda x: x.score or 0, reverse=True)
        
        total = len(all_chunks)
        # Applica il limite dalla richiesta
        all_chunks = all_chunks[:req.limit*2]
        
        return HybridSearchResponse(
            query=req.query,
            total=total,
            limit=req.limit,
            chunks=all_chunks
        )

search_service = SearchService()