# app/api/document_router.py
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, status
from typing import Optional, List
from app.core.decorator import handle_errors, audit_log
from app.models.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, 
    DocumentDetailResponse, DocumentsResponse
)
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload-pdf", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@handle_errors
@audit_log(method="POST", metadata={"service": "documents", "action": "upload_pdf"})
async def create_document_from_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None, description="Comma-separated tags")
) -> DocumentResponse:
    """Crea documento da file PDF"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    # Title sarà determinato dal service se non fornito
    document_data = DocumentCreate(
        title=title or file.filename,  # Usa filename come fallback temporaneo
        author=author,
        description=description,
        tags=tags_list
    )
    
    return await document_service.create_document_from_pdf(file, document_data)

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@handle_errors
@audit_log(method="POST", metadata={"service": "documents"})
async def create_document_from_text(document_data: DocumentCreate) -> DocumentResponse:
    """Crea documento da testo"""
    return await document_service.create_document_from_text(document_data)

# @router.get("/{document_id}", response_model=DocumentDetailResponse)
# @handle_errors
# @audit_log(method="GET", metadata={"service": "documents"})
# async def get_document(
#     document_id: str, 
#     include_content: bool = Query(False)
# ) -> DocumentDetailResponse:
#     """Recupera documento per ID"""
#     document = await document_service.get_document(document_id, include_content)
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
#     return document

# @router.put("/{document_id}", response_model=DocumentResponse)
# @handle_errors
# @audit_log(method="PUT", metadata={"service": "documents"})
# async def update_document(
#     document_id: str,
#     file: Optional[UploadFile] = File(None),
#     title: Optional[str] = Form(None),
#     author: Optional[str] = Form(None),
#     description: Optional[str] = Form(None),
#     tags: Optional[str] = Form(None)
# ) -> DocumentResponse:
#     """Aggiorna documento"""
#     tags_list = [tag.strip() for tag in tags.split(",")] if tags else None
    
#     document_data = DocumentUpdate(
#         title=title,
#         author=author,
#         description=description,
#         tags=tags_list
#     )
    
#     document = await document_service.update_document(document_id, file, document_data)
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
#     return document

# @router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
# @handle_errors
# @audit_log(method="DELETE", metadata={"service": "documents"})
# async def delete_document(document_id: str):
#     """Elimina documento (hard delete)"""
#     success = await document_service.delete_document(document_id)
#     if not success:
#         raise HTTPException(status_code=404, detail="Document not found")

# @router.patch("/{document_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
# @handle_errors
# @audit_log(method="PATCH", metadata={"service": "documents", "action": "deactivate"})
# async def deactivate_document(document_id: str):
#     """Disattiva documento (soft delete)"""
#     success = await document_service.deactivate_document(document_id)
#     if not success:
#         raise HTTPException(status_code=404, detail="Document not found")

# @router.get("/", response_model=DocumentsResponse)
# @handle_errors
# @audit_log(method="GET", metadata={"service": "documents"})
# async def list_documents(
#     page: int = Query(1, ge=1),
#     limit: int = Query(10, ge=1, le=100)
# ) -> DocumentsResponse:
#     """Lista documenti"""
#     return await document_service.list_documents(page=page, limit=limit)