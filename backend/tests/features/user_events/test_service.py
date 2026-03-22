import asyncio
from typing import Any

import pytest
from fastapi import Request

from app.features.user_events.repository import UserEventsRepository
from app.features.user_events.schemas import UserEventEnvelope, UserStreamEntry
from app.features.user_events.service import UserEventStreamService


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


async def _collect_first(async_iterator: Any) -> Any:
    try:
        return await anext(async_iterator)
    finally:
        await async_iterator.aclose()


class FakeRequest(Request):
    def __init__(self, disconnects: list[bool] | None = None) -> None:
        super().__init__(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/api/v1/events/stream",
                "raw_path": b"/api/v1/events/stream",
                "query_string": b"",
                "headers": [],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
            }
        )
        self._disconnects = disconnects or [False]

    async def is_disconnected(self) -> bool:
        if self._disconnects:
            return self._disconnects.pop(0)
        return False


class FakeUserEventsRepository(UserEventsRepository):
    def __init__(self, batches: list[Any]) -> None:
        self._batches = list(batches)
        self.read_calls: list[str] = []

    def assert_available(self) -> None:
        return None

    async def read_events(
        self,
        *,
        user_id: str,
        cursor: str,
        block_ms: int,
        count: int = 10,
    ) -> list[UserStreamEntry]:
        del user_id, block_ms, count
        self.read_calls.append(cursor)
        if not self._batches:
            return []

        batch = self._batches.pop(0)
        if isinstance(batch, BaseException):
            raise batch
        return batch


def _envelope_json(payload: dict[str, Any] | None = None) -> str:
    return UserEventEnvelope(
        topic="jobs",
        source="ig-scraper",
        kind="terminal",
        notification_id="job:job-1:terminal",
        payload=payload or {"job_id": "job-1", "status": "done"},
    ).model_dump_json()


def test_stream_events_starts_from_dollar_when_last_event_id_is_missing() -> None:
    repository = FakeUserEventsRepository(
        [
            [
                UserStreamEntry(
                    event_id="1-0",
                    event_name="ig-scrape.job.completed",
                    notification_id="job:job-1:terminal",
                    envelope_json=_envelope_json(),
                )
            ]
        ]
    )
    service = UserEventStreamService(repository=repository, read_block_ms=1)

    event = _run(
        _collect_first(
            service.stream_events(
                FakeRequest(),
                user_id="user-1",
                last_event_id=None,
            )
        )
    )

    assert repository.read_calls == ["$"]
    assert event.id == "1-0"
    assert event.data["topic"] == "jobs"
    assert event.data["payload"]["job_id"] == "job-1"


def test_stream_events_replays_from_explicit_last_event_id() -> None:
    repository = FakeUserEventsRepository(
        [
            [
                UserStreamEntry(
                    event_id="2-0",
                    event_name="ig-scrape.job.completed",
                    notification_id="job:job-1:terminal",
                    envelope_json=_envelope_json(),
                )
            ]
        ]
    )
    service = UserEventStreamService(repository=repository, read_block_ms=1)

    event = _run(
        _collect_first(
            service.stream_events(
                FakeRequest(),
                user_id="user-1",
                last_event_id="0-0",
            )
        )
    )

    assert repository.read_calls == ["0-0"]
    assert event.id == "2-0"


def test_stream_events_ignores_malformed_entries_and_keeps_payload_unparsed() -> None:
    repository = FakeUserEventsRepository(
        [
            [
                UserStreamEntry(
                    event_id="1-0",
                    event_name="ig-scrape.job.completed",
                    notification_id="job:job-1:terminal",
                    envelope_json="{not-valid-json",
                ),
                UserStreamEntry(
                    event_id="2-0",
                    event_name="ig-scrape.job.completed",
                    notification_id="job:job-1:terminal",
                    envelope_json=_envelope_json(
                        {
                            "job_id": "job-1",
                            "status": "done",
                            "custom": {"value": 1},
                        }
                    ),
                ),
            ]
        ]
    )
    service = UserEventStreamService(repository=repository, read_block_ms=1)

    event = _run(
        _collect_first(
            service.stream_events(
                FakeRequest(),
                user_id="user-1",
                last_event_id=None,
            )
        )
    )

    assert event.id == "2-0"
    assert event.data["payload"] == {
        "job_id": "job-1",
        "status": "done",
        "custom": {"value": 1},
    }


def test_stream_events_stops_when_request_disconnects() -> None:
    service = UserEventStreamService(
        repository=FakeUserEventsRepository([]),
        read_block_ms=1,
    )
    iterator = service.stream_events(
        FakeRequest([True]),
        user_id="user-1",
        last_event_id=None,
    )

    with pytest.raises(StopAsyncIteration):
        _run(anext(iterator))


def test_stream_events_preserves_cancelled_error() -> None:
    service = UserEventStreamService(
        repository=FakeUserEventsRepository([asyncio.CancelledError()]),
        read_block_ms=1,
    )
    iterator = service.stream_events(
        FakeRequest(),
        user_id="user-1",
        last_event_id=None,
    )

    with pytest.raises(asyncio.CancelledError):
        _run(anext(iterator))
