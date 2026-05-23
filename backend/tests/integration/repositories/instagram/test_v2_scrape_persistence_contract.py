from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any, cast

import pytest
from kiizama_scrape_core.ig_scraper_v2.apify import ApifyInstagramProfileScraper
from kiizama_scrape_core.ig_scraper_v2.metrics import calculate_metrics_from_scrape
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramMetricsSchema,
    InstagramPostMetricsSchema,
    InstagramPostSchema,
    InstagramProfileSchema,
    InstagramReelMetricsSchema,
    InstagramReelSchema,
    InstagramSuggestedUserSchema,
)
from kiizama_scrape_core.ig_scraper_v2.service import build_batch_scrape_summary
from sqlmodel import Session, delete

from app.crud.profile_snapshots import list_profile_snapshots_full
from app.features.ig_scraper_v2_runtime import BackendInstagramScrapePersistenceV2
from app.models import (
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
)


def _clear_instagram_tables(db: Session) -> None:
    db.exec(delete(IgProfileSnapshot))
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()


def _build_worker_response() -> InstagramBatchScrapeResponse:
    result_payload = {
        "user": {
            "id": "apify-creator-123",
            "username": "parity_creator",
            "full_name": "Parity Creator",
            "profile_pic_url": "https://cdn.example.test/parity-creator.jpg",
            "biography": "Parity creator bio",
            "is_private": False,
            "is_verified": True,
            "follower_count": 1200,
            "following_count": 110,
            "media_count": 60,
            "external_url": "https://example.test/parity",
            "bio_links": [{"title": "Site", "url": "https://example.test/parity-link"}],
            "category_name": "Creators",
        },
        "posts": [
            {
                "code": "PARITYPOST1",
                "caption_text": "Parity post one #parity",
                "like_count": 111,
                "comment_count": 11,
                "media_type": 1,
                "product_type": None,
                "usertags": ["friend_one", "friend_two"],
            },
            {
                "code": "PARITYPOST2",
                "caption_text": "Parity post two",
                "like_count": 222,
                "comment_count": 22,
                "media_type": 2,
                "product_type": None,
                "usertags": [],
            },
        ],
        "recommended_users": [
            {
                "username": "related_parity",
                "id": "related-123",
                "full_name": "Related Parity",
                "profile_pic_url": "https://cdn.example.test/related.jpg",
            }
        ],
        "success": True,
    }
    result_payload["metrics"] = calculate_metrics_from_scrape(result_payload)

    return InstagramBatchScrapeResponse(
        results={
            "parity_creator": InstagramBatchProfileResult.model_validate(result_payload)
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
    )


def _build_apify_normalized_response() -> InstagramBatchScrapeResponse:
    scraper = ApifyInstagramProfileScraper(
        api_token="test-token",
        usernames=["parity_creator"],
    )
    response = scraper._build_response(
        [
            {
                "id": "apify-creator-123",
                "username": "parity_creator",
                "fullName": "Parity Creator",
                "biography": "Parity creator bio",
                "private": False,
                "verified": True,
                "profilePicUrl": "https://cdn.example.test/parity-creator.jpg",
                "externalUrl": "https://example.test/parity",
                "followersCount": 1200,
                "followsCount": 110,
                "postsCount": 60,
                "externalUrls": [
                    {
                        "title": "Site",
                        "url": "https://example.test/parity-link",
                    }
                ],
                "businessCategoryName": "Creators",
                "latestPosts": [
                    {
                        "shortCode": "PARITYPOST1",
                        "caption": "Parity post one #parity",
                        "commentsCount": 11,
                        "likesCount": 111,
                        "taggedUsers": [
                            {"username": "friend_one"},
                            {"username": "friend_two"},
                        ],
                        "type": "Image",
                    },
                    {
                        "shortCode": "PARITYPOST2",
                        "caption": "Parity post two",
                        "commentsCount": 22,
                        "likesCount": 222,
                        "taggedUsers": [],
                        "type": "Video",
                    },
                ],
                "relatedProfiles": [
                    {
                        "username": "related_parity",
                        "id": "related-123",
                        "fullName": "Related Parity",
                        "profilePicUrl": "https://cdn.example.test/related.jpg",
                    }
                ],
            }
        ]
    )
    return InstagramBatchScrapeResponse.model_validate(response)


def _extract_common_persisted_fields(snapshot: dict[str, Any]) -> dict[str, Any]:
    profile = snapshot["profile"]
    posts_document = snapshot["posts"][0]
    metrics = snapshot["metrics"]

    return {
        "profile": {
            "ig_id": profile["ig_id"],
            "username": profile["username"],
            "full_name": profile["full_name"],
            "biography": profile["biography"],
            "is_private": profile["is_private"],
            "is_verified": profile["is_verified"],
            "profile_pic_url": profile["profile_pic_url"],
            "external_url": profile["external_url"],
            "follower_count": profile["follower_count"],
            "following_count": profile["following_count"],
            "media_count": profile["media_count"],
            "bio_links": profile["bio_links"],
        },
        "posts": [
            {
                "code": post["code"],
                "caption_text": post["caption_text"],
                "comment_count": post["comment_count"],
                "like_count": post["like_count"],
                "media_type": post["media_type"],
                "product_type": post["product_type"],
                "usertags": post["usertags"],
            }
            for post in posts_document["posts"]
        ],
        "metrics": {
            "post_metrics": metrics["post_metrics"],
            "overall_post_engagement_rate": metrics["overall_post_engagement_rate"],
        },
    }


@pytest.fixture(scope="module", autouse=True)
def ensure_instagram_tables(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgProfile).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgPostsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgReelsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgMetrics).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgProfileSnapshot).__table__.create(bind=bind, checkfirst=True)
    _clear_instagram_tables(db)
    yield
    _clear_instagram_tables(db)


def test_v2_batch_response_persists_with_current_instagram_repository(
    db: Session,
) -> None:
    persistence = BackendInstagramScrapePersistenceV2(
        profiles_collection=db,
        posts_collection=db,
        reels_collection=db,
        metrics_collection=db,
        snapshots_collection=db,
    )
    response = InstagramBatchScrapeResponse(
        results={
            "v2_creator": InstagramBatchProfileResult(
                user=InstagramProfileSchema(
                    id="v2-ig-123",
                    username="v2_creator",
                    full_name="V2 Creator",
                    profile_pic_url="https://cdn.example.test/v2-creator.jpg",
                    biography="V2 bio",
                    is_private=False,
                    is_verified=True,
                    follower_count=1000,
                    following_count=100,
                    media_count=50,
                    external_url="https://example.test/v2",
                    bio_links=[{"title": "Site", "url": "https://example.test"}],
                ),
                recommended_users=[InstagramSuggestedUserSchema(username="related_v2")],
                posts=[
                    InstagramPostSchema(
                        code="V2POST1",
                        caption_text="V2 post",
                        like_count=10,
                        comment_count=2,
                        media_type=1,
                        product_type="feed",
                    )
                ],
                reels=[
                    InstagramReelSchema(
                        code="V2REEL1",
                        play_count=100,
                        like_count=20,
                        comment_count=3,
                        media_type=2,
                        product_type="clips",
                    )
                ],
                success=True,
                metrics=InstagramMetricsSchema(
                    post_metrics=InstagramPostMetricsSchema(
                        total_posts=1,
                        total_likes=10,
                        total_comments=2,
                        avg_likes=10.0,
                        avg_comments=2.0,
                        avg_engagement_rate=0.01,
                    ),
                    reel_metrics=InstagramReelMetricsSchema(
                        total_reels=1,
                        total_plays=100,
                        avg_plays=100.0,
                        avg_reel_likes=20.0,
                        avg_reel_comments=3.0,
                    ),
                    overall_post_engagement_rate=0.012,
                    reel_engagement_rate_on_plays=0.23,
                ),
                ai_categories=["Fitness"],
                ai_roles=["Lifestyle"],
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
    )

    persisted = asyncio.run(persistence.persist_scrape_results(response))
    summary = build_batch_scrape_summary(
        InstagramBatchScrapeRequest(usernames=["v2_creator"]),
        InstagramBatchScrapeRequest(usernames=["v2_creator"]),
        persisted,
    )

    snapshots = list_profile_snapshots_full(
        db,
        skip=0,
        limit=10,
        usernames=["v2_creator"],
    )

    assert persisted.error is None
    assert summary.usernames[0].status == "success"
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot["profile"]["username"] == "v2_creator"
    assert snapshot["profile"]["ai_categories"] == ["Fitness"]
    assert snapshot["posts"][0]["posts"][0]["code"] == "V2POST1"
    assert snapshot["reels"][0]["reels"][0]["code"] == "V2REEL1"
    assert snapshot["metrics"]["post_metrics"]["total_posts"] == 1


def test_apify_and_worker_persist_same_common_instagram_fields(
    db: Session,
) -> None:
    persistence = BackendInstagramScrapePersistenceV2(
        profiles_collection=db,
        posts_collection=db,
        reels_collection=db,
        metrics_collection=db,
        snapshots_collection=db,
    )

    worker_response = _build_worker_response()
    persisted_worker = asyncio.run(persistence.persist_scrape_results(worker_response))
    assert persisted_worker.error is None
    worker_snapshots = list_profile_snapshots_full(
        db,
        skip=0,
        limit=10,
        usernames=["parity_creator"],
    )
    assert len(worker_snapshots) == 1
    worker_common_fields = _extract_common_persisted_fields(worker_snapshots[0])

    _clear_instagram_tables(db)

    apify_response = _build_apify_normalized_response()
    persisted_apify = asyncio.run(persistence.persist_scrape_results(apify_response))
    assert persisted_apify.error is None
    apify_snapshots = list_profile_snapshots_full(
        db,
        skip=0,
        limit=10,
        usernames=["parity_creator"],
    )
    assert len(apify_snapshots) == 1
    apify_common_fields = _extract_common_persisted_fields(apify_snapshots[0])

    assert worker_common_fields == apify_common_fields
