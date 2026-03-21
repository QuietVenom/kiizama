from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobTerminalizationRequest,
)
from kiizama_scrape_core.job_control.schemas import (
    JobQueueSpec,
    JobTransientState,
    TerminalizationDecision,
)

from app.features.ig_scraper_jobs.service import InstagramJobService
from app.features.job_control.repository import JobControlUnavailableError


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


@dataclass
class _UpdateResult:
    matched_count: int = 1


class FakeJobsCollection:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    async def insert_one(self, doc: dict[str, Any]) -> None:
        self.docs[str(doc["_id"])] = dict(doc)

    async def delete_one(self, filter_query: dict[str, Any]) -> None:
        self.docs.pop(str(filter_query["_id"]), None)

    async def find_one(
        self,
        filter_query: dict[str, Any],
        projection: dict[str, int] | None = None,
    ) -> dict[str, Any] | None:
        doc = self.docs.get(str(filter_query["_id"]))
        if doc is None:
            return None
        result = dict(doc)
        if projection:
            for key, include in projection.items():
                if include == 0:
                    result.pop(key, None)
        return result

    async def update_one(
        self,
        filter_query: dict[str, Any],
        update: dict[str, Any],
    ) -> _UpdateResult:
        doc = self.docs.get(str(filter_query["_id"]))
        if doc is None:
            return _UpdateResult(matched_count=0)
        for key, value in update.get("$set", {}).items():
            doc[key] = value
        return _UpdateResult()


class FakeJobControlRepository:
    def __init__(self) -> None:
        self.spec = JobQueueSpec(
            domain="ig-scrape",
            state_ttl_seconds=3600,
            queue_maxlen=100,
        )
        self.enqueued_messages: list[Any] = []
        self.read_state_result: JobTransientState | None = None
        self.enqueue_exception: Exception | None = None
        self.claim_terminal_result = TerminalizationDecision(
            decision="accepted_new",
            status="done",
            attempts=1,
            worker_id="worker-1",
            completed_at=datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
            notification_id="job:job-1:terminal",
            terminal_event_id=None,
        )
        self.complete_terminal_calls: list[tuple[str, str]] = []

    async def enqueue_job(self, message: Any) -> None:
        if self.enqueue_exception is not None:
            raise self.enqueue_exception
        self.enqueued_messages.append(message)

    async def read_state(self, job_id: str) -> JobTransientState | None:
        del job_id
        return self.read_state_result

    async def claim_terminal_state(
        self,
        job_id: str,
        *,
        status: str,
        attempt: int,
        worker_id: str,
        completed_at: datetime,
        notification_id: str,
    ) -> TerminalizationDecision:
        del job_id, status, attempt, worker_id, completed_at, notification_id
        return self.claim_terminal_result

    async def complete_terminal_state(
        self,
        job_id: str,
        *,
        terminal_event_id: str,
    ) -> JobTransientState | None:
        self.complete_terminal_calls.append((job_id, terminal_event_id))
        return None


class FakeUserEventsRepository:
    def __init__(self) -> None:
        self.publish_calls: list[dict[str, Any]] = []

    async def publish_event(self, **kwargs: Any) -> tuple[str, bool]:
        self.publish_calls.append(kwargs)
        return "1-0", True


def _payload() -> InstagramScrapeJobCreateRequest:
    return InstagramScrapeJobCreateRequest(usernames=["alpha", "beta"])


def _summary() -> InstagramBatchScrapeSummaryResponse:
    return InstagramBatchScrapeSummaryResponse(
        usernames=[
            InstagramBatchUsernameStatus(username="alpha", status="success"),
            InstagramBatchUsernameStatus(username="beta", status="skipped"),
        ],
        counters=InstagramBatchCountersSchema(requested=2, successful=1),
        error=None,
    )


def _service(
    *,
    jobs_collection: FakeJobsCollection | None = None,
    job_control_repository: FakeJobControlRepository | None = None,
    user_events_repository: FakeUserEventsRepository | None = None,
) -> InstagramJobService:
    return InstagramJobService(
        jobs_collection=jobs_collection or FakeJobsCollection(),
        job_control_repository=job_control_repository or FakeJobControlRepository(),
        user_events_repository=user_events_repository or FakeUserEventsRepository(),
        clock=lambda: datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
    )


def test_create_job_inserts_projection_and_enqueues_message() -> None:
    jobs_collection = FakeJobsCollection()
    job_control_repository = FakeJobControlRepository()
    service = _service(
        jobs_collection=jobs_collection,
        job_control_repository=job_control_repository,
    )

    job_id = _run(service.create_job(payload=_payload(), owner_user_id="user-1"))

    assert job_id in jobs_collection.docs
    doc = jobs_collection.docs[job_id]
    assert doc["ownerUserId"] == "user-1"
    assert doc["status"] == "queued"
    assert len(job_control_repository.enqueued_messages) == 1
    assert job_control_repository.enqueued_messages[0].job_id == job_id


def test_create_job_rolls_back_projection_when_enqueue_fails() -> None:
    jobs_collection = FakeJobsCollection()
    job_control_repository = FakeJobControlRepository()
    job_control_repository.enqueue_exception = JobControlUnavailableError("redis down")
    service = _service(
        jobs_collection=jobs_collection,
        job_control_repository=job_control_repository,
    )

    try:
        _run(service.create_job(payload=_payload(), owner_user_id="user-1"))
    except JobControlUnavailableError as exc:
        assert str(exc) == "redis down"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected JobControlUnavailableError")

    assert jobs_collection.docs == {}


def test_get_job_merges_redis_state_over_mongo_projection() -> None:
    jobs_collection = FakeJobsCollection()
    job_control_repository = FakeJobControlRepository()
    service = _service(
        jobs_collection=jobs_collection,
        job_control_repository=job_control_repository,
    )
    jobs_collection.docs["job-1"] = {
        "_id": "job-1",
        "ownerUserId": "user-1",
        "status": "queued",
        "createdAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "expiresAt": datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        "summary": None,
        "references": None,
        "error": None,
    }
    job_control_repository.read_state_result = JobTransientState(
        status="running",
        attempts=2,
        worker_id="worker-1",
        heartbeat_at=datetime(2026, 3, 21, 12, 5, tzinfo=timezone.utc),
        leased_until=datetime(2026, 3, 21, 12, 20, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 21, 12, 5, tzinfo=timezone.utc),
    )

    response = _run(service.get_job(job_id="job-1"))

    assert response is not None
    assert response.status == "running"
    assert response.attempts == 2
    assert response.lease_owner == "worker-1"


def test_get_job_returns_queued_projection_when_redis_state_is_not_created_yet() -> (
    None
):
    jobs_collection = FakeJobsCollection()
    service = _service(jobs_collection=jobs_collection)
    jobs_collection.docs["job-1"] = {
        "_id": "job-1",
        "ownerUserId": "user-1",
        "status": "queued",
        "createdAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "expiresAt": datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        "summary": None,
        "references": None,
        "error": None,
    }

    response = _run(service.get_job(job_id="job-1"))

    assert response is not None
    assert response.status == "queued"
    assert response.attempts == 0
    assert response.lease_owner is None


def test_get_job_rejects_stale_transient_projection_without_live_redis_state() -> None:
    jobs_collection = FakeJobsCollection()
    service = _service(jobs_collection=jobs_collection)
    jobs_collection.docs["job-1"] = {
        "_id": "job-1",
        "ownerUserId": "user-1",
        "status": "running",
        "createdAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "expiresAt": datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        "summary": None,
        "references": None,
        "error": None,
    }

    try:
        _run(service.get_job(job_id="job-1"))
    except RuntimeError as exc:
        assert "Unexpected transient job projection without live Redis state." in str(
            exc
        )
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected RuntimeError")


def test_complete_job_publishes_terminal_event_once_and_updates_projection() -> None:
    jobs_collection = FakeJobsCollection()
    job_control_repository = FakeJobControlRepository()
    user_events_repository = FakeUserEventsRepository()
    service = _service(
        jobs_collection=jobs_collection,
        job_control_repository=job_control_repository,
        user_events_repository=user_events_repository,
    )
    jobs_collection.docs["job-1"] = {
        "_id": "job-1",
        "ownerUserId": "user-1",
        "status": "queued",
        "createdAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "expiresAt": datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        "summary": None,
        "references": None,
        "error": None,
    }

    response = _run(
        service.complete_job(
            job_id="job-1",
            payload=InstagramScrapeJobTerminalizationRequest(
                status="done",
                attempt=1,
                worker_id="worker-1",
                completed_at=datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
                summary=_summary(),
                error=None,
            ),
        )
    )

    assert response is not None
    assert response.decision == "accepted_new"
    assert response.terminal_event_id == "1-0"
    assert len(user_events_repository.publish_calls) == 1
    publish_call = user_events_repository.publish_calls[0]
    assert publish_call["event_name"] == "ig-scrape.job.completed"
    envelope = publish_call["envelope"]
    assert envelope.payload["ready_usernames"] == ["alpha", "beta"]
    assert jobs_collection.docs["job-1"]["status"] == "done"
    assert job_control_repository.complete_terminal_calls == [("job-1", "1-0")]


def test_complete_job_duplicate_does_not_publish_event_twice() -> None:
    jobs_collection = FakeJobsCollection()
    job_control_repository = FakeJobControlRepository()
    job_control_repository.claim_terminal_result = TerminalizationDecision(
        decision="duplicate",
        status="done",
        attempts=1,
        worker_id="worker-1",
        completed_at=datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
        notification_id="job:job-1:terminal",
        terminal_event_id="1-0",
    )
    user_events_repository = FakeUserEventsRepository()
    service = _service(
        jobs_collection=jobs_collection,
        job_control_repository=job_control_repository,
        user_events_repository=user_events_repository,
    )
    jobs_collection.docs["job-1"] = {
        "_id": "job-1",
        "ownerUserId": "user-1",
        "status": "done",
        "createdAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
        "expiresAt": datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        "summary": _summary().model_dump(mode="json"),
        "references": None,
        "error": None,
    }

    response = _run(
        service.complete_job(
            job_id="job-1",
            payload=InstagramScrapeJobTerminalizationRequest(
                status="done",
                attempt=1,
                worker_id="worker-1",
                completed_at=datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
                summary=_summary(),
                error=None,
            ),
        )
    )

    assert response is not None
    assert response.decision == "duplicate"
    assert user_events_repository.publish_calls == []
    assert job_control_repository.complete_terminal_calls == []


def test_complete_job_duplicate_does_not_publish_again() -> None:
    jobs_collection = FakeJobsCollection()
    job_control_repository = FakeJobControlRepository()
    job_control_repository.claim_terminal_result = TerminalizationDecision(
        decision="duplicate",
        status="done",
        attempts=1,
        worker_id="worker-1",
        completed_at=datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
        notification_id="job:job-1:terminal",
        terminal_event_id="1-0",
    )
    user_events_repository = FakeUserEventsRepository()
    service = _service(
        jobs_collection=jobs_collection,
        job_control_repository=job_control_repository,
        user_events_repository=user_events_repository,
    )
    jobs_collection.docs["job-1"] = {
        "_id": "job-1",
        "ownerUserId": "user-1",
        "status": "done",
        "createdAt": datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
        "expiresAt": datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        "summary": _summary().model_dump(mode="json"),
        "references": None,
        "error": None,
    }

    response = _run(
        service.complete_job(
            job_id="job-1",
            payload=InstagramScrapeJobTerminalizationRequest(
                status="done",
                attempt=1,
                worker_id="worker-1",
                completed_at=datetime(2026, 3, 21, 12, 2, tzinfo=timezone.utc),
                summary=_summary(),
                error=None,
            ),
        )
    )

    assert response is not None
    assert response.decision == "duplicate"
    assert response.terminal_event_id == "1-0"
    assert user_events_repository.publish_calls == []
