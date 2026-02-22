from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.schemas import Profile, UpdateProfile


async def create_profile(collection, profile: Profile):
    doc = profile.model_dump(by_alias=True, exclude_none=True, mode="json")
    doc["updated_date"] = datetime.now(timezone.utc)
    try:
        result = await collection.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="ig_id ya existe") from exc
    return await collection.find_one({"_id": result.inserted_id})


async def get_profile(collection, profile_id: str):
    return await collection.find_one({"_id": ObjectId(profile_id)})


async def get_profile_by_username(collection, username: str):
    return await collection.find_one({"username": username})


async def list_profiles(collection, skip: int = 0, limit: int = 100):
    cursor = collection.find().skip(skip).limit(limit)
    return [doc async for doc in cursor]


async def get_profiles_by_usernames(collection, usernames: list[str]):
    cursor = collection.find({"username": {"$in": usernames}})
    return [doc async for doc in cursor]


async def update_profile(collection, profile_id: str, patch: UpdateProfile):
    updates = patch.model_dump(exclude_unset=True, mode="json")
    if not updates:
        return await collection.find_one({"_id": ObjectId(profile_id)})

    updates["updated_date"] = datetime.now(timezone.utc)
    try:
        return await collection.find_one_and_update(
            {"_id": ObjectId(profile_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="ig_id ya existe") from exc


async def replace_profile(collection, profile_id: str, profile: Profile):
    doc = profile.model_dump(by_alias=True, exclude_none=False, mode="json")
    doc["_id"] = ObjectId(profile_id)
    doc["updated_date"] = datetime.now(timezone.utc)
    try:
        return await collection.find_one_and_replace(
            {"_id": ObjectId(profile_id)},
            doc,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="ig_id ya existe") from exc


async def delete_profile(collection, profile_id: str):
    return await collection.find_one_and_delete({"_id": ObjectId(profile_id)})
