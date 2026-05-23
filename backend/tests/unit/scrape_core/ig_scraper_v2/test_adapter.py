from __future__ import annotations

from kiizama_scrape_core.ig_scraper_v2.adapter import (
    to_instagram_batch_scrape_response,
)
from kiizama_scrape_core.ig_scraper_v2.models import (
    BatchScrapeCounters,
    InstagramBatchScrapeRunResult,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import InstagramBatchScrapeResponse


def test_adapter_converts_run_result_to_v2_batch_response_contract() -> None:
    run_result = InstagramBatchScrapeRunResult(
        success=True,
        credential_id="cred_1",
        session_message="Existing Instagram session is valid",
        results={
            "example": {
                "user": {
                    "id": "ig_1",
                    "username": "example",
                    "follower_count": 100,
                    "following_count": 10,
                    "media_count": 20,
                    "is_private": False,
                    "is_verified": True,
                },
                "recommended_users": [{"username": "related"}],
                "posts": [
                    {
                        "code": "post_1",
                        "caption_text": "hello #tag @mention",
                        "like_count": 25,
                        "comment_count": 5,
                        "media_type": 1,
                        "product_type": "feed",
                    }
                ],
                "reels": [
                    {
                        "code": "reel_1",
                        "play_count": 1000,
                        "like_count": 50,
                        "comment_count": 10,
                        "media_type": 2,
                        "product_type": "clips",
                    }
                ],
                "success": True,
                "error": None,
                "metrics": {
                    "user": {"username": "example"},
                    "recommended_users": [{"username": "related"}],
                    "followers": 100,
                    "following": 10,
                    "media_count": 20,
                    "is_private": False,
                    "is_verified": True,
                    "overall_post_engagement_rate": 0.3,
                    "reel_engagement_rate_on_plays": 0.06,
                    "post_metrics": {
                        "total_posts": 1,
                        "total_likes": 25,
                        "total_comments": 5,
                    },
                    "reel_metrics": {
                        "total_reels": 1,
                        "total_plays": 1000,
                    },
                },
            }
        },
        counters=BatchScrapeCounters(requested=1, successful=1),
    )

    response = to_instagram_batch_scrape_response(run_result)

    assert isinstance(response, InstagramBatchScrapeResponse)
    assert response.counters.requested == 1
    assert response.counters.successful == 1
    profile_result = response.results["example"]
    assert profile_result.success is True
    assert profile_result.user.username == "example"
    assert profile_result.recommended_users[0].username == "related"
    assert profile_result.posts[0].code == "post_1"
    assert profile_result.reels[0].code == "reel_1"
    assert profile_result.metrics.followers == 100

    metrics_payload = profile_result.metrics.model_dump()
    assert "user" not in metrics_payload
    assert "recommended_users" not in metrics_payload


def test_adapter_preserves_failed_and_not_found_results() -> None:
    run_result = InstagramBatchScrapeRunResult(
        success=False,
        credential_id="cred_1",
        session_message="ok",
        results={
            "missing": {
                "success": False,
                "error": "Instagram username does not exist",
                "metrics": {},
            },
            "broken": {
                "success": False,
                "error": "Navigation failed",
                "metrics": {},
            },
        },
        counters=BatchScrapeCounters(
            requested=2,
            successful=0,
            failed=1,
            not_found=1,
        ),
        error=None,
    )

    response = to_instagram_batch_scrape_response(run_result)

    assert response.counters.requested == 2
    assert response.counters.failed == 1
    assert response.counters.not_found == 1
    assert response.results["missing"].error == "Instagram username does not exist"
    assert response.results["broken"].error == "Navigation failed"
