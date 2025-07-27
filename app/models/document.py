# app/models/document.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.base import PyObjectId

class DocumentInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_type: str = "text"  # "pdf" or "text"
    source_filename: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DocumentContentInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    document_id: PyObjectId
    raw_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DocumentCreate(BaseModel):
    title: Optional[str] = None  # Opzionale per supportare estrazione da PDF
    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None  # Per creazione da testo

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class DocumentResponse(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_type: str
    source_filename: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_dict(cls, doc: dict) -> "DocumentResponse":
        """Factory method per creare DocumentResponse da documento MongoDB"""
        return cls(
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
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class DocumentDetailResponse(DocumentResponse):
    raw_text: Optional[str] = None

class DocumentsResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    limit: int