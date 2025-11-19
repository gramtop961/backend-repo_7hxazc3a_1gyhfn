import os
from typing import Any, Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "appdb")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(DATABASE_URL)
        _db = _client[DATABASE_NAME]
    return _db

async def create_document(collection: str, data: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_db()
    now = datetime.utcnow()
    data = {**data, "created_at": now, "updated_at": now}
    result = await db[collection].insert_one(data)
    inserted = await db[collection].find_one({"_id": result.inserted_id})
    if inserted:
        inserted["id"] = str(inserted.pop("_id"))
    return inserted or {}

async def get_documents(collection: str, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = db[collection].find(filter_dict or {}).limit(limit)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return items

async def update_document(collection: str, doc_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from bson import ObjectId
    db = await get_db()
    data["updated_at"] = datetime.utcnow()
    await db[collection].update_one({"_id": ObjectId(doc_id)}, {"$set": data})
    doc = await db[collection].find_one({"_id": ObjectId(doc_id)})
    if doc:
        doc["id"] = str(doc.pop("_id"))
    return doc

async def delete_document(collection: str, doc_id: str) -> bool:
    from bson import ObjectId
    db = await get_db()
    res = await db[collection].delete_one({"_id": ObjectId(doc_id)})
    return res.deleted_count == 1
