from __future__ import annotations

from collections.abc import Callable
from typing import cast

from kiizama_scrape_core.redis import RedisClient, create_redis_client

from app.core.config import settings

_client: RedisClient | None = None
_client_resolver: Callable[[], RedisClient] | None = None


def configure_redis_client_resolver(
    resolver: Callable[[], RedisClient] | None,
) -> None:
    global _client_resolver
    _client_resolver = resolver


def get_redis_client() -> RedisClient:
    global _client
    if _client_resolver is not None:
        return _client_resolver()

    redis_url = settings._resolved_redis_url()
    if not redis_url:
        raise RuntimeError("REDIS_URL is not configured.")

    if _client is None:
        _client = cast(RedisClient, create_redis_client(redis_url))
    return _client


async def close_redis_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


__all__ = [
    "RedisClient",
    "create_redis_client",
    "configure_redis_client_resolver",
    "get_redis_client",
    "close_redis_client",
]
