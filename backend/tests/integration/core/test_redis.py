from typing import Any

import pytest


@pytest.mark.anyio
async def test_redis_fixture_real_client_ping_and_round_trip(redis_client: Any) -> None:
    assert await redis_client.ping() is True

    await redis_client.set("p2:core:redis", "ok")

    assert await redis_client.get("p2:core:redis") == "ok"
