import asyncio
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from sqlmodel import Session, delete

from app.crud.metrics import create_metrics
from app.crud.posts import create_post
from app.crud.profile import create_profile
from app.crud.profile_snapshots import (
    create_profile_snapshot,
    list_profile_snapshots_full,
)
from app.crud.reels import create_reel
from app.models import (
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
)
from app.schemas import (
    Metrics,
    Post,
    PostItem,
    PostMetrics,
    Profile,
    ProfileSnapshot,
    Reel,
    ReelItem,
    ReelMetrics,
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


def test_list_profile_snapshots_full_reads_expanded_snapshot_from_postgres(
    db: Session,
) -> None:
    now = datetime.now(timezone.utc)

    profile = asyncio.run(
        create_profile(
            db,
            Profile(
                ig_id="1234567890",
                username="creator_beta",
                full_name="Creator Beta",
                biography="Travel creator",
                is_private=False,
                is_verified=False,
                profile_pic_url=cast(Any, "https://cdn.example.com/creator-beta.jpg"),
                external_url=cast(Any, "https://example.com/creator-beta"),
                updated_date=now,
                follower_count=2500,
                following_count=150,
                media_count=80,
                bio_links=[],
                ai_categories=["Travel"],
                ai_roles=["Creator"],
            ),
        )
    )
    assert profile is not None

    posts = asyncio.run(
        create_post(
            db,
            Post(
                profile_id=str(profile["_id"]),
                posts=[
                    PostItem(
                        code="POST_BETA_1",
                        caption_text="A day in Tulum",
                        media_type=1,
                        product_type="feed",
                    )
                ],
                updated_at=now,
            ),
        )
    )
    assert posts is not None

    reels = asyncio.run(
        create_reel(
            db,
            Reel(
                profile_id=str(profile["_id"]),
                reels=[
                    ReelItem(
                        code="REEL_BETA_1",
                        media_type=2,
                        product_type="clips",
                        play_count=3200,
                    )
                ],
                updated_at=now,
            ),
        )
    )
    assert reels is not None

    metrics = asyncio.run(
        create_metrics(
            db,
            Metrics(
                post_metrics=PostMetrics(
                    total_posts=1,
                    total_likes=150,
                    total_comments=12,
                    avg_likes=150.0,
                    avg_comments=12.0,
                    avg_engagement_rate=0.05,
                    hashtags_per_post=1.0,
                    mentions_per_post=0.0,
                ),
                reel_metrics=ReelMetrics(
                    total_reels=1,
                    total_plays=3200,
                    avg_plays=3200.0,
                    avg_reel_likes=180.0,
                    avg_reel_comments=14.0,
                ),
                overall_post_engagement_rate=0.07,
                reel_engagement_rate_on_plays=0.060625,
            ),
        )
    )
    assert metrics is not None

    snapshot = asyncio.run(
        create_profile_snapshot(
            db,
            ProfileSnapshot(
                profile_id=str(profile["_id"]),
                post_ids=[str(posts["_id"])],
                reel_ids=[str(reels["_id"])],
                metrics_id=str(metrics["_id"]),
                scraped_at=now,
            ),
        )
    )
    assert snapshot is not None

    expanded_snapshots = asyncio.run(
        list_profile_snapshots_full(
            db,
            skip=0,
            limit=10,
            usernames=["creator_beta"],
        )
    )

    assert len(expanded_snapshots) == 1
    expanded_snapshot = expanded_snapshots[0]
    assert expanded_snapshot["_id"] == snapshot["_id"]
    assert expanded_snapshot["profile"]["username"] == "creator_beta"
    assert expanded_snapshot["posts"][0]["posts"][0]["code"] == "POST_BETA_1"
    assert expanded_snapshot["reels"][0]["reels"][0]["code"] == "REEL_BETA_1"
    assert expanded_snapshot["metrics"]["overall_post_engagement_rate"] == 0.07
    assert expanded_snapshot["metrics"]["reel_engagement_rate_on_plays"] == 0.060625
