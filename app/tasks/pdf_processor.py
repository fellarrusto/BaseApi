import os
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings
from app.services.document_service import document_service
from app.models.document import DocumentCreate
from app.services.log_service import log_service
from app.models.log import AuditLogInDB

class PDFProcessor:
    def __init__(self):
        self.inbox_path = Path(settings.PDF_INBOX_PATH)
        self.inbox_path.mkdir(parents=True, exist_ok=True)
    
    async def process_all_pdfs(self) -> Dict[str, Any]:
        """Elabora tutti i PDF nella cartella inbox"""
        pdf_files = list(self.inbox_path.glob("*.pdf"))
        
        if not pdf_files:
            return {
                "status": "completed",
                "message": "No PDF files found in inbox",
                "processed": 0,
                "errors": 0
            }
        
        results = {
            "status": "processing",
            "total_files": len(pdf_files),
            "processed": 0,
            "errors": 0,
            "error_details": []
        }
        
        await self._log_task_start(len(pdf_files))
        
        for pdf_file in pdf_files:
            try:
                await self._process_single_pdf(pdf_file)
                results["processed"] += 1
                print(f"[PDF_PROCESSOR] Successfully processed: {pdf_file.name}")
                
            except Exception as e:
                results["errors"] += 1
                error_msg = f"Failed to process {pdf_file.name}: {str(e)}"
                results["error_details"].append(error_msg)
                print(f"[PDF_PROCESSOR] Error: {error_msg}")
                
                await self._log_error(pdf_file.name, str(e))
        
        results["status"] = "completed"
        await self._log_task_completion(results)
        
        return results
    
    async def _process_single_pdf(self, pdf_path: Path):
        """Elabora un singolo PDF"""
        # Crea UploadFile mock dal file su disco
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        # Simula UploadFile
        class MockUploadFile:
            def __init__(self, filename: str, content: bytes):
                self.filename = filename
                self.content = content
                self._position = 0
            
            async def read(self) -> bytes:
                return self.content
            
            async def seek(self, position: int):
                self._position = position
        
        mock_file = MockUploadFile(pdf_path.name, file_content)
        
        # Crea documento usando il service esistente
        document_data = DocumentCreate(
            title=pdf_path.stem,  # Nome file senza estensione
            tags=["batch_processed"]
        )
        
        await document_service.create_document_from_pdf(mock_file, document_data)
        
        # Elimina file dopo elaborazione riuscita
        pdf_path.unlink()
    
    async def _log_task_start(self, file_count: int):
        """Log inizio task"""
        log_entry = AuditLogInDB(
            action="pdf_batch_processing_start",
            endpoint="/tasks/process-pdfs",
            method="POST",
            status="info",
            metadata={"files_found": file_count}
        )
        await log_service.save_log(log_entry)
    
    async def _log_task_completion(self, results: Dict[str, Any]):
        """Log completamento task"""
        log_entry = AuditLogInDB(
            action="pdf_batch_processing_completed",
            endpoint="/tasks/process-pdfs",
            method="POST",
            status="success" if results["errors"] == 0 else "warning",
            metadata=results
        )
        await log_service.save_log(log_entry)
    
    async def _log_error(self, filename: str, error: str):
        """Log errore specifico"""
        log_entry = AuditLogInDB(
            action="pdf_processing_error",
            endpoint="/tasks/process-pdfs",
            method="POST",
            status="error",
            metadata={"filename": filename, "error": error}
        )
        await log_service.save_log(log_entry)

pdf_processor = PDFProcessor()