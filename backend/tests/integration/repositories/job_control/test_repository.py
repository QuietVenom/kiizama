import json
from datetime import UTC, datetime
from typing import Any

import pytest

from app.features.job_control.keys import (
    build_consumer_group,
    build_lease_key,
    build_queue_key,
    build_state_key,
)
from app.features.job_control.repository import JobControlRepository
from app.features.job_control.schemas import JobQueueSpec, QueuedJobMessage

SPEC = JobQueueSpec(
    domain="test-jobs",
    state_ttl_seconds=60,
    queue_maxlen=100,
)


def _repository(redis: Any) -> JobControlRepository:
    return JobControlRepository(spec=SPEC, redis_provider=lambda: redis)


def _message(job_id: str = "job-1") -> QueuedJobMessage:
    return QueuedJobMessage(
        job_id=job_id,
        owner_user_id="user-1",
        created_at=datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
        expires_at=datetime(2099, 3, 15, 12, 0, tzinfo=UTC),
        payload={"usernames": ["creator_one"], "headless": True},
    )


@pytest.mark.anyio
async def test_enqueue_job_writes_state_and_stream_entry(redis_client: Any) -> None:
    repository = _repository(redis_client)
    message = _message()
    expires_at = message.expires_at
    assert expires_at is not None

    await repository.enqueue_job(message)

    state = await redis_client.hgetall(build_state_key(SPEC, message.job_id))
    assert state["status"] == "queued"
    assert state["attempts"] == "0"
    assert state["updated_at"] == message.created_at.isoformat()
    assert state["expires_at"] == expires_at.isoformat()

    entries = await redis_client.xread({build_queue_key(SPEC): "0-0"}, count=1)
    fields = entries[0][1][0][1]
    assert fields["job_id"] == message.job_id
    assert fields["owner_user_id"] == message.owner_user_id
    assert fields["expires_at"] == expires_at.isoformat()
    assert json.loads(fields["payload"]) == message.payload


@pytest.mark.anyio
async def test_claim_renew_and_release_lease_respect_ownership(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    message = _message()
    now = message.created_at

    await repository.enqueue_job(message)

    acquired = await repository.claim_lease(
        message.job_id,
        lease_token="worker-1",
        lease_seconds=30,
        now=now,
    )
    not_acquired = await repository.claim_lease(
        message.job_id,
        lease_token="worker-2",
        lease_seconds=30,
        now=now,
    )
    running = await repository.write_running_state(
        message.job_id,
        worker_id="worker-1",
        lease_seconds=30,
        now=now,
    )
    wrong_renewal = await repository.renew_lease(
        message.job_id,
        lease_token="worker-2",
        lease_seconds=30,
        now=now,
    )
    renewed = await repository.renew_lease(
        message.job_id,
        lease_token="worker-1",
        lease_seconds=30,
        now=datetime(2026, 3, 14, 12, 1, tzinfo=UTC),
    )
    wrong_release = await repository.release_lease(
        message.job_id, lease_token="worker-2"
    )
    released = await repository.release_lease(message.job_id, lease_token="worker-1")

    assert acquired.owned is True
    assert not_acquired.owned is False
    assert running.attempts == 1
    assert running.started_at == now
    assert wrong_renewal.owned is False
    assert renewed.owned is True
    assert renewed.leased_until == datetime(2026, 3, 14, 12, 1, 30, tzinfo=UTC)
    state = await repository.read_state(message.job_id)
    assert state is not None
    assert state.worker_id == "worker-1"
    assert state.started_at == now
    assert state.heartbeat_at == datetime(2026, 3, 14, 12, 1, tzinfo=UTC)
    assert wrong_release.owned is False
    assert released.owned is True
    assert await redis_client.get(build_lease_key(SPEC, message.job_id)) is None


@pytest.mark.anyio
async def test_read_new_and_reclaimed_messages_return_typed_messages(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    message = _message()
    expires_at = message.expires_at
    assert expires_at is not None
    queue_key = build_queue_key(SPEC)

    await redis_client.xgroup_create(
        queue_key, build_consumer_group(SPEC), id="0", mkstream=True
    )
    await repository.enqueue_job(message)

    new_messages = await repository.read_new_messages(
        worker_id="worker-1", count=1, block_ms=1
    )
    reclaimed_messages = await repository.read_reclaimed_messages(
        worker_id="worker-2",
        min_idle_time_ms=0,
        count=10,
    )

    assert len(new_messages) == 1
    assert new_messages[0].job_id == message.job_id
    assert new_messages[0].message_id is not None
    assert new_messages[0].expires_at == expires_at
    assert len(reclaimed_messages) == 1
    assert reclaimed_messages[0].job_id == message.job_id
    assert reclaimed_messages[0].payload == message.payload
    assert reclaimed_messages[0].expires_at == expires_at


@pytest.mark.anyio
async def test_ack_message_removes_stream_entry(redis_client: Any) -> None:
    repository = _repository(redis_client)
    message = _message()
    queue_key = build_queue_key(SPEC)

    await redis_client.xgroup_create(
        queue_key, build_consumer_group(SPEC), id="0", mkstream=True
    )
    await repository.enqueue_job(message)
    new_messages = await repository.read_new_messages(
        worker_id="worker-1", count=1, block_ms=1
    )

    await repository.ack_message(new_messages[0].message_id or "")

    assert await redis_client.xlen(queue_key) == 0
    assert (
        await redis_client.xpending_range(
            queue_key, build_consumer_group(SPEC), "-", "+", 10
        )
        == []
    )


@pytest.mark.anyio
async def test_claim_terminal_state_accepts_first_terminal(redis_client: Any) -> None:
    repository = _repository(redis_client)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=UTC)

    await repository.enqueue_job(message)

    decision = await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=1,
        worker_id="worker-1",
        completed_at=completed_at,
        notification_id="job:job-1:terminal",
    )

    assert decision.decision == "accepted_new"
    assert decision.status == "done"
    assert decision.completed_at == completed_at
    assert decision.terminal_event_id is None

    state = await repository.complete_terminal_state(
        message.job_id,
        terminal_event_id="1-0",
    )

    assert state is not None
    assert state.status == "done"
    assert state.attempts == 1
    assert state.worker_id == "worker-1"
    assert state.completed_at == completed_at
    assert state.notification_id == "job:job-1:terminal"
    assert state.terminal_event_id == "1-0"


@pytest.mark.anyio
async def test_claim_terminal_state_returns_duplicate_for_same_terminal(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=UTC)

    await repository.enqueue_job(message)
    await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=1,
        worker_id="worker-1",
        completed_at=completed_at,
        notification_id="job:job-1:terminal",
    )
    await repository.complete_terminal_state(
        message.job_id,
        terminal_event_id="1-0",
    )

    decision = await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=2,
        worker_id="worker-2",
        completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=UTC),
        notification_id="job:job-1:terminal:retry",
    )

    assert decision.decision == "duplicate"
    assert decision.status == "done"
    assert decision.attempts == 1
    assert decision.worker_id == "worker-1"
    assert decision.completed_at == completed_at
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id == "1-0"


@pytest.mark.anyio
async def test_claim_terminal_state_returns_pending_for_same_terminal_without_event_id(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=UTC)

    await repository.enqueue_job(message)
    await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=1,
        worker_id="worker-1",
        completed_at=completed_at,
        notification_id="job:job-1:terminal",
    )

    decision = await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=2,
        worker_id="worker-2",
        completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=UTC),
        notification_id="job:job-1:terminal:retry",
    )

    assert decision.decision == "accepted_pending"
    assert decision.status == "done"
    assert decision.attempts == 1
    assert decision.worker_id == "worker-1"
    assert decision.completed_at == completed_at
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id is None


@pytest.mark.anyio
async def test_claim_terminal_state_rejects_conflicting_terminal_after_done(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=UTC)

    await repository.enqueue_job(message)
    await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=1,
        worker_id="worker-1",
        completed_at=completed_at,
        notification_id="job:job-1:terminal",
    )
    await repository.complete_terminal_state(
        message.job_id,
        terminal_event_id="1-0",
    )

    decision = await repository.claim_terminal_state(
        message.job_id,
        status="failed",
        attempt=2,
        worker_id="worker-2",
        completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=UTC),
        notification_id="job:job-1:terminal:failed",
    )

    assert decision.decision == "conflict"
    assert decision.status == "done"
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id == "1-0"


@pytest.mark.anyio
async def test_claim_terminal_state_rejects_conflicting_terminal_after_failed(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=UTC)

    await repository.enqueue_job(message)
    await repository.claim_terminal_state(
        message.job_id,
        status="failed",
        attempt=1,
        worker_id="worker-1",
        completed_at=completed_at,
        notification_id="job:job-1:terminal",
    )
    await repository.complete_terminal_state(
        message.job_id,
        terminal_event_id="1-0",
    )

    decision = await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=2,
        worker_id="worker-2",
        completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=UTC),
        notification_id="job:job-1:terminal:done",
    )

    assert decision.decision == "conflict"
    assert decision.status == "failed"
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id == "1-0"


@pytest.mark.anyio
async def test_state_ttl_is_capped_by_job_expiration_and_terminal_expire(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=UTC)
    state_key = build_state_key(SPEC, message.job_id)

    await repository.enqueue_job(message)

    initial_ttl = await redis_client.ttl(state_key)
    assert initial_ttl > 0

    await repository.claim_terminal_state(
        message.job_id,
        status="done",
        attempt=1,
        worker_id="worker-1",
        completed_at=completed_at,
        notification_id="job:job-1:terminal",
    )
    await repository.complete_terminal_state(
        message.job_id,
        terminal_event_id="1-0",
    )
    assert await redis_client.ttl(state_key) > 0

    await repository.expire_state(message.job_id)

    ttl = await redis_client.ttl(state_key)
    assert ttl > 0
    assert ttl <= SPEC.state_ttl_seconds
    state = await repository.read_state(message.job_id)
    assert state is not None
    assert state.status == "done"
    assert state.started_at is None
    assert state.completed_at == completed_at
    assert state.notification_id == "job:job-1:terminal"
    assert state.terminal_event_id == "1-0"
