from __future__ import annotations

from kiizama_scrape_core.ig_scraper.types.apify_ig_scraper import (
    ApifyInstagramProfileScraper,
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
