from functools import wraps
from fastapi import HTTPException
from datetime import datetime

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