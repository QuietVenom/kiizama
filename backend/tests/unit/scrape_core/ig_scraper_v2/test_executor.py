from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramProfileSchema,
    InstagramScrapeJobExecutor,
)
from kiizama_scrape_core.ig_scraper_v2.service import NOT_FOUND_ERROR
from pydantic import ValidationError


class FakePersistence:
    def __init__(self, profiles: list[dict[str, Any]] | None = None) -> None:
        self.profiles = profiles or []
        self.persisted_response: InstagramBatchScrapeResponse | None = None

    async def get_profiles_by_usernames(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        return [
            profile
            for profile in self.profiles
            if str(profile.get("username", "")).lower() in set(usernames)
        ]

    async def persist_scrape_results(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        self.persisted_response = response
        return response


class FakeAnalysisService:
    def __init__(self) -> None:
        self.calls = 0

    async def enrich_scrape_response(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        self.calls += 1
        for result in response.results.values():
            result.ai_categories = ["Fitness / Wellness"]
        return response


class FakeAiFailureAnalysisService:
    async def enrich_scrape_response(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        for result in response.results.values():
            result.ai_error = "AI unavailable"
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


def expiring_cdn_url(*, seconds_from_now: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(seconds=seconds_from_now)
    return f"https://cdn.example.test/profile.jpg?oe={int(expires_at.timestamp()):X}"


@pytest.mark.anyio
async def test_executor_runs_scrape_ai_persist_and_summary_success() -> None:
    response = InstagramBatchScrapeResponse(
        results={
            "alpha": InstagramBatchProfileResult(
                success=True,
                user=InstagramProfileSchema(username="alpha"),
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
    )
    scraper_backend = FakeScraperBackend(response)
    persistence = FakePersistence()
    analysis_service = FakeAnalysisService()
    executor = InstagramScrapeJobExecutor(
        scraper_backend=scraper_backend,
        persistence=persistence,
        analysis_service=analysis_service,
    )

    result = await executor.execute({"usernames": ["alpha"]})

    assert result.error is None
    assert result.summary.usernames[0].status == "success"
    assert scraper_backend.requests[0].usernames == ["alpha"]
    assert analysis_service.calls == 1
    assert persistence.persisted_response is response
    assert response.results["alpha"].ai_categories == ["Fitness / Wellness"]


@pytest.mark.anyio
async def test_executor_early_response_skips_scrape_ai_and_persist() -> None:
    response = InstagramBatchScrapeResponse()
    scraper_backend = FakeScraperBackend(response)
    persistence = FakePersistence(
        [
            {
                "username": "fresh",
                "profile_pic_url": expiring_cdn_url(seconds_from_now=3600),
            }
        ]
    )
    analysis_service = FakeAnalysisService()
    executor = InstagramScrapeJobExecutor(
        scraper_backend=scraper_backend,
        persistence=persistence,
        analysis_service=analysis_service,
    )

    result = await executor.execute({"usernames": ["fresh"]})

    assert result.error is None
    assert result.summary.usernames[0].status == "skipped"
    assert scraper_backend.requests == []
    assert analysis_service.calls == 0
    assert persistence.persisted_response is None


@pytest.mark.anyio
async def test_executor_marks_not_found_and_failed_profiles() -> None:
    response = InstagramBatchScrapeResponse(
        results={
            "missing": InstagramBatchProfileResult(
                success=False,
                error=NOT_FOUND_ERROR,
            ),
            "bad": InstagramBatchProfileResult(
                success=False,
                error="Navigation failed",
            ),
        },
        counters=InstagramBatchCountersSchema(
            requested=2,
            not_found=1,
            failed=1,
        ),
    )
    executor = InstagramScrapeJobExecutor(
        scraper_backend=FakeScraperBackend(response),
        persistence=FakePersistence(),
        analysis_service=FakeAnalysisService(),
    )

    result = await executor.execute({"usernames": ["missing", "bad"]})

    assert [(item.username, item.status) for item in result.summary.usernames] == [
        ("missing", "not_found"),
        ("bad", "failed"),
    ]
    assert result.summary.usernames[1].error == "Navigation failed"


@pytest.mark.anyio
async def test_executor_preserves_ai_error_and_persists_response() -> None:
    response = InstagramBatchScrapeResponse(
        results={
            "alpha": InstagramBatchProfileResult(
                success=True,
                user=InstagramProfileSchema(username="alpha"),
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
    )
    persistence = FakePersistence()
    executor = InstagramScrapeJobExecutor(
        scraper_backend=FakeScraperBackend(response),
        persistence=persistence,
        analysis_service=FakeAiFailureAnalysisService(),
    )

    result = await executor.execute({"usernames": ["alpha"]})

    assert result.summary.usernames[0].status == "success"
    assert response.results["alpha"].ai_error == "AI unavailable"
    assert persistence.persisted_response is response


@pytest.mark.anyio
async def test_executor_invalid_payload_raises_validation_error() -> None:
    executor = InstagramScrapeJobExecutor(
        scraper_backend=FakeScraperBackend(InstagramBatchScrapeResponse()),
        persistence=FakePersistence(),
        analysis_service=FakeAnalysisService(),
    )

    with pytest.raises(ValidationError):
        await executor.execute({"usernames": []})
