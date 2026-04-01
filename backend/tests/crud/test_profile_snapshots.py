import asyncio
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import event
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


@contextmanager
def count_sql_queries(db: Session) -> Generator[SimpleNamespace, None, None]:
    counter = SimpleNamespace(count=0)
    bind = db.get_bind()

    def increment_query_count(*_args: Any, **_kwargs: Any) -> None:
        counter.count += 1

    event.listen(bind, "before_cursor_execute", increment_query_count)
    try:
        yield counter
    finally:
        event.remove(bind, "before_cursor_execute", increment_query_count)


def persist_snapshot_tree(
    db: Session,
    *,
    ig_id: str,
    username: str,
    scraped_at: datetime,
    post_code: str,
    reel_code: str,
) -> dict[str, Any]:
    profile = asyncio.run(
        create_profile(
            db,
            Profile(
                ig_id=ig_id,
                username=username,
                full_name=f"{username} Full Name",
                biography=f"{username} biography",
                is_private=False,
                is_verified=False,
                profile_pic_url=cast(Any, f"https://cdn.example.com/{username}.jpg"),
                external_url=cast(Any, f"https://example.com/{username}"),
                updated_date=scraped_at,
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

    return persist_snapshot_for_profile(
        db,
        profile_id=str(profile["_id"]),
        scraped_at=scraped_at,
        post_code=post_code,
        reel_code=reel_code,
    )


def persist_snapshot_for_profile(
    db: Session,
    *,
    profile_id: str,
    scraped_at: datetime,
    post_code: str,
    reel_code: str,
) -> dict[str, Any]:
    posts = asyncio.run(
        create_post(
            db,
            Post(
                profile_id=profile_id,
                posts=[
                    PostItem(
                        code=post_code,
                        caption_text=f"{post_code} caption",
                        media_type=1,
                        product_type="feed",
                    )
                ],
                updated_at=scraped_at,
            ),
        )
    )
    assert posts is not None

    reels = asyncio.run(
        create_reel(
            db,
            Reel(
                profile_id=profile_id,
                reels=[
                    ReelItem(
                        code=reel_code,
                        media_type=2,
                        product_type="clips",
                        play_count=3200,
                    )
                ],
                updated_at=scraped_at,
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
                profile_id=profile_id,
                post_ids=[str(posts["_id"])],
                reel_ids=[str(reels["_id"])],
                metrics_id=str(metrics["_id"]),
                scraped_at=scraped_at,
            ),
        )
    )
    assert snapshot is not None
    return {
        "snapshot": snapshot,
        "profile_id": profile_id,
        "posts": posts,
        "reels": reels,
        "metrics": metrics,
    }


def test_list_profile_snapshots_full_reads_expanded_snapshot_from_postgres(
    db: Session,
) -> None:
    now = datetime.now(timezone.utc)
    persisted = persist_snapshot_tree(
        db,
        ig_id="1234567890",
        username="creator_beta",
        scraped_at=now,
        post_code="POST_BETA_1",
        reel_code="REEL_BETA_1",
    )

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
    assert expanded_snapshot["_id"] == persisted["snapshot"]["_id"]
    assert expanded_snapshot["profile"]["username"] == "creator_beta"
    assert expanded_snapshot["posts"][0]["posts"][0]["code"] == "POST_BETA_1"
    assert expanded_snapshot["reels"][0]["reels"][0]["code"] == "REEL_BETA_1"
    assert expanded_snapshot["metrics"]["overall_post_engagement_rate"] == 0.07
    assert expanded_snapshot["metrics"]["reel_engagement_rate_on_plays"] == 0.060625


def test_list_profile_snapshots_full_applies_limit_per_username(db: Session) -> None:
    first_profile_snapshot = persist_snapshot_tree(
        db,
        ig_id="2234567890",
        username="creator_gamma",
        scraped_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
        post_code="POST_GAMMA_NEW",
        reel_code="REEL_GAMMA_NEW",
    )
    persist_snapshot_for_profile(
        db,
        profile_id=first_profile_snapshot["profile_id"],
        scraped_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        post_code="POST_GAMMA_OLD",
        reel_code="REEL_GAMMA_OLD",
    )
    persist_snapshot_tree(
        db,
        ig_id="3234567890",
        username="creator_delta",
        scraped_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        post_code="POST_DELTA",
        reel_code="REEL_DELTA",
    )

    expanded_snapshots = asyncio.run(
        list_profile_snapshots_full(
            db,
            skip=0,
            limit=1,
            usernames=["creator_gamma", "creator_delta"],
        )
    )

    assert [snapshot["profile"]["username"] for snapshot in expanded_snapshots] == [
        "creator_gamma",
        "creator_delta",
    ]
    assert [
        snapshot["posts"][0]["posts"][0]["code"] for snapshot in expanded_snapshots
    ] == [
        "POST_GAMMA_NEW",
        "POST_DELTA",
    ]


def test_list_profile_snapshots_full_uses_constant_query_count(db: Session) -> None:
    first_profile_snapshot = persist_snapshot_tree(
        db,
        ig_id="4234567890",
        username="creator_epsilon",
        scraped_at=datetime(2024, 2, 3, tzinfo=timezone.utc),
        post_code="POST_EPSILON_NEW",
        reel_code="REEL_EPSILON_NEW",
    )
    persist_snapshot_for_profile(
        db,
        profile_id=first_profile_snapshot["profile_id"],
        scraped_at=datetime(2024, 2, 2, tzinfo=timezone.utc),
        post_code="POST_EPSILON_MID",
        reel_code="REEL_EPSILON_MID",
    )
    persist_snapshot_for_profile(
        db,
        profile_id=first_profile_snapshot["profile_id"],
        scraped_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        post_code="POST_EPSILON_OLD",
        reel_code="REEL_EPSILON_OLD",
    )
    persist_snapshot_tree(
        db,
        ig_id="5234567890",
        username="creator_zeta",
        scraped_at=datetime(2024, 2, 4, tzinfo=timezone.utc),
        post_code="POST_ZETA",
        reel_code="REEL_ZETA",
    )
    db.expunge_all()

    with count_sql_queries(db) as query_counter:
        expanded_snapshots = asyncio.run(
            list_profile_snapshots_full(
                db,
                skip=0,
                limit=3,
                usernames=["creator_epsilon", "creator_zeta"],
            )
        )

    assert len(expanded_snapshots) == 4
    assert query_counter.count <= 6
