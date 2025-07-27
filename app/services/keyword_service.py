# app/services/keyword_service.py
import re
from rank_bm25 import BM25Okapi
from typing import List, Optional, Dict, Any
from app.db.database import get_database
from app.models.search import HybridChunk

class KeywordService:
    def __init__(self):
        pass
    
    async def query(self, 
                   query: Dict[str, Any],
                   collection_name: str,
                   limit: Optional[int] = None,
                   skip: Optional[int] = None,
                   projection: Optional[Dict] = None) -> List[Dict]:
        """Query MongoDB generica"""
        db = get_database()
        cursor = db[collection_name].find(query, projection)
        
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
            
        return await cursor.to_list(None)
    
    async def count(self, query: Dict[str, Any], collection_name: str) -> int:
        """Conta documenti che matchano la query"""
        db = get_database()
        return await db[collection_name].count_documents(query)
    
    async def text_search(self, 
                         text: str, 
                         field: str,
                         collection_name: str,
                         case_sensitive: bool = False,
                         limit: Optional[int] = None) -> List[Dict]:
        """Ricerca testuale con regex su un campo specifico"""
        options = "" if case_sensitive else "i"
        keywords = text.split()
        pattern = "(" + "|".join(map(re.escape, keywords)) + ")"
        query = { field: {"$regex": pattern, "$options": options} }
        return await self.query(query=query, collection_name=collection_name, limit=limit)
        
    def get_scores(self, query: str, chunks: List[HybridChunk]) -> List[HybridChunk]:
        tokenized_corpus = [chunk.text.split(" ") for chunk in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.split(" ")
        scores = bm25.get_scores(tokenized_query)
        min_score, max_score = min(scores), max(scores)
        norm_scores = [(s - min_score) / (max_score - min_score) if max_score > min_score else 0.0 for s in scores]
        for chunk, score in zip(chunks, norm_scores):
            chunk.score = float(score)
        return sorted(chunks, key=lambda c: c.score, reverse=True)

keyword_service = KeywordService()