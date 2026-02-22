from bson import ObjectId
from pymongo import ReturnDocument

from app.schemas import ProfileSnapshot, UpdateProfileSnapshot


def _normalize_snapshot_ids(snapshot_ids: list[str] | None):
    if snapshot_ids is None:
        return None
    if not snapshot_ids:
        return []
    return [ObjectId(snapshot_id) for snapshot_id in snapshot_ids]


async def create_profile_snapshot(collection, snapshot: ProfileSnapshot):
    doc = snapshot.model_dump(by_alias=True, exclude_none=True)
    result = await collection.insert_one(doc)
    return await collection.find_one({"_id": result.inserted_id})


async def get_profile_snapshot(collection, snapshot_id: str):
    return await collection.find_one({"_id": ObjectId(snapshot_id)})


async def get_profile_snapshot_by_profile_id(collection, profile_id: str):
    return await collection.find_one({"profile_id": profile_id})


async def list_profile_snapshots(
    collection,
    skip: int = 0,
    limit: int = 100,
    snapshot_ids: list[str] | None = None,
):
    ids = _normalize_snapshot_ids(snapshot_ids)
    if ids == []:
        return []
    filters = {"_id": {"$in": ids}} if ids else {}
    cursor = collection.find(filters).skip(skip).limit(limit)
    return [doc async for doc in cursor]


async def list_profile_snapshots_full(
    collection,
    skip: int = 0,
    limit: int = 100,
    usernames: list[str] | None = None,
):
    if usernames is not None and not usernames:
        return []
    pipeline: list[dict] = [
        {
            "$addFields": {
                "profile_oid": {
                    "$convert": {
                        "input": "$profile_id",
                        "to": "objectId",
                        "onError": None,
                        "onNull": None,
                    }
                },
                "metrics_oid": {
                    "$convert": {
                        "input": "$metrics_id",
                        "to": "objectId",
                        "onError": None,
                        "onNull": None,
                    }
                },
                "post_oids": {
                    "$map": {
                        "input": {"$ifNull": ["$post_ids", []]},
                        "as": "pid",
                        "in": {
                            "$convert": {
                                "input": "$$pid",
                                "to": "objectId",
                                "onError": None,
                                "onNull": None,
                            }
                        },
                    }
                },
                "reel_oids": {
                    "$map": {
                        "input": {"$ifNull": ["$reel_ids", []]},
                        "as": "rid",
                        "in": {
                            "$convert": {
                                "input": "$$rid",
                                "to": "objectId",
                                "onError": None,
                                "onNull": None,
                            }
                        },
                    }
                },
            }
        },
    ]
    if not usernames:
        pipeline.extend([{"$skip": skip}, {"$limit": limit}])

    pipeline.extend(
        [
            {
                "$lookup": {
                    "from": "profiles",
                    "localField": "profile_oid",
                    "foreignField": "_id",
                    "as": "profile",
                }
            },
            {"$addFields": {"profile": {"$first": "$profile"}}},
        ]
    )

    if usernames:
        pipeline.append({"$match": {"profile.username": {"$in": usernames}}})
        pipeline.extend([{"$skip": skip}, {"$limit": limit}])

    pipeline.extend(
        [
            {
                "$lookup": {
                    "from": "posts",
                    "let": {"post_oids": "$post_oids"},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$_id", "$$post_oids"]}}}
                    ],
                    "as": "posts",
                }
            },
            {
                "$lookup": {
                    "from": "reels",
                    "let": {"reel_oids": "$reel_oids"},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$_id", "$$reel_oids"]}}}
                    ],
                    "as": "reels",
                }
            },
            {
                "$lookup": {
                    "from": "metrics",
                    "localField": "metrics_oid",
                    "foreignField": "_id",
                    "as": "metrics",
                }
            },
            {"$addFields": {"metrics": {"$first": "$metrics"}}},
            {
                "$project": {
                    "profile_oid": 0,
                    "metrics_oid": 0,
                    "post_oids": 0,
                    "reel_oids": 0,
                }
            },
        ]
    )
    pipeline = [stage for stage in pipeline if stage]
    cursor = await collection.aggregate(pipeline)
    return [doc async for doc in cursor]


async def update_profile_snapshot(
    collection, snapshot_id: str, patch: UpdateProfileSnapshot
):
    updates = patch.model_dump(exclude_unset=True)
    if not updates:
        return await collection.find_one({"_id": ObjectId(snapshot_id)})

    return await collection.find_one_and_update(
        {"_id": ObjectId(snapshot_id)},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )


async def replace_profile_snapshot(
    collection, snapshot_id: str, snapshot: ProfileSnapshot
):
    doc = snapshot.model_dump(by_alias=True, exclude_none=False)
    doc["_id"] = ObjectId(snapshot_id)
    return await collection.find_one_and_replace(
        {"_id": ObjectId(snapshot_id)},
        doc,
        return_document=ReturnDocument.AFTER,
    )


async def delete_profile_snapshot(collection, snapshot_id: str):
    return await collection.find_one_and_delete({"_id": ObjectId(snapshot_id)})
