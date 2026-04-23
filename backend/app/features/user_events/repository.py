from __future__ import annotations

from collections.abc import Callable

from kiizama_scrape_core.user_events.repository import (
    UserEventsRepository as CoreUserEventsRepository,
)
from kiizama_scrape_core.user_events.repository import (
    UserEventsUnavailableError,
    build_user_events_stream_key,
)

from app.core.config import settings
from app.core.redis import RedisClient, get_redis_client


class UserEventsRepository(CoreUserEventsRepository):
    def __init__(
        self,
        *,
        redis_provider: Callable[[], RedisClient] = get_redis_client,
    ) -> None:
        super().__init__(
            redis_provider=redis_provider,
            stream_maxlen=settings.USER_EVENTS_STREAM_MAXLEN,
            stream_ttl_seconds=settings.USER_EVENTS_STREAM_TTL_SECONDS,
        )


def get_user_events_repository() -> UserEventsRepository:
    return UserEventsRepository()


__all__ = [
    "UserEventsRepository",
    "UserEventsUnavailableError",
    "build_user_events_stream_key",
    "get_user_events_repository",
]
