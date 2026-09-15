from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseStorage(ABC):
    """
    Abstract, database-agnostic storage contract for one collection/table.

    Only entity repositories (app/repositories) may use it. Documents are
    plain dicts; ids are strings. Filters use Mongo-style syntax: equality
    plus $gt, $gte, $lt, $lte, $ne, $in.
    """

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
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def count(self, filters: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    async def exists(self, filters: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def insert_one(self, data: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def insert_many(self, data: List[Dict[str, Any]]) -> List[str]:
        pass

    @abstractmethod
    async def update_one(self, id: str, data: Dict[str, Any]) -> bool:
        """Set the given fields. Returns True if the document exists."""
        pass

    @abstractmethod
    async def update_many(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        """Set the given fields. Returns the number of matched documents."""
        pass

    @abstractmethod
    async def delete_one(self, id: str) -> bool:
        pass

    @abstractmethod
    async def delete_many(self, filters: Dict[str, Any]) -> int:
        pass
