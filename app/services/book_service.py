# app/services/book_service.py
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
import re
from app.db.database import get_database
from fastapi import UploadFile
from app.models.book import (
    BookInDB, BookContentInDB, BookCreate, BookFromPDFCreate, BookUpdate, 
    BookResponse, BookWithContentResponse, SearchResponse
)
from app.services.pdf_service import pdf_service

class BookService:
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
    
    async def create_book(self, book_data: BookCreate) -> BookResponse:
        """Crea un nuovo libro con eventuale contenuto"""
        db = get_database()
        
        # Crea il libro
        book = BookInDB(
            title=book_data.title,
            author=book_data.author,
            isbn=book_data.isbn,
            description=book_data.description,
            tags=book_data.tags or []
        )
        
        result = await db[self.books_collection].insert_one(book.dict(by_alias=True))
        book_id = result.inserted_id
        
        # Se c'è contenuto raw, lo salva
        if book_data.raw_text:
            content = BookContentInDB(
                book_id=book_id,
                content_type="raw",
                raw_text=book_data.raw_text
            )
            await db[self.content_collection].insert_one(content.dict(by_alias=True))
        
        created_book = await db[self.books_collection].find_one({"_id": book_id})
    async def create_book_from_pdf(self, file: UploadFile, book_data: BookFromPDFCreate) -> BookResponse:
        """Crea un libro da un file PDF"""
        db = get_database()
        
        try:
            # Estrae testo dal PDF
            raw_text = await pdf_service.extract_text_from_pdf(file)
            
            # Estrae metadati dal PDF (file pointer viene resettato nel service)
            pdf_metadata = await pdf_service.extract_metadata_from_pdf(file)
            
            # Usa i metadati del PDF se non forniti
            title = book_data.title or pdf_metadata.get("pdf_title") or file.filename or "Untitled"
            author = book_data.author or pdf_metadata.get("pdf_author")
            
            # Crea il libro
            book = BookInDB(
                title=title,
                author=author,
                isbn=book_data.isbn,
                description=book_data.description,
                tags=book_data.tags or []
            )
            
            result = await db[self.books_collection].insert_one(book.dict(by_alias=True))
            book_id = result.inserted_id
            
            # Salva il contenuto raw con metadati PDF
            content_metadata = {
                "source": "pdf",
                "filename": file.filename,
                **pdf_metadata
            }
            
            content = BookContentInDB(
                book_id=book_id,
                content_type="raw",
                raw_text=raw_text,
                metadata=content_metadata
            )
            await db[self.content_collection].insert_one(content.dict(by_alias=True))
            
            created_book = await db[self.books_collection].find_one({"_id": book_id})
            return self._book_to_response(created_book)
            
        except Exception as e:
            raise Exception(f"Error creating book from PDF: {str(e)}")
    
    async def get_book(self, book_id: str, include_content: bool = False) -> Optional[BookWithContentResponse]:
        """Recupera un libro per ID"""
        db = get_database()
        
        if not ObjectId.is_valid(book_id):
            return None
            
        book = await db[self.books_collection].find_one({
            "_id": ObjectId(book_id),
            "is_deleted": False
        })
        
        if not book:
            return None
        
        response_data = {
            "id": str(book["_id"]),
            "title": book["title"],
            "author": book.get("author"),
            "isbn": book.get("isbn"),
            "description": book.get("description"),
            "tags": book.get("tags", []),
            "created_at": book["created_at"],
            "updated_at": book["updated_at"]
        }
        
        if include_content:
            content = await db[self.content_collection].find_one({
                "book_id": ObjectId(book_id),
                "content_type": "raw"
            })
            response_data["raw_text"] = content.get("raw_text") if content else None
        
        return BookWithContentResponse(**response_data)
    
    async def update_book(self, book_id: str, book_data: BookUpdate) -> Optional[BookResponse]:
        """Aggiorna un libro"""
        db = get_database()
        
        if not ObjectId.is_valid(book_id):
            return None
        
        update_data = {k: v for k, v in book_data.dict().items() if v is not None}
        if not update_data:
            return await self.get_book(book_id)
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = await db[self.books_collection].update_one(
            {"_id": ObjectId(book_id), "is_deleted": False},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return None
        
        return await self.get_book(book_id)
    
    async def delete_book(self, book_id: str) -> bool:
        """Soft delete di un libro"""
        db = get_database()
        
        if not ObjectId.is_valid(book_id):
            return False
        
        result = await db[self.books_collection].update_one(
            {"_id": ObjectId(book_id), "is_deleted": False},
            {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
        )
        
        return result.matched_count > 0
    
    async def search_books(self, keyword: str, page: int = 1, limit: int = 10) -> SearchResponse:
        """Ricerca libri per keyword"""
        db = get_database()
        
        # Regex case-insensitive per ricerca in title, author, description
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
        
        # Count totale
        total = await db[self.books_collection].count_documents(query)
        
        # Documenti paginati
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
    
    async def list_books(self, page: int = 1, limit: int = 10) -> SearchResponse:
        """Lista tutti i libri"""
        db = get_database()
        
        query = {"is_deleted": False}
        
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
    
    async def bulk_create_books_from_pdf(self, files: List[UploadFile], tags: List[str] = None) -> List[BookResponse]:
        """Crea multipli libri da file PDF in batch"""
        db = get_database()
        created_books = []
        
        for file in files:
            try:
                # Estrae testo dal PDF
                raw_text = await pdf_service.extract_text_from_pdf(file)
                
                # Estrae metadati dal PDF
                pdf_metadata = await pdf_service.extract_metadata_from_pdf(file)
                
                # Usa metadati del PDF o filename come fallback
                title = pdf_metadata.get("pdf_title") or file.filename or "Untitled"
                author = pdf_metadata.get("pdf_author")
                
                # Crea il libro
                book = BookInDB(
                    title=title,
                    author=author,
                    tags=tags or []
                )
                
                result = await db[self.books_collection].insert_one(book.dict(by_alias=True))
                book_id = result.inserted_id
                
                # Salva contenuto raw
                content_metadata = {
                    "source": "pdf_bulk",
                    "filename": file.filename,
                    **pdf_metadata
                }
                
                content = BookContentInDB(
                    book_id=book_id,
                    content_type="raw",
                    raw_text=raw_text,
                    metadata=content_metadata
                )
                await db[self.content_collection].insert_one(content.dict(by_alias=True))
                
                # Recupera libro creato
                created_book = await db[self.books_collection].find_one({"_id": book_id})
                created_books.append(self._book_to_response(created_book))
                
            except Exception as e:
                # In caso di errore su un file, continua con gli altri
                # Potresti decidere di fare un rollback completo o continuare
                print(f"Error processing {file.filename}: {str(e)}")
                continue
        
        return created_books

book_service = BookService()