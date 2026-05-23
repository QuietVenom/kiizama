from __future__ import annotations

from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import workflow as workflow_module
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
)
from kiizama_scrape_core.ig_scraper_v2.workflow import execute_scrape_job_payload


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.closed = True


class FakePersistence:
    def __init__(self, *, session: Any) -> None:
        self.session = session
        self.persisted_response: InstagramBatchScrapeResponse | None = None

    async def get_profiles_by_usernames(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        return []

    async def persist_scrape_results(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        self.persisted_response = response
        return response


class FakeScraperBackend:
    def __init__(self, response: InstagramBatchScrapeResponse) -> None:
        self.response = response
        self.requests: list[InstagramBatchScrapeRequest] = []

    async def scrape(
        self,
        request: InstagramBatchScrapeRequest,
    ) -> InstagramBatchScrapeResponse:
        self.requests.append(request)
        return self.response


class FakeAnalysisService:
    async def enrich_scrape_response(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        for result in response.results.values():
            result.ai_categories = ["Fitness / Wellness"]
        return response


@pytest.mark.anyio
async def test_execute_scrape_job_payload_runs_executor_within_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions: list[FakeSession] = []
    persistences: list[FakePersistence] = []

    def session_factory() -> FakeSession:
        session = FakeSession()
        sessions.append(session)
        return session

    class TrackingPersistence(FakePersistence):
        def __init__(self, *, session: Any) -> None:
            super().__init__(session=session)
            persistences.append(self)

    monkeypatch.setattr(
        workflow_module, "SqlInstagramScrapePersistenceV2", TrackingPersistence
    )

    scraper_backend = FakeScraperBackend(
        InstagramBatchScrapeResponse(
            results={"alpha": InstagramBatchProfileResult(success=True)},
            counters=InstagramBatchCountersSchema(requested=1, successful=1),
        )
    )

    summary, error = await execute_scrape_job_payload(
        {"usernames": ["alpha"]},
        session_factory=session_factory,
        scraper_backend=scraper_backend,
        analysis_service=FakeAnalysisService(),
    )

    assert error is None
    assert [(item.username, item.status) for item in summary.usernames] == [
        ("alpha", "success")
    ]
    assert scraper_backend.requests[0].usernames == ["alpha"]
    assert len(sessions) == 1
    assert sessions[0].closed is True
    assert persistences[0].session is sessions[0]
    assert persistences[0].persisted_response is not None
    assert persistences[0].persisted_response.results["alpha"].ai_categories == [
        "Fitness / Wellness"
    ]


@pytest.mark.anyio
async def test_execute_scrape_job_payload_propagates_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_module, "SqlInstagramScrapePersistenceV2", FakePersistence
    )

    scraper_backend = FakeScraperBackend(
        InstagramBatchScrapeResponse(
            results={
                "alpha": InstagramBatchProfileResult(
                    success=False,
                    error="Navigation failed",
                )
            },
            counters=InstagramBatchCountersSchema(requested=1, failed=1),
            error="Navigation failed",
        )
    )

    summary, error = await execute_scrape_job_payload(
        {"usernames": ["alpha"]},
        session_factory=lambda: FakeSession(),
        scraper_backend=scraper_backend,
        analysis_service=FakeAnalysisService(),
    )

    assert error == "Navigation failed"
    assert [(item.username, item.status) for item in summary.usernames] == [
        ("alpha", "failed")
    ]
