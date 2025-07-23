# app/models/search.py
from app.models.book import BookResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SearchResponse(BaseModel):
    books: List[BookResponse]
    total: int
    page: int
    limit: int