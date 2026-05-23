from __future__ import annotations

from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchScrapeRequest,
    InstagramScrapeJobCreateRequest,
)


def test_batch_scrape_request_normalizes_and_dedupes_usernames() -> None:
    payload = InstagramBatchScrapeRequest(
        usernames=[" Alpha ", "BETA", "alpha", " beta ", "gamma"]
    )

    assert payload.usernames == ["alpha", "beta", "gamma"]


def test_scrape_job_create_request_exposes_only_usernames() -> None:
    payload = InstagramScrapeJobCreateRequest(
        usernames=[" Alpha ", "BETA", "alpha", " beta ", "gamma"]
    )

    assert payload.usernames == ["alpha", "beta", "gamma"]
    assert set(InstagramScrapeJobCreateRequest.model_json_schema()["properties"]) == {
        "usernames"
    }
