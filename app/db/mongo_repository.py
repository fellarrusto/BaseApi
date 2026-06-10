from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.base_repository import BaseRepository

class MongoRepository(BaseRepository):

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.collection = db[collection_name]

    async def find_one(self, id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(id):
            return None
        return await self.collection.find_one({"_id": ObjectId(id)})

    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one(filters)

    async def find_many(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        return await cursor.to_list(length=limit)

    async def count(self, filters: Dict[str, Any]) -> int:
        return await self.collection.count_documents(filters)

    async def exists(self, filters: Dict[str, Any]) -> bool:
        return await self.collection.count_documents(filters, limit=1) > 0

    async def insert_one(self, data: Dict[str, Any]) -> str:
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def insert_many(self, data: List[Dict[str, Any]]) -> List[str]:
        result = await self.collection.insert_many(data)
        return [str(inserted_id) for inserted_id in result.inserted_ids]

    async def update_one(self, id: str, data: Dict[str, Any]) -> bool:
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": data}
        )
        return result.modified_count > 0

    async def update_many(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        result = await self.collection.update_many(filters, {"$set": data})
        return result.modified_count

    async def delete_one(self, id: str) -> bool:
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def delete_many(self, filters: Dict[str, Any]) -> int:
        result = await self.collection.delete_many(filters)
        return result.deleted_count
