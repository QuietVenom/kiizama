from datetime import timezone
from typing import Any

from kiizama_scrape_core.ig_scraper.jobs import (
    ensure_job_indexes,
)
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings

MongoDocument = dict[str, Any]
MongoCollection = AsyncCollection[MongoDocument]
MongoDatabase = AsyncDatabase[MongoDocument]

_client: AsyncMongoClient[MongoDocument] | None = None


def get_mongo_client() -> AsyncMongoClient[MongoDocument]:
    global _client
    mongodb_url = settings.MONGODB_URL
    if not mongodb_url:
        raise RuntimeError("MONGODB_URL is not configured.")
    if _client is None:
        _client = AsyncMongoClient(
            mongodb_url,
            tz_aware=True,
            tzinfo=timezone.utc,
        )
    return _client


def get_mongo_kiizama_ig() -> MongoDatabase:
    client = get_mongo_client()
    return client[settings.MONGODB_KIIZAMA_IG]


async def _dedupe_profiles_by_username(
    profiles: MongoCollection, chunk_size: int = 2000
) -> int:
    pipeline: list[dict[str, Any]] = [
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


async def ensure_indexes(database: MongoDatabase) -> None:
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
    await ensure_job_indexes(database.get_collection("ig_scrape_jobs"))


async def close_mongo_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
