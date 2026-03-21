from __future__ import annotations

from collections.abc import Callable

from kiizama_scrape_core.job_control.repository import (
    JobControlRepository as CoreJobControlRepository,
)
from kiizama_scrape_core.job_control.repository import (
    JobControlUnavailableError,
)

from app.core.redis import RedisClient, get_redis_client

from .schemas import JobQueueSpec


class JobControlRepository(CoreJobControlRepository):
    def __init__(
        self,
        *,
        spec: JobQueueSpec,
        redis_provider: Callable[[], RedisClient] = get_redis_client,
    ) -> None:
        super().__init__(spec=spec, redis_provider=redis_provider)


__all__ = ["JobControlRepository", "JobControlUnavailableError"]
