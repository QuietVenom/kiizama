import asyncio
from typing import Any

from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
)

from app.features.ig_scraper_jobs import apify_runner as runner_module


class _FakeJobControlRepository:
    def __init__(self) -> None:
        self.spec = object()


class _FakeSessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    def __enter__(self) -> object:
        return self._session

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _RecordingInstagramJobService:
    created_kwargs: dict[str, Any] | None = None
    completed_job_id: str | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.__class__.created_kwargs = kwargs

    async def complete_job(self, *, job_id: str, payload: Any) -> None:
        del payload
        self.__class__.completed_job_id = job_id


def test_apify_runner_complete_job_passes_session_to_instagram_job_service(
    monkeypatch,
) -> None:
    fake_session = object()
    monkeypatch.setattr(
        runner_module,
        "Session",
        lambda _engine: _FakeSessionContext(fake_session),
    )
    monkeypatch.setattr(
        runner_module,
        "InstagramJobService",
        _RecordingInstagramJobService,
    )
    monkeypatch.setattr(
        runner_module,
        "SqlJobProjectionRepository",
        lambda *, session: {"session": session},
    )
    monkeypatch.setattr(
        runner_module,
        "get_instagram_apify_job_control_repository",
        lambda: _FakeJobControlRepository(),
    )
    monkeypatch.setattr(
        runner_module,
        "get_instagram_job_control_repository",
        lambda: "worker-repo",
    )
    monkeypatch.setattr(
        runner_module,
        "get_instagram_user_events_repository",
        lambda: "user-events-repo",
    )

    runner = runner_module.ApifyInstagramJobRunner()
    summary = InstagramBatchScrapeSummaryResponse(
        usernames=[InstagramBatchUsernameStatus(username="alpha", status="success")],
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
        error=None,
    )

    ack = asyncio.run(
        runner._complete_job(
            job_id="job-123",
            attempt=1,
            status="done",
            summary=summary,
            error=None,
        )
    )

    assert ack is True
    assert _RecordingInstagramJobService.created_kwargs is not None
    assert _RecordingInstagramJobService.created_kwargs["session"] is fake_session
    assert (
        _RecordingInstagramJobService.created_kwargs["job_control_repositories"][
            "worker"
        ]
        == "worker-repo"
    )
    assert isinstance(
        _RecordingInstagramJobService.created_kwargs["job_control_repositories"][
            "apify"
        ],
        _FakeJobControlRepository,
    )
    assert _RecordingInstagramJobService.completed_job_id == "job-123"
