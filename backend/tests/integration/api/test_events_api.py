import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator, Coroutine
from typing import Any, cast

from fastapi import Request
from fastapi.sse import ServerSentEvent
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.redis import create_redis_client
from app.features.user_events.repository import (
    UserEventsRepository,
    build_user_events_stream_key,
)
from app.features.user_events.schemas import UserEventEnvelope
from app.features.user_events.service import (
    UserEventStreamService,
    UserEventsUnavailableError,
    get_user_event_stream_service,
)
from app.main import app


def _current_user_id(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> str:
    response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    return str(response.json()["id"])


def _run[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


async def _publish_user_event_for_stream(user_id: str) -> str:
    redis_url = settings._resolved_redis_url()
    if redis_url is None:
        raise RuntimeError("REDIS_URL is not configured.")

    redis = create_redis_client(redis_url)
    try:
        await redis.flushdb()
        repository = UserEventsRepository(redis_provider=lambda: redis)
        envelope = UserEventEnvelope(
            topic="jobs",
            source="backend",
            kind="job.completed",
            notification_id="notification-1",
            payload={"job_id": "job-1", "status": "done"},
        )

        event_id, published = await repository.publish_event(
            user_id=user_id,
            event_name="job.completed",
            envelope=envelope,
        )

        assert published is True
        assert await redis.xlen(build_user_events_stream_key(user_id)) == 1
        return event_id
    finally:
        await redis.aclose()


class StubEventStreamService(UserEventStreamService):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.availability_exception: Exception | None = None

    def assert_available(self) -> None:
        if self.availability_exception is not None:
            raise self.availability_exception

    async def assert_connection_available(self) -> None:
        self.assert_available()

    def stream_events(
        self,
        request: Request,
        *,
        user_id: str,
        last_event_id: str | None,
    ) -> AsyncIterator[ServerSentEvent]:
        del request
        self.calls.append((user_id, last_event_id))

        async def iterator() -> AsyncIterator[ServerSentEvent]:
            yield ServerSentEvent(
                id="1-0",
                event="ig-scrape.job.completed",
                data={
                    "topic": "jobs",
                    "source": "ig-scraper",
                    "kind": "terminal",
                    "notification_id": "job:job-1:terminal",
                    "payload": {"job_id": "job-1"},
                },
            )

        return iterator()


class OneShotEventStreamService(UserEventStreamService):
    def stream_events(
        self,
        request: Request,
        *,
        user_id: str,
        last_event_id: str | None,
    ) -> AsyncIterator[ServerSentEvent]:
        async def iterator() -> AsyncIterator[ServerSentEvent]:
            stream = cast(
                AsyncGenerator[ServerSentEvent, None],
                super(OneShotEventStreamService, self).stream_events(
                    request,
                    user_id=user_id,
                    last_event_id=last_event_id,
                ),
            )
            try:
                yield await anext(stream)
            finally:
                await stream.aclose()

        return iterator()


def test_stream_user_events_requires_authentication(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/events/stream")
    assert response.status_code == 401


def test_stream_user_events_uses_service_and_streams_sse(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubEventStreamService()
    current_user_id = _current_user_id(client, normal_user_token_headers)
    headers = dict(normal_user_token_headers)
    headers["Last-Event-ID"] = "0-0"

    app.dependency_overrides[get_user_event_stream_service] = lambda: service
    try:
        with client.stream(
            "GET",
            f"{settings.API_V1_STR}/events/stream",
            headers=headers,
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["x-accel-buffering"] == "no"

            lines: list[str] = []
            for line in response.iter_lines():
                lines.append(line)
                if line == "":
                    break
    finally:
        app.dependency_overrides.pop(get_user_event_stream_service, None)

    assert service.calls == [(current_user_id, "0-0")]
    assert "event: ig-scrape.job.completed" in lines
    assert "id: 1-0" in lines

    data_lines = [
        line.removeprefix("data: ") for line in lines if line.startswith("data: ")
    ]
    payload = json.loads("\n".join(data_lines))
    assert payload["topic"] == "jobs"
    assert payload["payload"]["job_id"] == "job-1"


def test_stream_user_events_reads_published_redis_event_as_sse(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    current_user_id = _current_user_id(client, normal_user_token_headers)
    event_id = _run(_publish_user_event_for_stream(current_user_id))
    headers = dict(normal_user_token_headers)
    headers["Last-Event-ID"] = "0-0"

    app.dependency_overrides[get_user_event_stream_service] = lambda: (
        OneShotEventStreamService(read_block_ms=1)
    )
    try:
        with client.stream(
            "GET",
            f"{settings.API_V1_STR}/events/stream",
            headers=headers,
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["x-accel-buffering"] == "no"

            lines: list[str] = []
            for line in response.iter_lines():
                lines.append(line)
                if line == "":
                    break
    finally:
        app.dependency_overrides.pop(get_user_event_stream_service, None)

    assert "event: job.completed" in lines
    assert f"id: {event_id}" in lines

    data_lines = [
        line.removeprefix("data: ") for line in lines if line.startswith("data: ")
    ]
    payload = json.loads("\n".join(data_lines))
    assert payload["topic"] == "jobs"
    assert payload["source"] == "backend"
    assert payload["kind"] == "job.completed"
    assert payload["notification_id"] == "notification-1"
    assert payload["payload"] == {"job_id": "job-1", "status": "done"}


def test_stream_user_events_returns_503_when_service_is_unavailable(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubEventStreamService()
    service.availability_exception = UserEventsUnavailableError(
        "Redis is unavailable for user events."
    )

    app.dependency_overrides[get_user_event_stream_service] = lambda: service
    try:
        response = client.get(
            f"{settings.API_V1_STR}/events/stream",
            headers=normal_user_token_headers,
        )
    finally:
        app.dependency_overrides.pop(get_user_event_stream_service, None)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Redis is unavailable for user events.",
        "dependency": "redis",
        "retryable": True,
    }
