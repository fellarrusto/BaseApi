# app/models/book.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.base import PyObjectId

class BookInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BookContentInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    book_id: PyObjectId
    content_type: str = "raw"  # raw, page, embedding
    raw_text: Optional[str] = None
    page_number: Optional[int] = None
    metadata: Optional[dict] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    raw_text: Optional[str] = None

class BookFromPDFCreate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class BookResponse(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class BookWithContentResponse(BookResponse):
    raw_text: Optional[str] = None

class SearchResponse(BaseModel):
    books: List[BookResponse]
    total: int
    page: int
    limit: int