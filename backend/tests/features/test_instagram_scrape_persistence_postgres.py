from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any, cast

import pytest
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeResponse,
    InstagramMetricsSchema,
    InstagramPostMetricsSchema,
    InstagramPostSchema,
    InstagramProfileSchema,
    InstagramReelMetricsSchema,
    InstagramReelSchema,
)
from sqlmodel import Session, delete

from app.crud.profile_snapshots import list_profile_snapshots_full
from app.features.ig_scraper_runtime import BackendInstagramScrapePersistence
from app.models import (
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
)


@pytest.fixture(scope="module", autouse=True)
def ensure_instagram_tables(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgProfile).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgPostsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgReelsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgMetrics).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgProfileSnapshot).__table__.create(bind=bind, checkfirst=True)
    db.exec(delete(IgProfileSnapshot))
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()
    yield
    db.exec(delete(IgProfileSnapshot))
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()


def test_backend_instagram_scrape_persistence_writes_full_snapshot_to_postgres(
    db: Session,
) -> None:
    persistence = BackendInstagramScrapePersistence(
        profiles_collection=db,
        posts_collection=db,
        reels_collection=db,
        metrics_collection=db,
        snapshots_collection=db,
    )

    response = InstagramBatchScrapeResponse(
        results={
            "creator_alpha": InstagramBatchProfileResult(
                user=InstagramProfileSchema(
                    id="1234567890",
                    username="creator_alpha",
                    full_name="Creator Alpha",
                    profile_pic_url="https://cdn.example.com/creator-alpha.jpg",
                    biography="Fitness creator",
                    is_private=False,
                    is_verified=True,
                    follower_count=1000,
                    following_count=100,
                    media_count=50,
                    external_url="https://example.com/creator-alpha",
                    bio_links=[{"title": "Site", "url": "https://example.com"}],
                ),
                posts=[
                    InstagramPostSchema(
                        code="POST1",
                        caption_text="Hello world",
                        like_count=10,
                        comment_count=2,
                        media_type=1,
                        product_type="feed",
                    )
                ],
                reels=[
                    InstagramReelSchema(
                        code="REEL1",
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
                        avg_engagement_rate=0.1,
                        hashtags_per_post=0.0,
                        mentions_per_post=0.0,
                    ),
                    reel_metrics=InstagramReelMetricsSchema(
                        total_reels=1,
                        total_plays=100,
                        avg_plays=100.0,
                        avg_reel_likes=20.0,
                        avg_reel_comments=3.0,
                    ),
                    overall_post_engagement_rate=0.2,
                    reel_engagement_rate_on_plays=0.23,
                ),
                ai_categories=["Fitness"],
                ai_roles=["Lifestyle"],
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
        error=None,
    )

    persisted = asyncio.run(persistence.persist_scrape_results(response))

    assert persisted.error is None
    snapshots = asyncio.run(
        list_profile_snapshots_full(
            db,
            skip=0,
            limit=10,
            usernames=["creator_alpha"],
        )
    )

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot["profile"]["username"] == "creator_alpha"
    assert snapshot["profile"]["ai_categories"] == ["Fitness"]
    assert snapshot["posts"][0]["posts"][0]["code"] == "POST1"
    assert snapshot["reels"][0]["reels"][0]["code"] == "REEL1"
    assert snapshot["metrics"]["post_metrics"]["total_posts"] == 1
