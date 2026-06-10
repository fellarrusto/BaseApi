from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class BaseRepository(ABC):
    """
    Abstract data-access contract.

    Services must depend on this interface only, never on a concrete
    database driver. Documents are plain dicts; ids are strings.
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
        pass

    @abstractmethod
    async def update_many(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    async def delete_one(self, id: str) -> bool:
        pass

    @abstractmethod
    async def delete_many(self, filters: Dict[str, Any]) -> int:
        pass
