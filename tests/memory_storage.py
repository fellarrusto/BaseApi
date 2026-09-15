import copy
from typing import Any, Callable, Dict, List, Optional, Tuple

from bson import ObjectId

from app.db.base_storage import BaseStorage

_OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "$eq": lambda value, expected: value == expected,
    "$ne": lambda value, expected: value != expected,
    "$gt": lambda value, expected: value is not None and value > expected,
    "$gte": lambda value, expected: value is not None and value >= expected,
    "$lt": lambda value, expected: value is not None and value < expected,
    "$lte": lambda value, expected: value is not None and value <= expected,
    "$in": lambda value, expected: value in expected,
}


class MemoryStorage(BaseStorage):
    """In-memory BaseStorage for tests, with the same semantics as MongoStorage."""

    def __init__(self) -> None:
        self.docs: Dict[str, Dict[str, Any]] = {}

    def _matches(self, doc: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            conditions = value.items() if isinstance(value, dict) else [("$eq", value)]
            if not all(_OPERATORS[op](doc.get(key), expected) for op, expected in conditions):
                return False
        return True

    def _select(self, filters: Dict[str, Any], sort: Optional[List[Tuple[str, int]]] = None) -> List[Dict[str, Any]]:
        docs = [doc for doc in self.docs.values() if self._matches(doc, filters)]
        for key, direction in reversed(sort or []):
            docs.sort(key=lambda doc: doc[key], reverse=direction < 0)
        return docs

    async def find_one(self, id: str) -> Optional[Dict[str, Any]]:
        doc = self.docs.get(id) if ObjectId.is_valid(id) else None
        return copy.deepcopy(doc) if doc else None

    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        docs = self._select(filters)
        return copy.deepcopy(docs[0]) if docs else None

    async def find_many(self, filters, limit=100, skip=0, sort=None) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._select(filters, sort)[skip:skip + limit])

    async def count(self, filters: Dict[str, Any]) -> int:
        return len(self._select(filters))

    async def exists(self, filters: Dict[str, Any]) -> bool:
        return await self.count(filters) > 0

    async def insert_one(self, data: Dict[str, Any]) -> str:
        self.docs[str(data["_id"])] = copy.deepcopy(data)
        return str(data["_id"])

    async def insert_many(self, data: List[Dict[str, Any]]) -> List[str]:
        return [await self.insert_one(doc) for doc in data]

    async def update_one(self, id: str, data: Dict[str, Any], where: Optional[Dict[str, Any]] = None) -> bool:
        doc = self.docs.get(id)
        if doc is None or not self._matches(doc, where or {}):
            return False
        doc.update(copy.deepcopy(data))
        return True

    async def update_many(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        docs = self._select(filters)
        for doc in docs:
            doc.update(copy.deepcopy(data))
        return len(docs)

    async def claim_one(self, filters, data, sort=None) -> Optional[Dict[str, Any]]:
        docs = self._select(filters, sort)
        if not docs:
            return None
        docs[0].update(copy.deepcopy(data))
        return copy.deepcopy(docs[0])

    async def ensure_index(self, fields, expire_after_seconds=None) -> None:
        pass  # no indexes in memory

    async def delete_one(self, id: str) -> bool:
        return self.docs.pop(id, None) is not None

    async def delete_many(self, filters: Dict[str, Any]) -> int:
        docs = self._select(filters)
        for doc in docs:
            self.docs.pop(str(doc["_id"]))
        return len(docs)
