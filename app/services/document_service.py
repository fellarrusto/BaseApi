# app/services/document_service.py
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime
from fastapi import UploadFile

from app.db.database import get_database
from app.models.document import (
    DocumentInDB, DocumentContentInDB, DocumentCreate, DocumentUpdate,
    DocumentResponse, DocumentDetailResponse, DocumentsResponse
)
from app.models.chunk import ChunkWithEmbedding
from app.utils import pdf_utils, chunking_utils, embedding_utils
from app.services.vector_service import vector_service

class DocumentService:
    def __init__(self):
        self.documents_collection = "documents"
        self.content_collection = "document_contents"
        self.chunks_collection = "document_chunks"
    
    async def create_document_from_pdf(self, file: UploadFile, document_data: DocumentCreate) -> DocumentResponse:
        """Crea documento da PDF"""
        
        text = await pdf_utils.extract_text(file)
        metadata = await pdf_utils.extract_metadata(file)
        # Usa metadati PDF se non forniti
        doc_data = DocumentCreate(
            title=document_data.title or metadata.get("title") or file.filename,
            author=document_data.author or metadata.get("author"),
            description=document_data.description,
            tags=document_data.tags,
            raw_text=text
        )
        
        metadata["source_filename"] = file.filename
        return await self._process_document_creation(text, metadata, doc_data, "pdf", file.filename)
    
    async def create_document_from_text(self, document_data: DocumentCreate) -> DocumentResponse:
        """Crea documento da testo raw"""
        if not document_data.raw_text:
            raise ValueError("raw_text is required for text document creation")
        
        if not document_data.title:
            raise ValueError("title is required for text document creation")
        
        return await self._process_document_creation(
            document_data.raw_text, 
            {}, 
            document_data, 
            "text", 
            None
        )
    
    async def get_document(self, document_id: str, include_content: bool = False) -> Optional[DocumentDetailResponse]:
        """Recupera documento per ID"""
        db = get_database()
        
        if not ObjectId.is_valid(document_id):
            return None
        
        doc = await db[self.documents_collection].find_one({
            "_id": ObjectId(document_id),
            "is_deleted": False
        })
        
        if not doc:
            return None
        
        response = DocumentDetailResponse(
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
        
        if include_content:
            content = await db[self.content_collection].find_one({"document_id": ObjectId(document_id)})
            response.raw_text = content.get("raw_text") if content else None
        
        return response
    
    async def update_document(self, document_id: str, file: Optional[UploadFile], document_data: DocumentUpdate) -> Optional[DocumentResponse]:
        """Aggiorna documento (elimina e ricrea)"""
        # Verifica che esista
        existing = await self.get_document(document_id)
        if not existing:
            return None
        
        # Elimina vecchio
        await self._delete_document_completely(document_id)
        
        # Ricrea con nuovi dati
        create_data = DocumentCreate(
            title=document_data.title or existing.title,
            author=document_data.author or existing.author,
            description=document_data.description or existing.description,
            tags=document_data.tags if document_data.tags is not None else existing.tags
        )
        
        if file:
            return await self.create_document_from_pdf(file, create_data)
        else:
            # Recupera testo esistente se non fornito nuovo file
            content = await self._get_document_content(document_id)
            create_data.raw_text = content
            return await self.create_document_from_text(create_data)
    
    async def delete_document(self, document_id: str) -> bool:
        """Elimina documento (hard delete)"""
        if not ObjectId.is_valid(document_id):
            return False
        
        return await self._delete_document_completely(document_id)
    
    async def deactivate_document(self, document_id: str) -> bool:
        """Soft delete documento"""
        db = get_database()
        
        if not ObjectId.is_valid(document_id):
            return False
        
        # Update flag in MongoDB
        result = await db[self.documents_collection].update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count > 0:
            # Update flag in Qdrant
            await vector_service.update_chunks_deleted_flag(document_id, True)
            return True
        
        return False
    
    async def list_documents(self, page: int = 1, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> DocumentsResponse:
        """Lista documenti con paginazione"""
        db = get_database()
        
        query = {"is_deleted": False}
        if filters:
            query.update(filters)
        
        total = await db[self.documents_collection].count_documents(query)
        skip = (page - 1) * limit
        
        cursor = db[self.documents_collection].find(query).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        
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
        
        return DocumentsResponse(
            documents=documents,
            total=total,
            page=page,
            limit=limit
        )
    
    # ===================== PRIVATE METHODS =====================
    
    async def _process_document_creation(
        self, 
        text: str, 
        metadata: Dict[str, Any], 
        document_data: DocumentCreate, 
        source_type: str,
        source_filename: Optional[str]
    ) -> DocumentResponse:
        """Processo comune di creazione documento"""
        try:
            print(f"[PROCESS] Starting document creation - Title: {document_data.title}, Source: {source_type}")
            db = get_database()
            
            doc = DocumentInDB(
                title=document_data.title,
                author=document_data.author,
                description=document_data.description,
                tags=document_data.tags or [],
                source_type=source_type,
                source_filename=source_filename
            )
            
            result = await db[self.documents_collection].insert_one(doc.dict(by_alias=True))
            document_id = str(result.inserted_id)
            print(f"[MONGODB] Document created with ID: {document_id}")
            
            content = DocumentContentInDB(
                document_id=result.inserted_id,
                raw_text=text,
                metadata=metadata or {}
            )
            await db[self.content_collection].insert_one(content.dict(by_alias=True))
            print(f"[MONGODB] Content saved - Text length: {len(text)} chars")
            
            # Crea chunks base
            chunks = chunking_utils.create_chunks(text, metadata or {})
            print(f"[CHUNKING] Created {len(chunks)} chunks")
            
            # Salva chunks in MongoDB e ottieni gli ID
            chunk_docs = []
            for chunk in chunks:
                chunk_dict = chunk.dict(by_alias=True)
                chunk_dict["document_id"] = result.inserted_id
                chunk_result = await db[self.chunks_collection].insert_one(chunk_dict)
                chunk_docs.append({
                    "chunk_id": str(chunk_result.inserted_id),
                    "chunk": chunk
                })
            
            print(f"[MONGODB] Saved {len(chunk_docs)} chunks to database")
            
            if chunk_docs:
                print(f"[EMBEDDING] Generating embeddings for {len(chunk_docs)} chunks...")
                texts = [item["chunk"].text for item in chunk_docs]
                embeddings = []
                for i, t in enumerate(texts):
                    emb = embedding_utils.generate_embeddings([t])[0]
                    embeddings.append(emb)
                    print(f"[EMBEDDING] {i+1}/{len(texts)} generated")
                
                # Crea chunks con embedding includendo l'ID MongoDB
                chunks_with_embeddings = []
                for i, item in enumerate(chunk_docs):
                    chunk = item["chunk"]
                    chunk_id = item["chunk_id"]
                    
                    # Aggiungi chunk_id ai metadati
                    enhanced_metadata = chunk.metadata.copy()
                    enhanced_metadata["chunk_id"] = chunk_id
                    
                    chunk_with_embedding = ChunkWithEmbedding(
                        text=chunk.text,
                        index=chunk.index,
                        metadata=enhanced_metadata,
                        embedding=embeddings[i],
                        document_id=document_id
                    )
                    chunks_with_embeddings.append(chunk_with_embedding)
                
                print(f"[QDRANT] Inserting {len(chunks_with_embeddings)} chunks with MongoDB IDs...")
                await vector_service.insert_chunks(chunks_with_embeddings, document_id)
                print(f"[QDRANT] Chunks inserted successfully")
            
            created_doc = await db[self.documents_collection].find_one({"_id": result.inserted_id})
            print(f"[COMPLETE] Document creation completed for: {created_doc['title']}")
            
            return DocumentResponse(
                id=document_id,
                title=created_doc["title"],
                author=created_doc.get("author"),
                description=created_doc.get("description"),
                tags=created_doc.get("tags", []),
                source_type=created_doc["source_type"],
                source_filename=created_doc.get("source_filename"),
                created_at=created_doc["created_at"],
                updated_at=created_doc["updated_at"]
            )
            
        except Exception as e:
            print(f"[ERROR] Document creation failed: {str(e)}")
            raise Exception(f"Document creation failed: {str(e)}")

    
    async def _delete_document_completely(self, document_id: str) -> bool:
        """Elimina completamente documento da MongoDB e Qdrant"""
        db = get_database()
        
        # Elimina da MongoDB
        result = await db[self.documents_collection].delete_one({"_id": ObjectId(document_id)})
        await db[self.content_collection].delete_one({"document_id": ObjectId(document_id)})
        await db[self.chunks_collection].delete_many({"document_id": ObjectId(document_id)})
        
        # Elimina da Qdrant
        await vector_service.delete_document_chunks(document_id)
        
        return result.deleted_count > 0
    
    async def _get_document_content(self, document_id: str) -> Optional[str]:
        """Recupera contenuto raw di un documento"""
        db = get_database()
        content = await db[self.content_collection].find_one({"document_id": ObjectId(document_id)})
        return content.get("raw_text") if content else None

document_service = DocumentService()