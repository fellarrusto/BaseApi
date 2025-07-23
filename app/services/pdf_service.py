import PyPDF2
import io
from typing import Dict, Any, List
from fastapi import UploadFile
from app.models.chunk import DocumentChunk

class PDFService:
    
    def __init__(self):
        self.chunk_size = 1000  # caratteri per chunk
        self.chunk_overlap = 200  # overlap tra chunk
    
    async def extract_text_from_pdf(self, file: UploadFile) -> str:
        """Estrae il testo da un file PDF"""
        try:
            content = await file.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    async def extract_metadata_from_pdf(self, file: UploadFile) -> Dict[str, Any]:
        """Estrae metadati dal PDF"""
        try:
            # Reset file pointer per leggere di nuovo
            await file.seek(0)
            content = await file.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            
            metadata = {"pdf_pages": len(pdf_reader.pages)}
            
            if pdf_reader.metadata:
                metadata.update({
                    "pdf_title": pdf_reader.metadata.get("/Title", ""),
                    "pdf_author": pdf_reader.metadata.get("/Author", ""),
                    "pdf_subject": pdf_reader.metadata.get("/Subject", ""),
                    "pdf_creator": pdf_reader.metadata.get("/Creator", ""),
                    "pdf_producer": pdf_reader.metadata.get("/Producer", "")
                })
            
            return metadata
        except Exception as e:
            return {"pdf_pages": 0, "error": f"Error extracting metadata: {str(e)}"}
    
    async def chunk_pdf_by_pages(self, file: UploadFile, chunk_size: int = None, chunk_overlap: int = None) -> List[DocumentChunk]:
        """Estrae chunk di testo pagina per pagina con metadati"""
        try:
            full_text = await self.extract_text_from_pdf(file)
            
            doc_metadata = await self.extract_metadata_from_pdf(file)
            
            return self.chunk_text_by_pages(full_text, doc_metadata, file.filename, chunk_size, chunk_overlap)
            
        except Exception as e:
            raise Exception(f"Error chunking PDF: {str(e)}")
    
    def chunk_text_by_pages(self, text: str, doc_metadata: Dict[str, Any], filename: str, chunk_size: int = None, chunk_overlap: int = None) -> List[DocumentChunk]:
        """Divide un testo in chunk con metadati"""
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        chunks = self._split_text_into_chunks(text, chunk_size, chunk_overlap)
        
        result = []
        for idx, chunk_text in enumerate(chunks):
            chunk_metadata = {
                **doc_metadata,
                "filename": filename,
                "total_chunks": len(chunks),
                "chunk_length": len(chunk_text)
            }
            
            result.append(DocumentChunk(
                page_number=1,  # Non abbiamo info pagina dal testo integrale
                chunk_text=chunk_text,
                chunk_index=idx,
                metadata=chunk_metadata
            ))
        
        return result
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Divide un testo in chunk con overlap"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end >= len(text):
                break
            
            start = end - overlap
        
        return chunks

pdf_service = PDFService()