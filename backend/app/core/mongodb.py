from datetime import timezone
from typing import Any

from pymongo import AsyncMongoClient

from app.core.config import settings

_client: AsyncMongoClient[dict[str, Any]] | None = None


def get_mongo_client() -> AsyncMongoClient[dict[str, Any]]:
    global _client
    if _client is None:
        _client = AsyncMongoClient(
            settings.MONGODB_URL,
            tz_aware=True,
            tzinfo=timezone.utc,
        )
    return _client


def get_mongo_kiizama_ig():
    client = get_mongo_client()
    return client[settings.MONGODB_KIIZAMA_IG]


async def _dedupe_profiles_by_username(profiles, chunk_size: int = 2000) -> int:
    pipeline = [
        {"$match": {"username": {"$type": "string", "$ne": ""}}},
        {
            "$setWindowFields": {
                "partitionBy": "$username",
                "sortBy": {"updated_date": -1},
                "output": {"rn": {"$documentNumber": {}}},
            }
        },
        {"$match": {"rn": {"$gt": 1}}},
        # Proyectar solo _id desde el inicio
        {"$project": {"_id": 1}},
    ]

    removed = 0
    current_chunk = []

    # Procesar stream directamente sin acumular todo en memoria
    cursor = await profiles.aggregate(pipeline, allowDiskUse=True)
    async for doc in cursor:
        current_chunk.append(doc["_id"])

        if len(current_chunk) >= chunk_size:
            result = await profiles.delete_many({"_id": {"$in": current_chunk}})
            removed += result.deleted_count
            current_chunk = []  # Reset chunk

    # Procesar el último chunk incompleto
    if current_chunk:
        result = await profiles.delete_many({"_id": {"$in": current_chunk}})
        removed += result.deleted_count

    return removed


async def ensure_indexes(database) -> None:
    profiles = database.get_collection("profiles")
    await profiles.create_index(
        [("ig_id", 1)],
        unique=True,
        name="uniq_profiles_ig_id",
    )
    await _dedupe_profiles_by_username(profiles)
    await profiles.create_index(
        [("username", 1)],
        unique=True,
        name="idx_profiles_username",
    )
    profile_snapshots = database.get_collection("profile_snapshots")
    await profile_snapshots.create_index(
        [("profile_id", 1), ("scraped_at", -1)],
        name="idx_profile_snapshots_profile_id_scraped_at",
    )
    ig_credentials = database.get_collection("ig_credentials")
    await ig_credentials.create_index(
        [("login_username", 1)],
        unique=True,
        name="uniq_ig_credentials_login_username",
    )


async def close_mongo_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
