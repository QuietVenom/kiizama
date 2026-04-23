from typing import Any

import pytest

from app.core.config import settings
from app.core.redis import create_redis_client


@pytest.fixture
async def redis_client() -> Any:
    redis_url = settings._resolved_redis_url()
    if redis_url is None:
        raise RuntimeError("REDIS_URL is not configured.")

    client = create_redis_client(redis_url)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()
