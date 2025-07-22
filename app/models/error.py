from pydantic import BaseModel
from datetime import datetime

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime = datetime.now()
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}