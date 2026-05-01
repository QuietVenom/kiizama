from __future__ import annotations

import pytest
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchRecommendationsRequest,
    InstagramBatchScrapeRequest,
    InstagramScrapeJobCreateRequest,
)
from kiizama_scrape_core.ig_scraper.service import prepare_recommendations_batch_payload


def test_batch_scrape_request_normalizes_and_dedupes_usernames() -> None:
    payload = InstagramBatchScrapeRequest(
        usernames=[" Alpha ", "BETA", "alpha", " beta ", "gamma"]
    )

    assert payload.usernames == ["alpha", "beta", "gamma"]


def test_scrape_job_create_request_reuses_shared_username_normalization() -> None:
    payload = InstagramScrapeJobCreateRequest(
        usernames=[" Alpha ", "BETA", "alpha", " beta ", "gamma"]
    )

    assert payload.usernames == ["alpha", "beta", "gamma"]


def test_batch_scrape_request_uses_env_default_max_concurrent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IG_SCRAPER_MAX_CONCURRENT", "4")

    payload = InstagramBatchScrapeRequest(usernames=["alpha"])

    assert payload.max_concurrent == 4


def test_explicit_max_concurrent_overrides_env_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IG_SCRAPER_MAX_CONCURRENT", "4")

    payload = InstagramBatchScrapeRequest(usernames=["alpha"], max_concurrent=6)

    assert payload.max_concurrent == 6


def test_prepare_recommendations_batch_payload_skips_invalid_usernames() -> None:
    payload = InstagramBatchRecommendationsRequest(
        usernames=[" Alpha ", "invalid!", "alpha"]
    )

    prepared_payload, skipped, early_response = prepare_recommendations_batch_payload(
        payload
    )

    assert prepared_payload.usernames == ["alpha"]
    assert [(item.username, item.status, item.error) for item in skipped] == [
        ("invalid!", "skipped", "Invalid username format")
    ]
    assert early_response is None
