from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.crud.metrics import create_metrics
from app.crud.posts import create_post
from app.crud.profile_snapshots import create_profile_snapshot
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


def _profile_payload(
    *,
    ig_id: str,
    username: str,
    full_name: str,
    biography: str,
    follower_count: int,
    ai_categories: list[str],
    ai_roles: list[str],
) -> dict[str, object]:
    return {
        "ig_id": ig_id,
        "username": username,
        "full_name": full_name,
        "biography": biography,
        "is_private": False,
        "is_verified": True,
        "profile_pic_url": f"https://cdn.example.com/{username}.jpg",
        "external_url": f"https://example.com/{username}",
        "updated_date": "2026-03-27T12:00:00Z",
        "follower_count": follower_count,
        "following_count": 100,
        "media_count": 50,
        "bio_links": [{"title": "Site", "url": "https://example.com"}],
        "ai_categories": ai_categories,
        "ai_roles": ai_roles,
    }


def _persist_snapshot_tree(
    db: Session,
    *,
    profile_id: str,
    scraped_at: datetime,
    post_code: str,
    reel_code: str,
) -> None:
    posts = create_post(
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
    assert posts is not None

    reels = create_reel(
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
    assert reels is not None

    metrics = create_metrics(
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
    assert metrics is not None

    snapshot = create_profile_snapshot(
        db,
        ProfileSnapshot(
            profile_id=profile_id,
            post_ids=[str(posts["_id"])],
            reel_ids=[str(reels["_id"])],
            metrics_id=str(metrics["_id"]),
            scraped_at=scraped_at,
        ),
    )
    assert snapshot is not None


def test_ig_profiles_route_uses_postgres(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    payload = _profile_payload(
        ig_id="1234567890",
        username="creator_alpha",
        full_name="Creator Alpha",
        biography="Fitness creator",
        follower_count=1000,
        ai_categories=["Fitness"],
        ai_roles=["Lifestyle"],
    )

    create_response = client.post(
        f"{settings.API_V1_STR}/ig-profiles/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["username"] == "creator_alpha"
    assert created["_id"]

    read_response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/by-username/creator_alpha",
        headers=superuser_token_headers,
    )
    assert read_response.status_code == 200
    assert read_response.json()["_id"] == created["_id"]

    patch_response = client.patch(
        f"{settings.API_V1_STR}/ig-profiles/{created['_id']}",
        headers=superuser_token_headers,
        json={"biography": "Updated bio", "follower_count": 1200},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["biography"] == "Updated bio"
    assert patch_response.json()["follower_count"] == 1200

    delete_response = client.delete(
        f"{settings.API_V1_STR}/ig-profiles/{created['_id']}",
        headers=superuser_token_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["_id"] == created["_id"]


def test_ig_profiles_search_returns_filtered_paginated_results(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    payloads = [
        _profile_payload(
            ig_id="ig-search-1",
            username="alpha_fit",
            full_name="Alpha Fit",
            biography="Fitness creator",
            follower_count=5_000,
            ai_categories=["Fitness"],
            ai_roles=["Creator"],
        ),
        _profile_payload(
            ig_id="ig-search-2",
            username="gamma_move",
            full_name="Gamma Move",
            biography="Fitness and travel ugc creator",
            follower_count=12_000,
            ai_categories=["Fitness", "Travel"],
            ai_roles=["Creator", "UGC"],
        ),
        _profile_payload(
            ig_id="ig-search-3",
            username="delta_glow",
            full_name="Delta Glow",
            biography="Beauty ugc creator",
            follower_count=8_000,
            ai_categories=["Beauty"],
            ai_roles=["UGC"],
        ),
        _profile_payload(
            ig_id="ig-search-4",
            username="omega_stream",
            full_name="Omega Stream",
            biography="Gaming creator",
            follower_count=20_000,
            ai_categories=["Gaming"],
            ai_roles=["Streamer"],
        ),
    ]

    for payload in payloads:
        response = client.post(
            f"{settings.API_V1_STR}/ig-profiles/",
            headers=superuser_token_headers,
            json=payload,
        )
        assert response.status_code == 201

    response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/search",
        headers=normal_user_token_headers,
        params=[
            ("query", "ugc"),
            ("ai_categories", "Fitness"),
            ("ai_categories", "Beauty"),
            ("ai_roles", "UGC"),
            ("follower_count_min", "7000"),
            ("follower_count_max", "15000"),
            ("sort_by", "follower_count"),
            ("sort_order", "asc"),
            ("page", "1"),
            ("page_size", "2"),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert [profile["username"] for profile in payload["profiles"]] == [
        "delta_glow",
        "gamma_move",
    ]
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 2,
        "total": 2,
        "total_pages": 1,
        "has_next": False,
        "has_previous": False,
    }


def test_ig_profiles_search_rejects_invalid_follower_range(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/search",
        headers=normal_user_token_headers,
        params={"follower_count_min": 5000, "follower_count_max": 1000},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("follower_count_min" in str(item) for item in detail)


def test_ig_profiles_search_matches_partial_username_and_full_name(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    payloads = [
        _profile_payload(
            ig_id="ig-search-partial-1",
            username="alpha_signal",
            full_name="Signal Alpha",
            biography="Creator profile",
            follower_count=2_000,
            ai_categories=["Fitness"],
            ai_roles=["Creator"],
        ),
        _profile_payload(
            ig_id="ig-search-partial-2",
            username="steady_creator",
            full_name="Gamma Focus",
            biography="Creator profile",
            follower_count=3_000,
            ai_categories=["Travel"],
            ai_roles=["UGC"],
        ),
    ]

    for payload in payloads:
        response = client.post(
            f"{settings.API_V1_STR}/ig-profiles/",
            headers=superuser_token_headers,
            json=payload,
        )
        assert response.status_code == 201

    username_response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/search",
        headers=normal_user_token_headers,
        params={"query": "sign"},
    )
    assert username_response.status_code == 200
    assert [
        profile["username"] for profile in username_response.json()["profiles"]
    ] == ["alpha_signal"]

    full_name_response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/search",
        headers=normal_user_token_headers,
        params={"query": "focus"},
    )
    assert full_name_response.status_code == 200
    assert [
        profile["username"] for profile in full_name_response.json()["profiles"]
    ] == ["steady_creator"]


def test_ig_profiles_search_rejects_query_shorter_than_three_characters(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/search",
        headers=normal_user_token_headers,
        params={"query": "ug"},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(item["loc"][-1] == "query" for item in detail)


def test_ig_profiles_full_profile_returns_expanded_snapshot_with_update_required(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/ig-profiles/",
        headers=superuser_token_headers,
        json=_profile_payload(
            ig_id="ig-full-profile-1",
            username="creator_full_profile",
            full_name="Creator Full Profile",
            biography="Full profile creator",
            follower_count=22_000,
            ai_categories=["Travel"],
            ai_roles=["Creator"],
        )
        | {
            "profile_pic_url": (
                "https://instagram.fxyz1-1.fna.fbcdn.net/"
                "v/t51.2885-19/creator-full-profile.jpg"
            )
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    _persist_snapshot_tree(
        db,
        profile_id=created["_id"],
        scraped_at=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        post_code="POST_FULL_1",
        reel_code="REEL_FULL_1",
    )

    with (
        patch("app.api.routes.ig_profile.should_refresh_profile", return_value=True),
        patch(
            "app.api.routes.ig_profile.resolve_profile_picture_data_uri",
            return_value="data:image/jpeg;base64,abc123",
        ),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/ig-profiles/{created['_id']}/full-profile",
            headers=normal_user_token_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["_id"]
    assert payload["profile"]["username"] == "creator_full_profile"
    assert payload["posts"][0]["posts"][0]["code"] == "POST_FULL_1"
    assert payload["reels"][0]["reels"][0]["code"] == "REEL_FULL_1"
    assert payload["metrics"]["overall_post_engagement_rate"] == 0.07
    assert payload["update_required"] is True
    assert payload["profile"]["profile_pic_src"] == "data:image/jpeg;base64,abc123"


def test_ig_profiles_full_profile_returns_update_required_false_when_current(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/ig-profiles/",
        headers=superuser_token_headers,
        json=_profile_payload(
            ig_id="ig-full-profile-2",
            username="creator_current_profile",
            full_name="Creator Current Profile",
            biography="Current profile creator",
            follower_count=18_000,
            ai_categories=["Beauty"],
            ai_roles=["UGC"],
        ),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    _persist_snapshot_tree(
        db,
        profile_id=created["_id"],
        scraped_at=datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
        post_code="POST_CURRENT_1",
        reel_code="REEL_CURRENT_1",
    )

    with patch("app.api.routes.ig_profile.should_refresh_profile", return_value=False):
        response = client.get(
            f"{settings.API_V1_STR}/ig-profiles/{created['_id']}/full-profile",
            headers=normal_user_token_headers,
        )

    assert response.status_code == 200
    assert response.json()["update_required"] is False


def test_ig_profiles_full_profile_returns_404_when_profile_is_missing(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/00000000-0000-0000-0000-000000000000/full-profile",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


def test_ig_profiles_full_profile_returns_404_when_snapshot_is_missing(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    create_response = client.post(
        f"{settings.API_V1_STR}/ig-profiles/",
        headers=superuser_token_headers,
        json=_profile_payload(
            ig_id="ig-full-profile-3",
            username="creator_without_snapshot",
            full_name="Creator Without Snapshot",
            biography="No snapshot yet",
            follower_count=3_000,
            ai_categories=["Gaming"],
            ai_roles=["Streamer"],
        ),
    )
    assert create_response.status_code == 201
    created = create_response.json()

    response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/{created['_id']}/full-profile",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile snapshot not found"}
