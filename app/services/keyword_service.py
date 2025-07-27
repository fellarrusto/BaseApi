# app/services/keyword_service.py
from typing import List, Optional, Dict, Any
from app.db.database import get_database

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
        query = {field: {"$regex": text, "$options": options}}
        
        return await self.query(
            query=query,
            collection_name=collection_name,
            limit=limit
        )

keyword_service = KeywordService()