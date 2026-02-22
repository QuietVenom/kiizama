from bson import ObjectId
from pymongo import ReturnDocument

from app.schemas import Post, UpdatePost


async def create_post(collection, post: Post):
    doc = post.model_dump(by_alias=True, exclude_none=True)
    result = await collection.insert_one(doc)
    return await collection.find_one({"_id": result.inserted_id})


async def get_post(collection, post_id: str):
    return await collection.find_one({"_id": ObjectId(post_id)})


async def list_posts(collection, skip: int = 0, limit: int = 100):
    cursor = collection.find().skip(skip).limit(limit)
    return [doc async for doc in cursor]


async def update_post(collection, post_id: str, patch: UpdatePost):
    updates = patch.model_dump(exclude_unset=True)
    if not updates:
        return await collection.find_one({"_id": ObjectId(post_id)})

    return await collection.find_one_and_update(
        {"_id": ObjectId(post_id)},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )


async def replace_post(collection, post_id: str, post: Post):
    doc = post.model_dump(by_alias=True, exclude_none=False)
    doc["_id"] = ObjectId(post_id)
    return await collection.find_one_and_replace(
        {"_id": ObjectId(post_id)},
        doc,
        return_document=ReturnDocument.AFTER,
    )


async def delete_post(collection, post_id: str):
    return await collection.find_one_and_delete({"_id": ObjectId(post_id)})
