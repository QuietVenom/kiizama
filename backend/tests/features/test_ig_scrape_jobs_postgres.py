from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine, Generator
from datetime import datetime, timezone
from typing import Any, TypeVar, cast

import pytest
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobTerminalizationRequest,
)
from kiizama_scrape_core.job_control.schemas import (
    JobQueueSpec,
    TerminalizationDecision,
)
from sqlmodel import Session, delete, select

from app.core.config import settings
from app.features.ig_scraper_jobs.repository import SqlJobProjectionRepository
from app.features.ig_scraper_jobs.service import InstagramJobService
from app.models import IgScrapeJob, User


@pytest.fixture(scope="module", autouse=True)
def ensure_ig_scrape_jobs_table(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgScrapeJob).__table__.create(bind=bind, checkfirst=True)
    db.exec(delete(IgScrapeJob))
    db.commit()
    yield
    db.exec(delete(IgScrapeJob))
    db.commit()


class FakeJobControlRepository:
    def __init__(self) -> None:
        self.spec = JobQueueSpec(
            domain="ig-scrape",
            state_ttl_seconds=3600,
            queue_maxlen=100,
        )
        self.enqueued_messages: list[object] = []
        self.read_state_result = None
        self.claim_terminal_result = TerminalizationDecision(
            decision="accepted_new",
            status="done",
            attempts=1,
            worker_id="worker-1",
            completed_at=datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc),
            notification_id="job:terminal",
            terminal_event_id=None,
        )
        self.complete_terminal_calls: list[tuple[str, str]] = []

    async def enqueue_job(self, message: object) -> None:
        self.enqueued_messages.append(message)

    async def read_state(self, job_id: str) -> None:
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
    ) -> None:
        self.complete_terminal_calls.append((job_id, terminal_event_id))
        return None


class FakeUserEventsRepository:
    def __init__(self) -> None:
        self.publish_calls: list[dict[str, object]] = []

    async def publish_event(self, **kwargs: object) -> tuple[str, bool]:
        self.publish_calls.append(kwargs)
        return "1-0", True


T = TypeVar("T")


def _run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


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


def _owner_user_id(db: Session) -> str:
    user = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()
    return str(user.id)


def test_create_job_persists_projection_in_postgres(db: Session) -> None:
    repository = SqlJobProjectionRepository(session=db)
    job_control_repository = FakeJobControlRepository()
    service = InstagramJobService(
        jobs_collection=repository,
        job_control_repositories={
            "worker": job_control_repository,
            "apify": job_control_repository,
        },
        user_events_repository=FakeUserEventsRepository(),
        clock=lambda: datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
    )

    job_id = _run(
        service.create_job(payload=_payload(), owner_user_id=_owner_user_id(db))
    )

    record = db.get(IgScrapeJob, uuid.UUID(str(job_id)))
    assert isinstance(record, IgScrapeJob)
    assert str(record.owner_user_id) == _owner_user_id(db)
    assert record.status == "queued"
    assert record.payload["usernames"] == ["alpha", "beta"]
    assert len(job_control_repository.enqueued_messages) == 1


def test_complete_job_updates_postgres_projection_and_returns_terminal_status(
    db: Session,
) -> None:
    repository = SqlJobProjectionRepository(session=db)
    job_control_repository = FakeJobControlRepository()
    user_events_repository = FakeUserEventsRepository()
    service = InstagramJobService(
        jobs_collection=repository,
        job_control_repositories={
            "worker": job_control_repository,
            "apify": job_control_repository,
        },
        user_events_repository=user_events_repository,
        clock=lambda: datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
    )

    job_id = str(
        _run(service.create_job(payload=_payload(), owner_user_id=_owner_user_id(db)))
    )

    response = _run(
        service.complete_job(
            job_id=job_id,
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
    record = db.get(IgScrapeJob, uuid.UUID(job_id))
    assert isinstance(record, IgScrapeJob)
    assert record.status == "done"
    assert record.summary is not None
    assert record.references is not None
    assert record.completed_at == datetime(2026, 3, 21, 12, 1, tzinfo=timezone.utc)
    assert record.notification_id == f"job:{job_id}:terminal"
    assert len(user_events_repository.publish_calls) == 1

    status_response = _run(
        service.get_job(
            job_id=job_id,
            owner_user_id=_owner_user_id(db),
        )
    )
    assert status_response is not None
    assert status_response.status == "done"
    assert status_response.summary is not None
    assert status_response.references is not None


def test_get_job_returns_none_for_foreign_owner_in_postgres(db: Session) -> None:
    repository = SqlJobProjectionRepository(session=db)
    job_control_repository = FakeJobControlRepository()
    service = InstagramJobService(
        jobs_collection=repository,
        job_control_repositories={
            "worker": job_control_repository,
            "apify": job_control_repository,
        },
        user_events_repository=FakeUserEventsRepository(),
        clock=lambda: datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
    )

    job_id = str(
        _run(service.create_job(payload=_payload(), owner_user_id=_owner_user_id(db)))
    )

    assert (
        _run(
            service.get_job(
                job_id=job_id,
                owner_user_id=str(uuid.uuid4()),
            )
        )
        is None
    )
