from typing import Any

import pytest

from app.core.config import settings
from app.features.user_events.repository import (
    UserEventsRepository,
    build_user_events_stream_key,
)
from app.features.user_events.schemas import UserEventEnvelope


def _build_envelope(notification_id: str = "notification-1") -> UserEventEnvelope:
    return UserEventEnvelope(
        topic="jobs",
        source="backend",
        kind="job.completed",
        notification_id=notification_id,
        payload={"job_id": "job-1"},
    )


@pytest.mark.anyio
async def test_publish_event_with_dedupe_writes_single_stream_entry(
    redis_client: Any,
) -> None:
    # Arrange
    repository = UserEventsRepository(redis_provider=lambda: redis_client)
    envelope = _build_envelope()

    # Act
    first_event_id, first_published = await repository.publish_event(
        user_id="user-1",
        event_name="job.completed",
        envelope=envelope,
        dedupe_key="events:dedupe:user-1:job-1",
        dedupe_ttl_seconds=60,
    )
    second_event_id, second_published = await repository.publish_event(
        user_id="user-1",
        event_name="job.completed",
        envelope=envelope,
        dedupe_key="events:dedupe:user-1:job-1",
        dedupe_ttl_seconds=60,
    )
    entries = await repository.read_events(
        user_id="user-1",
        cursor="0-0",
        block_ms=1,
        count=10,
    )

    # Assert
    assert first_published is True
    assert second_published is False
    assert second_event_id == first_event_id
    assert len(entries) == 1
    assert entries[0].event_name == "job.completed"
    assert entries[0].notification_id == "notification-1"
    parsed_envelope = UserEventEnvelope.model_validate_json(entries[0].envelope_json)
    assert parsed_envelope.notification_id == "notification-1"
    assert parsed_envelope.payload == {"job_id": "job-1"}
    stream_ttl = await redis_client.ttl(build_user_events_stream_key("user-1"))
    assert 0 < stream_ttl <= settings.USER_EVENTS_STREAM_TTL_SECONDS
    assert await redis_client.ttl("events:dedupe:user-1:job-1") == 60


@pytest.mark.anyio
async def test_publish_event_without_dedupe_sets_stream_ttl(
    redis_client: Any,
) -> None:
    # Arrange
    repository = UserEventsRepository(redis_provider=lambda: redis_client)

    # Act
    await repository.publish_event(
        user_id="user-without-dedupe",
        event_name="job.completed",
        envelope=_build_envelope(),
    )

    # Assert
    stream_ttl = await redis_client.ttl(
        build_user_events_stream_key("user-without-dedupe")
    )
    assert 0 < stream_ttl <= settings.USER_EVENTS_STREAM_TTL_SECONDS


@pytest.mark.anyio
async def test_publish_event_trims_stream_to_configured_maxlen(
    redis_client: Any,
) -> None:
    # Arrange
    repository = UserEventsRepository(redis_provider=lambda: redis_client)
    stream_key = build_user_events_stream_key("user-trimmed")
    first_event_id: str | None = None

    # Act
    for index in range(settings.USER_EVENTS_STREAM_MAXLEN + 1):
        event_id, _published = await repository.publish_event(
            user_id="user-trimmed",
            event_name="job.completed",
            envelope=_build_envelope(notification_id=f"notification-{index}"),
        )
        if first_event_id is None:
            first_event_id = event_id

    # Assert
    assert await redis_client.xlen(stream_key) == settings.USER_EVENTS_STREAM_MAXLEN
    remaining_entries = await repository.read_events(
        user_id="user-trimmed",
        cursor="0-0",
        block_ms=1,
        count=settings.USER_EVENTS_STREAM_MAXLEN + 1,
    )
    assert first_event_id is not None
    assert first_event_id not in {entry.event_id for entry in remaining_entries}


@pytest.mark.anyio
async def test_delete_user_stream_removes_only_target_user_stream(
    redis_client: Any,
) -> None:
    # Arrange
    repository = UserEventsRepository(redis_provider=lambda: redis_client)
    await repository.publish_event(
        user_id="deleted-user",
        event_name="job.completed",
        envelope=_build_envelope(notification_id="deleted-notification"),
    )
    await repository.publish_event(
        user_id="kept-user",
        event_name="job.completed",
        envelope=_build_envelope(notification_id="kept-notification"),
    )

    # Act
    await repository.delete_user_stream(user_id="deleted-user")

    # Assert
    assert await redis_client.exists(build_user_events_stream_key("deleted-user")) == 0
    assert await redis_client.exists(build_user_events_stream_key("kept-user")) == 1
