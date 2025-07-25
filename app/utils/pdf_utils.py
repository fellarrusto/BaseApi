import re
import PyPDF2
import io
from typing import Dict, Any
from fastapi import UploadFile

def clean_text(text: str) -> str:
    # Rimuove i caratteri di nuova linea e li sostituisce con uno spazio singolo
    cleaned_text = text.replace('\n', ' ').replace('\r', ' ')
    # Rimuove i caratteri speciali (mantenendo lettere, numeri, spazi e punteggiatura specificata)
    cleaned_text = re.sub(r'[^\w\s.,!?;]', '', cleaned_text)
    # Rimuove multipli spazi bianchi consecutivi
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = cleaned_text.lower()
    return cleaned_text

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