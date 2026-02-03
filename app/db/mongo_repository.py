from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.base_repository import BaseRepository

class MongoRepository(BaseRepository):
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.collection = db[collection_name]
        
    async def find_one(self, id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"id": id})
    
    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one(filters)
    
    async def find_many(
        self, 
        filters: Dict[str, Any], 
        limit: int = 100, 
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def insert_one(self, data: Dict[str, Any]) -> str:
        await self.collection.insert_one(data)
        return str(data["_id"])
    
    async def update_one(self, id: str, data: Dict[str, Any]) -> bool:
        result = await self.collection.update_one(
            {"id": id}, 
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete_one(self, id: str) -> bool:
        result = await self.collection.delete_one({"id": id})
        return result.deleted_count > 0