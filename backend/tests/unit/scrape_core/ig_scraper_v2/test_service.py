from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
)
from kiizama_scrape_core.ig_scraper_v2.service import (
    NOT_FOUND_ERROR,
    build_batch_scrape_summary,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
)


class FakePersistence:
    def __init__(self, profiles: list[dict[str, Any]]) -> None:
        self.profiles = profiles
        self.persisted_response: InstagramBatchScrapeResponse | None = None

    async def get_profiles_by_usernames(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        return [
            profile
            for profile in self.profiles
            if profile.get("username") in set(usernames)
        ]

    async def persist_scrape_results(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        self.persisted_response = response
        return response


class FakeAnalysisService:
    async def enrich_scrape_response(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        for result in response.results.values():
            result.ai_categories = ["Fitness / Wellness"]
        return response


def expiring_cdn_url(*, seconds_from_now: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(seconds=seconds_from_now)
    return f"https://cdn.example.test/profile.jpg?oe={int(expires_at.timestamp()):X}"


@pytest.mark.anyio
async def test_prepare_scrape_batch_payload_skips_fresh_profiles() -> None:
    payload = InstagramBatchScrapeRequest(usernames=["fresh"])
    persistence = FakePersistence(
        [
            {
                "username": "fresh",
                "profile_pic_url": expiring_cdn_url(seconds_from_now=3600),
            }
        ]
    )

    prepared_payload, early_response = await prepare_scrape_batch_payload(
        payload,
        persistence,
    )

    assert prepared_payload.usernames == ["fresh"]
    assert early_response is not None
    assert early_response.counters.requested == 0


@pytest.mark.anyio
async def test_prepare_scrape_batch_payload_keeps_missing_and_expired_profiles() -> (
    None
):
    payload = InstagramBatchScrapeRequest(usernames=["fresh", "expired", "missing"])
    persistence = FakePersistence(
        [
            {
                "username": "fresh",
                "profile_pic_url": expiring_cdn_url(seconds_from_now=3600),
            },
            {
                "username": "expired",
                "profile_pic_url": expiring_cdn_url(seconds_from_now=-60),
            },
        ]
    )

    prepared_payload, early_response = await prepare_scrape_batch_payload(
        payload,
        persistence,
    )

    assert early_response is None
    assert prepared_payload.usernames == ["expired", "missing"]


def test_build_batch_scrape_summary_marks_skipped_success_not_found_and_failed() -> (
    None
):
    payload = InstagramBatchScrapeRequest(usernames=["fresh", "ok", "missing", "bad"])
    scrape_payload = payload.model_copy(update={"usernames": ["ok", "missing", "bad"]})
    response = InstagramBatchScrapeResponse(
        results={
            "ok": InstagramBatchProfileResult(success=True),
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
            requested=3,
            successful=1,
            not_found=1,
            failed=1,
        ),
    )

    summary = build_batch_scrape_summary(payload, scrape_payload, response)

    assert [(item.username, item.status) for item in summary.usernames] == [
        ("fresh", "skipped"),
        ("ok", "success"),
        ("missing", "not_found"),
        ("bad", "failed"),
    ]
    assert summary.usernames[3].error == "Navigation failed"
    assert summary.counters.requested == 3


def test_build_batch_scrape_summary_marks_all_skipped_for_early_response() -> None:
    payload = InstagramBatchScrapeRequest(usernames=["fresh"])

    summary = build_batch_scrape_summary(
        payload,
        payload,
        None,
        early_response=InstagramBatchScrapeResponse(
            counters=InstagramBatchCountersSchema(requested=0)
        ),
    )

    assert [(item.username, item.status) for item in summary.usernames] == [
        ("fresh", "skipped")
    ]
    assert summary.counters.requested == 0


@pytest.mark.anyio
async def test_enrich_and_persist_wrappers_use_injected_dependencies() -> None:
    response = InstagramBatchScrapeResponse(
        results={"ok": InstagramBatchProfileResult(success=True)}
    )
    persistence = FakePersistence([])

    enriched = await enrich_with_ai_analysis(
        response,
        analysis_service=FakeAnalysisService(),
    )
    persisted = await persist_scrape_results_to_db(
        enriched,
        persistence=persistence,
    )

    assert persisted.results["ok"].ai_categories == ["Fitness / Wellness"]
    assert persistence.persisted_response is persisted
