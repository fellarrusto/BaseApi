from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseRepository(ABC):
    
    @abstractmethod
    async def find_one(self, id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def find_many(
        self, 
        filters: Dict[str, Any], 
        limit: int = 100, 
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def insert_one(self, data: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    async def update_one(self, id: str, data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def delete_one(self, id: str) -> bool:
        pass