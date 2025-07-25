from fastapi import APIRouter, BackgroundTasks, status
from app.core.decorator import handle_errors, audit_log
from app.models.task import (
    TaskTriggerResponse, TaskStatusResponse, SchedulerControlResponse
)
from app.tasks.task_scheduler import task_scheduler

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/process-pdfs", response_model=TaskTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
@handle_errors
@audit_log(method="POST", metadata={"service": "tasks", "action": "process_pdfs"})
async def trigger_pdf_processing(background_tasks: BackgroundTasks) -> TaskTriggerResponse:
    """Triggera elaborazione PDF in background"""
    
    # Avvia task in background
    background_tasks.add_task(task_scheduler.trigger_pdf_processing)
    
    return TaskTriggerResponse(
        status="triggered",
        message="PDF processing started in background"
    )

@router.get("/status", response_model=TaskStatusResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="GET", metadata={"service": "tasks", "action": "status"})
async def get_task_status() -> TaskStatusResponse:
    """Ottieni status dei task"""
    return TaskStatusResponse(
        is_running=task_scheduler.is_running,
        scheduler_active=task_scheduler.current_task is not None and not task_scheduler.current_task.done()
    )

@router.post("/scheduler/start", response_model=SchedulerControlResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="POST", metadata={"service": "tasks", "action": "start_scheduler"})
async def start_scheduler(interval_minutes: int = 30) -> SchedulerControlResponse:
    """Avvia scheduler automatico"""
    result = await task_scheduler.start_scheduled_processing(interval_minutes)
    return SchedulerControlResponse(**result)

@router.post("/scheduler/stop", response_model=SchedulerControlResponse, status_code=status.HTTP_200_OK)
@handle_errors
@audit_log(method="POST", metadata={"service": "tasks", "action": "stop_scheduler"})
async def stop_scheduler() -> SchedulerControlResponse:
    """Ferma scheduler automatico"""
    result = await task_scheduler.stop_scheduled_processing()
    return SchedulerControlResponse(**result)