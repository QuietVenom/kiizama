import asyncio
from datetime import UTC, datetime
from typing import Any

from app.features.job_control.schemas import (
    JobLeaseStatus,
    JobQueueSpec,
    JobTransientState,
    QueuedJobMessage,
)
from app.features.job_control.worker_runtime import JobWorkerRuntime


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeJobControlRepository:
    def __init__(self) -> None:
        self.spec = JobQueueSpec(
            domain="ig-scrape",
            state_ttl_seconds=60,
            queue_maxlen=100,
        )
        self.reclaimed_messages: list[QueuedJobMessage] = []
        self.new_messages: list[QueuedJobMessage] = []
        self.read_state_result: JobTransientState | None = None
        self.claim_owned = True
        self.running_attempt = 1
        self.renew_outcomes: list[bool] = []
        self.acked_message_ids: list[str] = []
        self.release_calls: list[tuple[str, str]] = []
        self.claim_calls: list[tuple[str, str]] = []
        self.running_calls: list[str] = []
        self.renew_calls: list[tuple[str, str]] = []
        self.expired_job_ids: list[str] = []
        self.read_reclaimed_calls = 0
        self.read_new_calls = 0

    async def read_reclaimed_messages(
        self,
        *,
        worker_id: str,
        min_idle_time_ms: int,
        count: int,
    ) -> list[QueuedJobMessage]:
        del worker_id, min_idle_time_ms, count
        self.read_reclaimed_calls += 1
        return list(self.reclaimed_messages)

    async def read_new_messages(
        self,
        *,
        worker_id: str,
        count: int,
        block_ms: int,
    ) -> list[QueuedJobMessage]:
        del worker_id, count, block_ms
        self.read_new_calls += 1
        return list(self.new_messages)

    async def read_state(self, job_id: str) -> JobTransientState | None:
        del job_id
        return self.read_state_result

    async def ack_message(self, message_id: str) -> None:
        self.acked_message_ids.append(message_id)

    async def claim_lease(
        self,
        job_id: str,
        *,
        lease_token: str,
        lease_seconds: int,
        now: datetime,
    ) -> JobLeaseStatus:
        del lease_seconds
        self.claim_calls.append((job_id, lease_token))
        return JobLeaseStatus(
            job_id=job_id,
            lease_token=lease_token,
            owned=self.claim_owned,
            leased_until=now,
        )

    async def write_running_state(
        self,
        job_id: str,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
        expires_at: datetime | None = None,
    ) -> JobTransientState:
        del lease_seconds
        self.running_calls.append(job_id)
        return JobTransientState(
            status="running",
            attempts=self.running_attempt,
            worker_id=worker_id,
            started_at=now,
            heartbeat_at=now,
            leased_until=now,
            updated_at=now,
            expires_at=expires_at,
        )

    async def renew_lease(
        self,
        job_id: str,
        *,
        lease_token: str,
        lease_seconds: int,
        now: datetime,
    ) -> JobLeaseStatus:
        del lease_seconds
        self.renew_calls.append((job_id, lease_token))
        owned = self.renew_outcomes.pop(0) if self.renew_outcomes else True
        return JobLeaseStatus(
            job_id=job_id,
            lease_token=lease_token,
            owned=owned,
            leased_until=now,
        )

    async def release_lease(self, job_id: str, *, lease_token: str) -> None:
        self.release_calls.append((job_id, lease_token))

    async def expire_state(self, job_id: str) -> None:
        self.expired_job_ids.append(job_id)


def _message(job_id: str = "job-1", message_id: str = "1-0") -> QueuedJobMessage:
    return QueuedJobMessage(
        message_id=message_id,
        job_id=job_id,
        owner_user_id="user-1",
        created_at=datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
        expires_at=datetime(2099, 3, 15, 12, 0, tzinfo=UTC),
        payload={"usernames": ["creator_one"]},
    )


def test_poll_messages_prefers_reclaimed_over_new() -> None:
    repository = FakeJobControlRepository()
    repository.reclaimed_messages = [_message("job-reclaimed")]
    repository.new_messages = [_message("job-new")]
    runtime = JobWorkerRuntime(
        repository=repository,  # type: ignore[arg-type]
        worker_id="worker-1",
        lease_seconds=30,
        heartbeat_seconds=0.01,
        poll_seconds=0.01,
    )

    messages = _run(runtime.poll_messages())

    assert [message.job_id for message in messages] == ["job-reclaimed"]
    assert repository.read_reclaimed_calls == 1
    assert repository.read_new_calls == 0


def test_poll_messages_reads_new_when_no_reclaimed_jobs_exist() -> None:
    repository = FakeJobControlRepository()
    repository.new_messages = [_message("job-new")]
    runtime = JobWorkerRuntime(
        repository=repository,  # type: ignore[arg-type]
        worker_id="worker-1",
        lease_seconds=30,
        heartbeat_seconds=0.01,
        poll_seconds=0.01,
    )

    messages = _run(runtime.poll_messages())

    assert [message.job_id for message in messages] == ["job-new"]
    assert repository.read_new_calls == 1


def test_start_job_short_circuits_terminal_messages() -> None:
    repository = FakeJobControlRepository()
    repository.read_state_result = JobTransientState(status="done", attempts=1)
    runtime = JobWorkerRuntime(
        repository=repository,  # type: ignore[arg-type]
        worker_id="worker-1",
        lease_seconds=30,
        heartbeat_seconds=0.01,
        poll_seconds=0.01,
    )

    handle = _run(runtime.start_job(_message()))

    assert handle is None
    assert repository.acked_message_ids == ["1-0"]
    assert repository.claim_calls == []


def test_start_job_discards_expired_messages_before_claiming_lease() -> None:
    repository = FakeJobControlRepository()
    runtime = JobWorkerRuntime(
        repository=repository,  # type: ignore[arg-type]
        worker_id="worker-1",
        lease_seconds=30,
        heartbeat_seconds=0.01,
        poll_seconds=0.01,
    )

    handle = _run(
        runtime.start_job(
            QueuedJobMessage(
                message_id="1-0",
                job_id="job-expired",
                owner_user_id="user-1",
                created_at=datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                expires_at=datetime(2026, 3, 13, 12, 0, tzinfo=UTC),
                payload={"usernames": ["creator_one"]},
            )
        )
    )

    assert handle is None
    assert repository.acked_message_ids == ["1-0"]
    assert repository.claim_calls == []
    assert repository.expired_job_ids == ["job-expired"]


def test_start_job_claims_lease_and_increments_attempts() -> None:
    repository = FakeJobControlRepository()
    repository.running_attempt = 2
    runtime = JobWorkerRuntime(
        repository=repository,  # type: ignore[arg-type]
        worker_id="worker-1",
        lease_seconds=30,
        heartbeat_seconds=60,
        poll_seconds=0.01,
    )

    handle = _run(runtime.start_job(_message()))

    assert handle is not None
    assert handle.attempt == 2
    assert handle.started_at is not None
    assert repository.claim_calls == [("job-1", "worker-1")]
    assert repository.running_calls == ["job-1"]

    _run(runtime.finish_job(handle, ack=False))


def test_finish_job_acks_and_releases_message() -> None:
    repository = FakeJobControlRepository()
    runtime = JobWorkerRuntime(
        repository=repository,  # type: ignore[arg-type]
        worker_id="worker-1",
        lease_seconds=30,
        heartbeat_seconds=60,
        poll_seconds=0.01,
    )
    handle = _run(runtime.start_job(_message()))
    assert handle is not None

    _run(runtime.finish_job(handle, ack=True))

    assert repository.acked_message_ids == ["1-0"]
    assert repository.release_calls == [("job-1", "worker-1")]


def test_heartbeat_renews_lease_and_marks_loss_of_ownership() -> None:
    repository = FakeJobControlRepository()
    repository.renew_outcomes = [False]
    runtime = JobWorkerRuntime(
        repository=repository,  # type: ignore[arg-type]
        worker_id="worker-1",
        lease_seconds=30,
        heartbeat_seconds=0.01,
        poll_seconds=0.01,
    )

    async def scenario() -> None:
        handle = await runtime.start_job(_message())
        assert handle is not None
        await asyncio.sleep(0.03)
        assert handle.lease_lost.is_set() is True
        await runtime.finish_job(handle, ack=False)

    _run(scenario())

    assert repository.renew_calls == [("job-1", "worker-1")]
