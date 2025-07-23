# app/api/book_router.py
from app.models.chunk import ChunkResponse
from app.services.pdf_service import pdf_service
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, status
from typing import Optional, List
from app.core.decorator import handle_errors, audit_log
from app.models.book import (
    BookCreate, BookFromPDFCreate, BookUpdate, BookResponse, 
    BookWithContentResponse, BooksResponse
)
from app.services.book_service import book_service

router = APIRouter(prefix="/books", tags=["books"])

@router.post("/upload-pdf", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
@handle_errors
@audit_log(method="POST", metadata={"service": "books", "action": "upload_pdf"})
async def create_book_from_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    title: Optional[str] = Form(None, description="Book title (auto-detected if not provided)"),
    author: Optional[str] = Form(None, description="Book author (auto-detected if not provided)"),
    isbn: Optional[str] = Form(None, description="Book ISBN"),
    description: Optional[str] = Form(None, description="Book description"),
    tags: Optional[str] = Form(None, description="Comma-separated tags")
) -> BookResponse:
    """Crea un libro caricando un file PDF"""
    
    # Valida che sia un PDF
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    # Converte tags da stringa a lista
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    book_data = BookFromPDFCreate(
        title=title,
        author=author,
        isbn=isbn,
        description=description,
        tags=tags_list
    )
    
    return await book_service.create_book_from_pdf(file, book_data)

@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
@handle_errors
@audit_log(method="POST", metadata={"service": "books"})
async def create_book(book_data: BookCreate) -> BookResponse:
    """Crea un nuovo libro"""
    return await book_service.create_book(book_data)

@router.get("/{book_id}", response_model=BookWithContentResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="GET", metadata={"service": "books"})
async def get_book(
    book_id: str, 
    include_content: bool = Query(False, description="Include raw text content")
) -> BookWithContentResponse:
    """Recupera un libro per ID"""
    book = await book_service.get_book(book_id, include_content)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return book

@router.put("/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="PUT", metadata={"service": "books"})
async def update_book(book_id: str, book_data: BookUpdate) -> BookResponse:
    """Aggiorna un libro"""
    book = await book_service.update_book(book_id, book_data)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return book

@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_errors
@audit_log(method="DELETE", metadata={"service": "books"})
async def delete_book(book_id: str):
    """Elimina un libro (soft delete)"""
    success = await book_service.delete_book(book_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

@router.get("/", response_model=BooksResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="GET", metadata={"service": "books"})
async def list_books(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
) -> BooksResponse:
    """Lista tutti i libri"""
    return await book_service.list_books(page=page, limit=limit)


@router.post("/bulk-upload-pdf", response_model=List[BookResponse], status_code=status.HTTP_201_CREATED)
@handle_errors
@audit_log(method="POST", metadata={"service": "books", "action": "bulk_upload_pdf"})
async def bulk_create_books_from_pdf(
    files: List[UploadFile] = File(..., description="Multiple PDF files to upload"),
    tags: Optional[str] = Form(None, description="Comma-separated tags for all books")
) -> List[BookResponse]:
    """Crea più libri caricando multipli file PDF"""
    
    # Valida che tutti i file siano PDF
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} must be a PDF"
            )
    
    # Converte tags da stringa a lista
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    return await book_service.bulk_create_books_from_pdf(files, tags_list)