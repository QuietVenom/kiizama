from __future__ import annotations

from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2 import apify as apify_module
from kiizama_scrape_core.ig_scraper_v2.apify import (
    ApifyInstagramProfileScraper,
    ApifyInstagramScraperBackend,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
)


def test_build_response_missing_profile_id_counts_username_as_not_found() -> None:
    scraper = ApifyInstagramProfileScraper(
        api_token="test-token",
        usernames=["missinguser"],
    )

    response = scraper._build_response(
        [
            {
                "username": "missinguser",
                "id": None,
            }
        ]
    )

    assert response["results"]["missinguser"]["success"] is False
    assert response["results"]["missinguser"]["error"] == (
        "Instagram username does not exist"
    )
    assert response["counters"] == {
        "requested": 1,
        "successful": 0,
        "failed": 0,
        "not_found": 1,
    }


@pytest.mark.anyio
async def test_scraper_backend_adapts_request_to_profile_scraper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeProfileScraper:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def run(self) -> dict[str, Any]:
            return {
                "results": {
                    "alpha": {
                        "success": True,
                        "error": None,
                    }
                },
                "counters": {
                    "requested": 1,
                    "successful": 1,
                    "failed": 0,
                    "not_found": 0,
                },
                "error": None,
            }

    monkeypatch.setattr(
        apify_module, "ApifyInstagramProfileScraper", FakeProfileScraper
    )

    backend = ApifyInstagramScraperBackend(
        api_token="test-token",
        include_about_section=True,
    )
    response = await backend.scrape(InstagramBatchScrapeRequest(usernames=["alpha"]))

    assert isinstance(response, InstagramBatchScrapeResponse)
    assert response.results["alpha"].success is True
    assert response.counters.successful == 1
    assert captured == {
        "api_token": "test-token",
        "usernames": ["alpha"],
        "actor_id": apify_module.APIFY_INSTAGRAM_PROFILE_SCRAPER_ACTOR_ID,
        "include_about_section": True,
    }
