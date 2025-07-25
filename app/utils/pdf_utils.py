import re
import PyPDF2
import io
from typing import Dict, Any
from fastapi import UploadFile
from app.utils.text_utils import clean_text

async def extract_text(file: UploadFile) -> str:
    """Estrae il testo da un file PDF"""
    content = await file.read()
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
    
    text_pages = [page.extract_text() for page in pdf_reader.pages]
    return clean_text("\n".join(text_pages).strip())

async def extract_metadata(file: UploadFile) -> Dict[str, Any]:
    """Estrae metadati dal PDF"""
    await file.seek(0)
    content = await file.read()
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
    
    metadata = {"pages": len(pdf_reader.pages)}
    
    if pdf_reader.metadata:
        pdf_meta = pdf_reader.metadata
        metadata.update({
            "title": pdf_meta.get("/Title", ""),
            "author": pdf_meta.get("/Author", ""),
            "subject": pdf_meta.get("/Subject", ""),
            "creator": pdf_meta.get("/Creator", "")
        })
    
    return metadata