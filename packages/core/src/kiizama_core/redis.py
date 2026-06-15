from __future__ import annotations

from typing import Any, cast

from redis.asyncio import Redis

RedisClient = Any


def create_redis_client(redis_url: str) -> Redis:
    return cast(
        Redis,
        Redis.from_url(
            redis_url,
            decode_responses=True,
            health_check_interval=30,
        ),
    )


__all__ = ["RedisClient", "create_redis_client"]
