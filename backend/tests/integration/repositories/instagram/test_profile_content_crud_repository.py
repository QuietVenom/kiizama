from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlmodel import Session, delete

from app.crud.metrics import (
    create_metrics,
    delete_metrics,
    get_metrics,
    list_metrics,
    replace_metrics,
    update_metrics,
)
from app.crud.posts import (
    create_post,
    delete_post,
    get_post,
    list_posts,
    replace_post,
    update_post,
)
from app.crud.profile import (
    create_profile,
    delete_profile,
    get_existing_profile_usernames,
    get_profile,
    get_profile_by_ig_id,
    get_profile_by_username,
    get_profiles_by_usernames,
    list_profiles,
    replace_profile,
    update_profile,
)
from app.crud.reels import (
    create_reel,
    delete_reel,
    get_reel,
    list_reels,
    replace_reel,
    update_reel,
)
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
    Reel,
    ReelItem,
    ReelMetrics,
    UpdateMetrics,
    UpdatePost,
    UpdateProfile,
    UpdateReel,
)


@pytest.fixture(scope="module", autouse=True)
def ensure_instagram_content_tables(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgProfile).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgPostsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgReelsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgMetrics).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgProfileSnapshot).__table__.create(bind=bind, checkfirst=True)
    _clear_instagram_content(db)
    yield
    _clear_instagram_content(db)


def _clear_instagram_content(db: Session) -> None:
    db.exec(delete(IgProfileSnapshot))
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()


def _run[T](value: T) -> T:
    return value


def _profile(
    *,
    username: str | None = None,
    ig_id: str | None = None,
    follower_count: int = 1_000,
) -> Profile:
    suffix = uuid4().hex
    resolved_username = username or f"creator_{suffix}"
    return Profile(
        ig_id=ig_id or f"ig-{suffix}",
        username=resolved_username,
        full_name=f"{resolved_username} Full",
        biography="Creator biography",
        is_private=False,
        is_verified=True,
        profile_pic_url=cast(
            Any,
            f"https://images.cdninstagram.com/{resolved_username}.jpg",
        ),
        external_url=cast(Any, f"https://example.com/{resolved_username}"),
        updated_date=datetime.now(UTC),
        follower_count=follower_count,
        following_count=100,
        media_count=20,
        bio_links=[],
        ai_categories=["Beauty"],
        ai_roles=["Creator"],
    )


def _metrics(
    *,
    total_posts: int = 1,
    overall_post_engagement_rate: float = 0.07,
) -> Metrics:
    return Metrics(
        post_metrics=PostMetrics(
            total_posts=total_posts,
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
            total_plays=3_200,
            avg_plays=3_200.0,
            avg_reel_likes=180.0,
            avg_reel_comments=14.0,
        ),
        overall_post_engagement_rate=overall_post_engagement_rate,
        reel_engagement_rate_on_plays=0.060625,
    )


def test_profiles_crud_lookups_and_duplicate_constraints_persist_in_postgres(
    db: Session,
) -> None:
    # Arrange
    profile_payload = _profile(username=f"creator_{uuid4().hex}", ig_id=uuid4().hex)

    # Act
    created = _run(create_profile(db, profile_payload))
    assert created is not None
    profile_id = created["_id"]
    by_id = _run(get_profile(db, profile_id))
    by_username = _run(get_profile_by_username(db, profile_payload.username))
    by_ig_id = _run(get_profile_by_ig_id(db, profile_payload.ig_id))
    matching_profiles = _run(get_profiles_by_usernames(db, [profile_payload.username]))
    existing_usernames = _run(
        get_existing_profile_usernames(db, [profile_payload.username, "missing"])
    )
    updated = _run(
        update_profile(
            db,
            profile_id,
            UpdateProfile(
                username=f"{profile_payload.username}_updated",
                follower_count=2_000,
            ),
        )
    )
    replaced = _run(
        replace_profile(
            db,
            profile_id,
            _profile(username=f"replacement_{uuid4().hex}", ig_id=uuid4().hex),
        )
    )
    listed = _run(list_profiles(db, skip=0, limit=10))
    deleted = _run(delete_profile(db, profile_id))

    # Assert
    assert by_id is not None
    assert by_username is not None
    assert by_username["_id"] == profile_id
    assert by_ig_id is not None
    assert by_ig_id["_id"] == profile_id
    assert [profile["_id"] for profile in matching_profiles] == [profile_id]
    assert existing_usernames == [profile_payload.username]
    assert updated is not None
    assert updated["follower_count"] == 2_000
    assert replaced is not None
    assert replaced["username"].startswith("replacement_")
    assert profile_id in {profile["_id"] for profile in listed}
    assert deleted is not None
    assert deleted["_id"] == profile_id
    assert _run(get_profile(db, profile_id)) is None
    assert _run(get_profile(db, "not-a-uuid")) is None
    assert _run(update_profile(db, str(uuid4()), UpdateProfile(biography="x"))) is None

    duplicate_username = f"duplicate_{uuid4().hex}"
    _run(create_profile(db, _profile(username=duplicate_username, ig_id=uuid4().hex)))
    with pytest.raises(HTTPException) as exc_info:
        _run(
            create_profile(
                db,
                _profile(username=duplicate_username, ig_id=uuid4().hex),
            )
        )
    assert exc_info.value.status_code == 409


def test_posts_reels_and_metrics_crud_handles_not_found_and_invalid_ids(
    db: Session,
) -> None:
    # Arrange
    profile = _run(create_profile(db, _profile()))
    assert profile is not None
    profile_id = str(profile["_id"])
    now = datetime.now(UTC)

    # Act
    post = _run(
        create_post(
            db,
            Post(
                profile_id=profile_id,
                posts=[PostItem(code="POST1", caption_text="first")],
                updated_at=now,
            ),
        )
    )
    reel = _run(
        create_reel(
            db,
            Reel(
                profile_id=profile_id,
                reels=[ReelItem(code="REEL1", play_count=10)],
                updated_at=now,
            ),
        )
    )
    metrics = _run(create_metrics(db, _metrics()))

    # Assert
    assert post is not None
    assert reel is not None
    assert metrics is not None
    assert _run(get_post(db, post["_id"])) == post
    assert _run(get_reel(db, reel["_id"])) == reel
    assert _run(get_metrics(db, metrics["_id"])) == metrics
    assert post["_id"] in {item["_id"] for item in _run(list_posts(db, 0, 10))}
    assert reel["_id"] in {item["_id"] for item in _run(list_reels(db, 0, 10))}
    assert metrics["_id"] in {item["_id"] for item in _run(list_metrics(db, 0, 10))}

    updated_post = _run(
        update_post(
            db,
            post["_id"],
            UpdatePost(posts=[PostItem(code="POST2", caption_text="updated")]),
        )
    )
    updated_reel = _run(
        update_reel(
            db,
            reel["_id"],
            UpdateReel(reels=[ReelItem(code="REEL2", play_count=20)]),
        )
    )
    updated_metrics = _run(
        update_metrics(
            db,
            metrics["_id"],
            UpdateMetrics(overall_post_engagement_rate=0.5),
        )
    )
    assert updated_post is not None
    assert updated_post["posts"][0]["code"] == "POST2"
    assert updated_reel is not None
    assert updated_reel["reels"][0]["code"] == "REEL2"
    assert updated_metrics is not None
    assert updated_metrics["overall_post_engagement_rate"] == 0.5

    replaced_post = _run(
        replace_post(
            db,
            post["_id"],
            Post(
                profile_id=profile_id,
                posts=[PostItem(code="POST3", caption_text="replaced")],
                updated_at=now,
            ),
        )
    )
    replaced_reel = _run(
        replace_reel(
            db,
            reel["_id"],
            Reel(
                profile_id=profile_id,
                reels=[ReelItem(code="REEL3", play_count=30)],
                updated_at=now,
            ),
        )
    )
    replaced_metrics = _run(
        replace_metrics(db, metrics["_id"], _metrics(total_posts=3))
    )
    assert replaced_post is not None
    assert replaced_post["posts"][0]["code"] == "POST3"
    assert replaced_reel is not None
    assert replaced_reel["reels"][0]["code"] == "REEL3"
    assert replaced_metrics is not None
    assert replaced_metrics["post_metrics"]["total_posts"] == 3

    assert _run(get_post(db, "not-a-uuid")) is None
    assert _run(get_reel(db, "not-a-uuid")) is None
    assert _run(get_metrics(db, "not-a-uuid")) is None
    assert _run(update_post(db, str(uuid4()), UpdatePost(posts=[]))) is None
    assert _run(update_reel(db, str(uuid4()), UpdateReel(reels=[]))) is None
    assert _run(update_metrics(db, str(uuid4()), UpdateMetrics())) is None
    assert _run(delete_post(db, post["_id"])) is not None
    assert _run(delete_reel(db, reel["_id"])) is not None
    assert _run(delete_metrics(db, metrics["_id"])) is not None
    assert _run(get_post(db, post["_id"])) is None
    assert _run(get_reel(db, reel["_id"])) is None
    assert _run(get_metrics(db, metrics["_id"])) is None
