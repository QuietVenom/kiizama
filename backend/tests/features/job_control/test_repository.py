import asyncio
import json
from datetime import datetime, timezone
from typing import Any, cast

import fakeredis.aioredis

from app.features.job_control.keys import (
    build_consumer_group,
    build_lease_key,
    build_queue_key,
    build_state_key,
)
from app.features.job_control.repository import JobControlRepository
from app.features.job_control.schemas import JobQueueSpec, QueuedJobMessage
from app.features.job_control.scripts import (
    LEASE_RELEASE_SCRIPT,
    LEASE_RENEW_SCRIPT,
    TERMINALIZATION_CLAIM_SCRIPT,
)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class EvalFakeRedis:
    def __init__(self) -> None:
        self._redis = cast(
            Any,
            fakeredis.aioredis.FakeRedis(decode_responses=True),
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._redis, name)

    async def eval(self, script: str, numkeys: int, *args: str) -> object:
        del numkeys
        if script == LEASE_RENEW_SCRIPT:
            key, lease_token, ttl_ms = args
            if await self._redis.get(key) == lease_token:
                await self._redis.pexpire(key, int(ttl_ms))
                return 1
            return 0

        if script == LEASE_RELEASE_SCRIPT:
            key, lease_token = args
            if await self._redis.get(key) == lease_token:
                return await self._redis.delete(key)
            return 0

        if script == TERMINALIZATION_CLAIM_SCRIPT:
            (
                state_key,
                status,
                attempt,
                worker_id,
                completed_at,
                notification_id,
            ) = args
            existing_status = await self._redis.hget(state_key, "status")
            existing_attempts = await self._redis.hget(state_key, "attempts")
            existing_worker_id = await self._redis.hget(state_key, "worker_id")
            existing_completed_at = await self._redis.hget(state_key, "completed_at")
            existing_notification_id = await self._redis.hget(
                state_key, "notification_id"
            )
            existing_terminal_event_id = await self._redis.hget(
                state_key, "terminal_event_id"
            )

            if existing_status in {"done", "failed"}:
                if existing_status == status:
                    return [
                        (
                            "duplicate"
                            if existing_terminal_event_id
                            else "accepted_pending"
                        ),
                        existing_status,
                        existing_attempts or "",
                        existing_worker_id or "",
                        existing_completed_at or "",
                        existing_notification_id or "",
                        existing_terminal_event_id or "",
                    ]
                return [
                    "conflict",
                    existing_status,
                    existing_attempts or "",
                    existing_worker_id or "",
                    existing_completed_at or "",
                    existing_notification_id or "",
                    existing_terminal_event_id or "",
                ]

            await self._redis.hset(
                state_key,
                mapping={
                    "status": status,
                    "attempts": attempt,
                    "worker_id": worker_id,
                    "updated_at": completed_at,
                    "completed_at": completed_at,
                    "notification_id": notification_id,
                },
            )
            await self._redis.hdel(
                state_key,
                "terminal_event_id",
                "leased_until",
                "heartbeat_at",
            )
            return [
                "accepted_new",
                status,
                attempt,
                worker_id,
                completed_at,
                notification_id,
                "",
            ]

        raise AssertionError(f"Unexpected Lua script: {script}")


SPEC = JobQueueSpec(
    domain="test-jobs",
    state_ttl_seconds=60,
    queue_maxlen=100,
)


def _repository(redis: EvalFakeRedis) -> JobControlRepository:
    return JobControlRepository(spec=SPEC, redis_provider=lambda: redis)


def _message(job_id: str = "job-1") -> QueuedJobMessage:
    return QueuedJobMessage(
        job_id=job_id,
        owner_user_id="user-1",
        created_at=datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
        expires_at=datetime(2099, 3, 15, 12, 0, tzinfo=timezone.utc),
        payload={"usernames": ["creator_one"], "headless": True},
    )


def test_enqueue_job_writes_state_and_stream_entry() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    expires_at = message.expires_at
    assert expires_at is not None

    _run(repository.enqueue_job(message))

    state = _run(redis.hgetall(build_state_key(SPEC, message.job_id)))
    assert state["status"] == "queued"
    assert state["attempts"] == "0"
    assert state["updated_at"] == message.created_at.isoformat()
    assert state["expires_at"] == expires_at.isoformat()

    entries = _run(redis.xread({build_queue_key(SPEC): "0-0"}, count=1))
    fields = entries[0][1][0][1]
    assert fields["job_id"] == message.job_id
    assert fields["owner_user_id"] == message.owner_user_id
    assert fields["expires_at"] == expires_at.isoformat()
    assert json.loads(fields["payload"]) == message.payload


def test_claim_renew_and_release_lease_respect_ownership() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    now = message.created_at

    _run(repository.enqueue_job(message))

    acquired = _run(
        repository.claim_lease(
            message.job_id,
            lease_token="worker-1",
            lease_seconds=30,
            now=now,
        )
    )
    not_acquired = _run(
        repository.claim_lease(
            message.job_id,
            lease_token="worker-2",
            lease_seconds=30,
            now=now,
        )
    )
    running = _run(
        repository.write_running_state(
            message.job_id,
            worker_id="worker-1",
            lease_seconds=30,
            now=now,
        )
    )
    wrong_renewal = _run(
        repository.renew_lease(
            message.job_id,
            lease_token="worker-2",
            lease_seconds=30,
            now=now,
        )
    )
    renewed = _run(
        repository.renew_lease(
            message.job_id,
            lease_token="worker-1",
            lease_seconds=30,
            now=datetime(2026, 3, 14, 12, 1, tzinfo=timezone.utc),
        )
    )
    wrong_release = _run(
        repository.release_lease(message.job_id, lease_token="worker-2")
    )
    released = _run(repository.release_lease(message.job_id, lease_token="worker-1"))

    assert acquired.owned is True
    assert not_acquired.owned is False
    assert running.attempts == 1
    assert running.started_at == now
    assert wrong_renewal.owned is False
    assert renewed.owned is True
    assert renewed.leased_until == datetime(2026, 3, 14, 12, 1, 30, tzinfo=timezone.utc)
    state = _run(repository.read_state(message.job_id))
    assert state is not None
    assert state.worker_id == "worker-1"
    assert state.started_at == now
    assert state.heartbeat_at == datetime(2026, 3, 14, 12, 1, tzinfo=timezone.utc)
    assert wrong_release.owned is False
    assert released.owned is True
    assert _run(redis.get(build_lease_key(SPEC, message.job_id))) is None


def test_read_new_and_reclaimed_messages_return_typed_messages() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    expires_at = message.expires_at
    assert expires_at is not None
    queue_key = build_queue_key(SPEC)

    _run(
        redis.xgroup_create(
            queue_key, build_consumer_group(SPEC), id="0", mkstream=True
        )
    )
    _run(repository.enqueue_job(message))

    new_messages = _run(
        repository.read_new_messages(worker_id="worker-1", count=1, block_ms=1)
    )
    reclaimed_messages = _run(
        repository.read_reclaimed_messages(
            worker_id="worker-2",
            min_idle_time_ms=0,
            count=10,
        )
    )

    assert len(new_messages) == 1
    assert new_messages[0].job_id == message.job_id
    assert new_messages[0].message_id is not None
    assert new_messages[0].expires_at == expires_at
    assert len(reclaimed_messages) == 1
    assert reclaimed_messages[0].job_id == message.job_id
    assert reclaimed_messages[0].payload == message.payload
    assert reclaimed_messages[0].expires_at == expires_at


def test_ack_message_removes_stream_entry() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    queue_key = build_queue_key(SPEC)

    _run(
        redis.xgroup_create(
            queue_key, build_consumer_group(SPEC), id="0", mkstream=True
        )
    )
    _run(repository.enqueue_job(message))
    new_messages = _run(
        repository.read_new_messages(worker_id="worker-1", count=1, block_ms=1)
    )

    _run(repository.ack_message(new_messages[0].message_id or ""))

    assert _run(redis.xlen(queue_key)) == 0
    assert (
        _run(redis.xpending_range(queue_key, build_consumer_group(SPEC), "-", "+", 10))
        == []
    )


def test_claim_terminal_state_accepts_first_terminal() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc)

    _run(repository.enqueue_job(message))

    decision = _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=1,
            worker_id="worker-1",
            completed_at=completed_at,
            notification_id="job:job-1:terminal",
        )
    )

    assert decision.decision == "accepted_new"
    assert decision.status == "done"
    assert decision.completed_at == completed_at
    assert decision.terminal_event_id is None

    state = _run(
        repository.complete_terminal_state(
            message.job_id,
            terminal_event_id="1-0",
        )
    )

    assert state is not None
    assert state.status == "done"
    assert state.attempts == 1
    assert state.worker_id == "worker-1"
    assert state.completed_at == completed_at
    assert state.notification_id == "job:job-1:terminal"
    assert state.terminal_event_id == "1-0"


def test_claim_terminal_state_returns_duplicate_for_same_terminal() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc)

    _run(repository.enqueue_job(message))
    _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=1,
            worker_id="worker-1",
            completed_at=completed_at,
            notification_id="job:job-1:terminal",
        )
    )
    _run(
        repository.complete_terminal_state(
            message.job_id,
            terminal_event_id="1-0",
        )
    )

    decision = _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=2,
            worker_id="worker-2",
            completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=timezone.utc),
            notification_id="job:job-1:terminal:retry",
        )
    )

    assert decision.decision == "duplicate"
    assert decision.status == "done"
    assert decision.attempts == 1
    assert decision.worker_id == "worker-1"
    assert decision.completed_at == completed_at
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id == "1-0"


def test_claim_terminal_state_returns_pending_for_same_terminal_without_event_id() -> (
    None
):
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc)

    _run(repository.enqueue_job(message))
    _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=1,
            worker_id="worker-1",
            completed_at=completed_at,
            notification_id="job:job-1:terminal",
        )
    )

    decision = _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=2,
            worker_id="worker-2",
            completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=timezone.utc),
            notification_id="job:job-1:terminal:retry",
        )
    )

    assert decision.decision == "accepted_pending"
    assert decision.status == "done"
    assert decision.attempts == 1
    assert decision.worker_id == "worker-1"
    assert decision.completed_at == completed_at
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id is None


def test_claim_terminal_state_rejects_conflicting_terminal_after_done() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc)

    _run(repository.enqueue_job(message))
    _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=1,
            worker_id="worker-1",
            completed_at=completed_at,
            notification_id="job:job-1:terminal",
        )
    )
    _run(
        repository.complete_terminal_state(
            message.job_id,
            terminal_event_id="1-0",
        )
    )

    decision = _run(
        repository.claim_terminal_state(
            message.job_id,
            status="failed",
            attempt=2,
            worker_id="worker-2",
            completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=timezone.utc),
            notification_id="job:job-1:terminal:failed",
        )
    )

    assert decision.decision == "conflict"
    assert decision.status == "done"
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id == "1-0"


def test_claim_terminal_state_rejects_conflicting_terminal_after_failed() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc)

    _run(repository.enqueue_job(message))
    _run(
        repository.claim_terminal_state(
            message.job_id,
            status="failed",
            attempt=1,
            worker_id="worker-1",
            completed_at=completed_at,
            notification_id="job:job-1:terminal",
        )
    )
    _run(
        repository.complete_terminal_state(
            message.job_id,
            terminal_event_id="1-0",
        )
    )

    decision = _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=2,
            worker_id="worker-2",
            completed_at=datetime(2026, 3, 14, 12, 6, tzinfo=timezone.utc),
            notification_id="job:job-1:terminal:done",
        )
    )

    assert decision.decision == "conflict"
    assert decision.status == "failed"
    assert decision.notification_id == "job:job-1:terminal"
    assert decision.terminal_event_id == "1-0"


def test_state_ttl_is_capped_by_job_expiration_and_terminal_expire() -> None:
    redis = EvalFakeRedis()
    repository = _repository(redis)
    message = _message()
    completed_at = datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc)
    state_key = build_state_key(SPEC, message.job_id)

    _run(repository.enqueue_job(message))

    initial_ttl = _run(redis.ttl(state_key))
    assert initial_ttl > 0

    _run(
        repository.claim_terminal_state(
            message.job_id,
            status="done",
            attempt=1,
            worker_id="worker-1",
            completed_at=completed_at,
            notification_id="job:job-1:terminal",
        )
    )
    _run(
        repository.complete_terminal_state(
            message.job_id,
            terminal_event_id="1-0",
        )
    )
    assert _run(redis.ttl(state_key)) > 0

    _run(repository.expire_state(message.job_id))

    ttl = _run(redis.ttl(state_key))
    assert ttl > 0
    assert ttl <= SPEC.state_ttl_seconds
    state = _run(repository.read_state(message.job_id))
    assert state is not None
    assert state.status == "done"
    assert state.started_at is None
    assert state.completed_at == completed_at
    assert state.notification_id == "job:job-1:terminal"
    assert state.terminal_event_id == "1-0"
