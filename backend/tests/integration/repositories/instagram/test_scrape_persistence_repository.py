from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from kiizama_scrape_core.ig_scraper.schemas import (
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
)
from kiizama_scrape_core.ig_scraper.service import build_batch_scrape_summary
from sqlmodel import Session, delete, select

from app.crud.profile_snapshots import list_profile_snapshots_full
from app.features.ig_scraper_runtime import BackendInstagramScrapePersistence
from app.models import (
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
)


def _persistence(db: Session) -> BackendInstagramScrapePersistence:
    return BackendInstagramScrapePersistence(
        profiles_collection=db,
        posts_collection=db,
        reels_collection=db,
        metrics_collection=db,
        snapshots_collection=db,
    )


def _create_profile(
    db: Session,
    *,
    ig_id: str,
    username: str,
) -> IgProfile:
    now = datetime.now(UTC)
    profile = IgProfile(
        ig_id=ig_id,
        username=username,
        full_name=f"{username} Creator",
        biography="Creator bio",
        is_private=False,
        is_verified=False,
        profile_pic_url=f"https://cdn.example.com/{username}.jpg",
        external_url=None,
        follower_count=100,
        following_count=10,
        media_count=5,
        bio_links=[],
        ai_categories=[],
        ai_roles=[],
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _scrape_response(
    *,
    ig_id: str,
    username: str,
    requested_username: str | None = None,
) -> InstagramBatchScrapeResponse:
    result_key = requested_username or username
    return InstagramBatchScrapeResponse(
        results={
            result_key: InstagramBatchProfileResult(
                user=InstagramProfileSchema(
                    id=ig_id,
                    username=username,
                    full_name=f"{username} Creator",
                    profile_pic_url=f"https://cdn.example.com/{username}.jpg",
                    biography=f"{username} bio",
                    is_private=False,
                    is_verified=False,
                    follower_count=200,
                    following_count=20,
                    media_count=10,
                ),
                success=True,
                metrics=InstagramMetricsSchema(),
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
        error=None,
    )


def _get_profiles_by_ig_id(db: Session) -> dict[str, IgProfile]:
    return {profile.ig_id: profile for profile in db.exec(select(IgProfile)).all()}


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
    snapshots = list_profile_snapshots_full(
        db,
        skip=0,
        limit=10,
        usernames=["creator_alpha"],
    )

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot["profile"]["username"] == "creator_alpha"
    assert snapshot["profile"]["ai_categories"] == ["Fitness"]
    assert snapshot["posts"][0]["posts"][0]["code"] == "POST1"
    assert snapshot["reels"][0]["reels"][0]["code"] == "REEL1"
    assert snapshot["metrics"]["post_metrics"]["total_posts"] == 1


def test_backend_instagram_scrape_persistence_updates_username_by_ig_id(
    db: Session,
) -> None:
    persistence = _persistence(db)
    profile = _create_profile(db, ig_id="rename-ig-123", username="kiko1")
    existing_snapshot = IgProfileSnapshot(profile_id=profile.id)
    db.add(existing_snapshot)
    db.commit()
    db.refresh(existing_snapshot)

    persisted = asyncio.run(
        persistence.persist_scrape_results(
            _scrape_response(
                ig_id="rename-ig-123",
                username="kiko6",
                requested_username="kiko6",
            )
        )
    )

    assert persisted.error is None
    profiles = db.exec(
        select(IgProfile).where(IgProfile.ig_id == "rename-ig-123")
    ).all()
    assert len(profiles) == 1
    assert profiles[0].id == profile.id
    assert profiles[0].username == "kiko6"
    refreshed_snapshot = db.get(IgProfileSnapshot, existing_snapshot.id)
    assert refreshed_snapshot is not None
    assert refreshed_snapshot.profile_id == profile.id


def test_backend_instagram_scrape_persistence_parks_username_owner_when_ig_reclaims_handle(
    db: Session,
) -> None:
    persistence = _persistence(db)
    confirmed_profile = _create_profile(
        db, ig_id="claim-ig-123", username="claim_kiko1"
    )
    displaced_profile = _create_profile(
        db, ig_id="claim-ig-456", username="claim_kiko6"
    )

    persisted = asyncio.run(
        persistence.persist_scrape_results(
            _scrape_response(
                ig_id="claim-ig-123",
                username="claim_kiko6",
                requested_username="claim_kiko6",
            )
        )
    )

    assert persisted.error is None
    profiles = _get_profiles_by_ig_id(db)
    assert profiles["claim-ig-123"].id == confirmed_profile.id
    assert profiles["claim-ig-123"].username == "claim_kiko6"
    assert profiles["claim-ig-456"].id == displaced_profile.id
    assert profiles["claim-ig-456"].username == "__stale__claim-ig-456__claim_kiko6"


def test_backend_instagram_scrape_persistence_restores_stale_profile_organically(
    db: Session,
) -> None:
    persistence = _persistence(db)
    stale_profile = _create_profile(
        db,
        ig_id="restore-ig-456",
        username="__stale__restore-ig-456__restore_kiko6",
    )

    persisted = asyncio.run(
        persistence.persist_scrape_results(
            _scrape_response(
                ig_id="restore-ig-456",
                username="restore_kiko7",
                requested_username="restore_kiko7",
            )
        )
    )

    assert persisted.error is None
    profiles = db.exec(
        select(IgProfile).where(IgProfile.ig_id == "restore-ig-456")
    ).all()
    assert len(profiles) == 1
    assert profiles[0].id == stale_profile.id
    assert profiles[0].username == "restore_kiko7"


def test_backend_instagram_scrape_persistence_adds_profile_id_suffix_when_stale_username_exists(
    db: Session,
) -> None:
    persistence = _persistence(db)
    _create_profile(db, ig_id="suffix-ig-123", username="suffix_kiko1")
    displaced_profile = _create_profile(
        db, ig_id="suffix-ig-456", username="suffix_kiko6"
    )
    existing_stale_owner = _create_profile(
        db,
        ig_id="suffix-ig-789",
        username="__stale__suffix-ig-456__suffix_kiko6",
    )

    persisted = asyncio.run(
        persistence.persist_scrape_results(
            _scrape_response(
                ig_id="suffix-ig-123",
                username="suffix_kiko6",
                requested_username="suffix_kiko6",
            )
        )
    )

    assert persisted.error is None
    profiles = _get_profiles_by_ig_id(db)
    expected_suffix = str(displaced_profile.id).replace("-", "")[:12]
    assert profiles["suffix-ig-123"].username == "suffix_kiko6"
    assert (
        profiles["suffix-ig-456"].username
        == f"__stale__suffix-ig-456__suffix_kiko6__{expected_suffix}"
    )
    assert profiles["suffix-ig-789"].id == existing_stale_owner.id
    assert profiles["suffix-ig-789"].username == "__stale__suffix-ig-456__suffix_kiko6"


def test_backend_instagram_scrape_persistence_marks_profile_failed_on_write_error(
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
            "broken_creator": InstagramBatchProfileResult(
                user=InstagramProfileSchema(
                    id="999",
                    username="broken_creator",
                    profile_pic_url=None,
                ),
                success=True,
                metrics=InstagramMetricsSchema(),
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
        error=None,
    )

    persisted = asyncio.run(persistence.persist_scrape_results(response))
    summary = build_batch_scrape_summary(
        InstagramBatchScrapeRequest(usernames=["broken_creator"]),
        InstagramBatchScrapeRequest(usernames=["broken_creator"]),
        persisted,
    )

    assert persisted.results["broken_creator"].success is False
    assert persisted.results["broken_creator"].error == "Missing profile_pic_url"
    assert (
        persisted.error == "Persistence errors: broken_creator: Missing profile_pic_url"
    )
    assert summary.usernames[0].status == "failed"
