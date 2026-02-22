from bson import ObjectId
from pymongo import ReturnDocument

from app.schemas import Reel, UpdateReel


async def create_reel(collection, reel: Reel):
    doc = reel.model_dump(by_alias=True, exclude_none=True)
    result = await collection.insert_one(doc)
    return await collection.find_one({"_id": result.inserted_id})


async def get_reel(collection, reel_id: str):
    return await collection.find_one({"_id": ObjectId(reel_id)})


async def list_reels(collection, skip: int = 0, limit: int = 100):
    cursor = collection.find().skip(skip).limit(limit)
    return [doc async for doc in cursor]


async def update_reel(collection, reel_id: str, patch: UpdateReel):
    updates = patch.model_dump(exclude_unset=True)
    if not updates:
        return await collection.find_one({"_id": ObjectId(reel_id)})

    return await collection.find_one_and_update(
        {"_id": ObjectId(reel_id)},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )


async def replace_reel(collection, reel_id: str, reel: Reel):
    doc = reel.model_dump(by_alias=True, exclude_none=False)
    doc["_id"] = ObjectId(reel_id)
    return await collection.find_one_and_replace(
        {"_id": ObjectId(reel_id)},
        doc,
        return_document=ReturnDocument.AFTER,
    )


async def delete_reel(collection, reel_id: str):
    return await collection.find_one_and_delete({"_id": ObjectId(reel_id)})
