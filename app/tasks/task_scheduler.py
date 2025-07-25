import asyncio
from typing import Optional
from datetime import datetime
from app.tasks.pdf_processor import pdf_processor

class TaskScheduler:
    def __init__(self):
        self.is_running = False
        self.current_task: Optional[asyncio.Task] = None
    
    async def trigger_pdf_processing(self):
        """Avvia elaborazione PDF (manuale da API)"""
        if self.is_running:
            return {
                "status": "already_running",
                "message": "PDF processing task is already running"
            }
        
        self.is_running = True
        try:
            results = await pdf_processor.process_all_pdfs()
            return results
        finally:
            self.is_running = False
    
    async def start_scheduled_processing(self, interval_minutes: int = 30):
        """Avvia elaborazione schedulata (opzionale)"""
        if self.current_task and not self.current_task.done():
            return {"status": "scheduler_already_running"}
        
        self.current_task = asyncio.create_task(
            self._scheduled_loop(interval_minutes)
        )
        return {"status": "scheduler_started", "interval_minutes": interval_minutes}
    
    async def stop_scheduled_processing(self):
        """Ferma elaborazione schedulata"""
        if self.current_task:
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
        return {"status": "scheduler_stopped"}
    
    async def _scheduled_loop(self, interval_minutes: int):
        """Loop per elaborazione periodica"""
        while True:
            try:
                if not self.is_running:  # Evita sovrapposizioni
                    await self.trigger_pdf_processing()
                
                await asyncio.sleep(interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[SCHEDULER] Error in scheduled processing: {e}")
                await asyncio.sleep(60)

task_scheduler = TaskScheduler()