from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

from app.db.base_storage import BaseStorage
from app.db.database import get_storage

ModelT = TypeVar("ModelT", bound=BaseModel)


class EntityRepository(Generic[ModelT]):
    """
    Typed data access for one entity: `{Feature}InDB` models in and out.

    Subclasses set `collection` and `model`, and add domain queries
    (e.g. `find_by_email`) built on the protected `_find_*` helpers.
    Filters are Mongo-style and never leave the repository.
    """

    collection: str
    model: Type[ModelT]

    def __init__(self) -> None:
        self._storage_instance: Optional[BaseStorage] = None

    @property
    def _storage(self) -> BaseStorage:
        # Lazy: the database connection only exists after startup
        if self._storage_instance is None:
            self._storage_instance = get_storage(self.collection)
        return self._storage_instance

    async def get_by_id(self, id: str) -> Optional[ModelT]:
        doc = await self._storage.find_one(id)
        return self._to_model(doc) if doc else None

    async def create(self, entity: ModelT) -> ModelT:
        await self._storage.insert_one(entity.model_dump(by_alias=True))
        return entity

    async def update(self, id: str, fields: Dict[str, Any]) -> bool:
        """Set the given fields. Returns False if the entity does not exist."""
        return await self._storage.update_one(id, fields)

    async def delete(self, id: str) -> bool:
        """Returns False if the entity does not exist."""
        return await self._storage.delete_one(id)

    async def _find_one(self, filters: Dict[str, Any]) -> Optional[ModelT]:
        doc = await self._storage.find_one_by(filters)
        return self._to_model(doc) if doc else None

    async def _find_many(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[ModelT]:
        docs = await self._storage.find_many(filters, limit=limit, skip=skip, sort=sort)
        return [self._to_model(doc) for doc in docs]

    async def _count(self, filters: Dict[str, Any]) -> int:
        return await self._storage.count(filters)

    async def _exists(self, filters: Dict[str, Any]) -> bool:
        return await self._storage.exists(filters)

    def _to_model(self, doc: Dict[str, Any]) -> ModelT:
        return self.model.model_validate(doc)
