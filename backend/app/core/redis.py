from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from redis.asyncio import Redis

from app.core.config import settings

RedisClient = Any

_client: RedisClient | None = None
_client_resolver: Callable[[], RedisClient] | None = None


def create_redis_client(redis_url: str) -> Redis:
    return cast(
        Redis,
        Redis.from_url(
            redis_url,
            decode_responses=True,
            health_check_interval=30,
        ),
    )


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
        _client = create_redis_client(redis_url)
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
