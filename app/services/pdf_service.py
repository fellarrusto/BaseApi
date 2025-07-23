# app/services/pdf_service.py
import PyPDF2
import io
from typing import Dict, Any
from fastapi import UploadFile

class PDFService:
    
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

pdf_service = PDFService()