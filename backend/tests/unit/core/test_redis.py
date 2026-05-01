import pytest

from app.core import redis as redis_core


class FakeRedisClient:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def reset_redis_client_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redis_core, "_client", None)
    monkeypatch.setattr(redis_core, "_client_resolver", None)


def test_get_redis_client_uses_configured_resolver() -> None:
    fake = FakeRedisClient()
    redis_core.configure_redis_client_resolver(lambda: fake)

    assert redis_core.get_redis_client() is fake


def test_get_redis_client_without_url_raises_runtime_error(monkeypatch) -> None:
    monkeypatch.setattr(redis_core.settings, "_resolved_redis_url", lambda: None)

    with pytest.raises(RuntimeError, match="REDIS_URL is not configured"):
        redis_core.get_redis_client()


def test_get_redis_client_reuses_singleton_and_close_resets(monkeypatch) -> None:
    created: list[FakeRedisClient] = []

    def create_client(_url: str) -> FakeRedisClient:
        client = FakeRedisClient()
        created.append(client)
        return client

    monkeypatch.setattr(
        redis_core.settings,
        "_resolved_redis_url",
        lambda: "redis://localhost:6379/0",
    )
    monkeypatch.setattr(redis_core, "create_redis_client", create_client)

    first = redis_core.get_redis_client()
    second = redis_core.get_redis_client()

    assert first is second
    assert len(created) == 1


@pytest.mark.anyio
async def test_close_redis_client_closes_cached_client(monkeypatch) -> None:
    fake = FakeRedisClient()
    monkeypatch.setattr(
        redis_core.settings,
        "_resolved_redis_url",
        lambda: "redis://localhost:6379/0",
    )
    monkeypatch.setattr(redis_core, "create_redis_client", lambda _url: fake)

    assert redis_core.get_redis_client() is fake

    await redis_core.close_redis_client()

    assert fake.closed is True
