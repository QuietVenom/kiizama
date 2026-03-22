from __future__ import annotations

from datetime import timezone
from typing import Any

from pymongo import AsyncMongoClient

from scrape_worker.config import get_settings

_client: AsyncMongoClient[dict[str, Any]] | None = None


def get_worker_mongo_client() -> AsyncMongoClient[dict[str, Any]]:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncMongoClient(
            settings.mongodb_url,
            tz_aware=True,
            tzinfo=timezone.utc,
        )
    return _client


def get_worker_mongo_database():
    return get_worker_mongo_client()[get_settings().mongodb_database]


async def close_worker_mongo_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


__all__ = [
    "get_worker_mongo_client",
    "get_worker_mongo_database",
    "close_worker_mongo_client",
]
