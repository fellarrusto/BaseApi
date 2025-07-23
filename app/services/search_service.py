from typing import Optional, List
from bson import ObjectId
from datetime import datetime
import re
from app.db.database import get_database
from fastapi import UploadFile
from app.models.book import (
    BookResponse
)
from app.models.search import (
    SearchResponse
)
from app.services.pdf_service import pdf_service

class SearchService:
    def __init__(self):
        self.books_collection = "books"
        self.content_collection = "book_contents"

    def _book_to_response(self, book_doc: dict) -> BookResponse:
        """Converte documento MongoDB in BookResponse"""
        return BookResponse(
            id=str(book_doc["_id"]),
            title=book_doc["title"],
            author=book_doc.get("author"),
            isbn=book_doc.get("isbn"),
            description=book_doc.get("description"),
            tags=book_doc.get("tags", []),
            created_at=book_doc["created_at"],
            updated_at=book_doc["updated_at"]
        )
    
    
    async def search_books(self, keyword: str, page: int = 1, limit: int = 10) -> SearchResponse:
        """Ricerca libri per keyword"""
        db = get_database()
        
        regex_pattern = re.compile(keyword, re.IGNORECASE)
        
        query = {
            "is_deleted": False,
            "$or": [
                {"title": {"$regex": regex_pattern}},
                {"author": {"$regex": regex_pattern}},
                {"description": {"$regex": regex_pattern}},
                {"tags": {"$in": [regex_pattern]}}
            ]
        }
        
        total = await db[self.books_collection].count_documents(query)
        skip = (page - 1) * limit
        cursor = db[self.books_collection].find(query).skip(skip).limit(limit)
        books = await cursor.to_list(length=limit)
        
        book_responses = [self._book_to_response(book) for book in books]
        
        return SearchResponse(
            books=book_responses,
            total=total,
            page=page,
            limit=limit
        )

search_service = SearchService()