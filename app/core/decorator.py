from functools import wraps
from fastapi import HTTPException, Request
from datetime import datetime
import time
import inspect
from app.services.log_service import log_service
from app.models.log import AuditLogInDB

def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": type(e).__name__,
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
    return wrapper

def audit_log(method: str = "UNKNOWN", metadata: dict = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            error_info = None
            result = None
            
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                status = "error"
                error_info = str(e)

            duration = (time.time() - start_time) * 1000
            
            log_metadata = metadata or {}
            if error_info:
                log_metadata["error"] = error_info
            
            log_entry = AuditLogInDB(
                action=func.__name__,
                endpoint=f"/{func.__name__}",
                method=method,
                status=status,
                duration_ms=duration,
                metadata=log_metadata
            )
            
            await log_service.save_log(log_entry)
            
            if status == "error":
                raise
            
            return result
        return wrapper
    return decorator