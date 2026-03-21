from __future__ import annotations

from kiizama_scrape_core.redis import RedisClient, create_redis_client

from scrape_worker.config import get_settings

_client: RedisClient | None = None


def get_worker_redis_client() -> RedisClient:
    global _client
    if _client is None:
        _client = create_redis_client(get_settings().redis_url)
    return _client


async def close_worker_redis_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


__all__ = ["close_worker_redis_client", "get_worker_redis_client"]
