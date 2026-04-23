from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_profile_snapshots_collection
from app.core.config import settings
from app.main import app


def test_read_ig_profile_snapshots_advanced_includes_missing_usernames(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    fake_collection = object()
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: fake_collection
    mocked_snapshots = [
        {
            "_id": "65c2f0b7f6b7a8c1c3d4e5f9",
            "profile_id": "65c2f0b7f6b7a8c1c3d4e5f6",
            "post_ids": [],
            "reel_ids": [],
            "metrics_id": None,
            "scraped_at": "2024-02-12T15:04:05Z",
            "profile": {
                "_id": "65c2f0b7f6b7a8c1c3d4e5f6",
                "ig_id": "1234567890",
                "username": "creator_one",
                "full_name": "Creator One",
                "biography": "Fitness creator",
                "is_private": False,
                "is_verified": True,
                "profile_pic_url": "https://cdn.example.com/creator-one.jpg?oe=00000000",
                "external_url": "https://example.com/creator-one",
                "updated_date": "2024-02-12T15:04:05Z",
                "follower_count": 1000,
                "following_count": 100,
                "media_count": 50,
                "bio_links": [],
                "ai_categories": [],
                "ai_roles": [],
            },
            "posts": [],
            "reels": [],
            "metrics": None,
        }
    ]
    list_profile_snapshots_full = MagicMock(return_value=mocked_snapshots)

    try:
        with patch(
            "app.api.routes.ig_profile_snapshots.list_profile_snapshots_full",
            new=list_profile_snapshots_full,
        ):
            response = client.get(
                f"{settings.API_V1_STR}/ig-profile-snapshots/advanced",
                headers=superuser_token_headers,
                params=[
                    ("usernames", "creator_one"),
                    ("usernames", "missing.user"),
                ],
            )
    finally:
        app.dependency_overrides.pop(get_profile_snapshots_collection, None)

    assert response.status_code == 200
    assert response.json()["missing_usernames"] == ["missing.user"]
    assert response.json()["expired_usernames"] == ["creator_one"]
    assert response.json()["snapshots"][0]["profile"]["username"] == "creator_one"
    list_profile_snapshots_full.assert_called_once()
    assert list_profile_snapshots_full.call_args.kwargs == {
        "skip": 0,
        "limit": 100,
        "usernames": ["creator_one", "missing.user"],
    }


def test_read_ig_profile_snapshots_advanced_allows_normal_users(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    fake_collection = object()
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: fake_collection
    mocked_snapshots = [
        {
            "_id": "65c2f0b7f6b7a8c1c3d4e5f9",
            "profile_id": "65c2f0b7f6b7a8c1c3d4e5f6",
            "post_ids": [],
            "reel_ids": [],
            "metrics_id": None,
            "scraped_at": "2024-02-12T15:04:05Z",
            "profile": {
                "_id": "65c2f0b7f6b7a8c1c3d4e5f6",
                "ig_id": "1234567890",
                "username": "creator_one",
                "full_name": "Creator One",
                "biography": "Fitness creator",
                "is_private": False,
                "is_verified": True,
                "profile_pic_url": "https://cdn.example.com/creator-one.jpg?oe=ffffffff",
                "external_url": "https://example.com/creator-one",
                "updated_date": "2024-02-12T15:04:05Z",
                "follower_count": 1000,
                "following_count": 100,
                "media_count": 50,
                "bio_links": [],
                "ai_categories": [],
                "ai_roles": [],
            },
            "posts": [],
            "reels": [],
            "metrics": None,
        }
    ]
    list_profile_snapshots_full = MagicMock(return_value=mocked_snapshots)

    try:
        with patch(
            "app.api.routes.ig_profile_snapshots.list_profile_snapshots_full",
            new=list_profile_snapshots_full,
        ):
            response = client.get(
                f"{settings.API_V1_STR}/ig-profile-snapshots/advanced",
                headers=normal_user_token_headers,
                params=[("usernames", "creator_one")],
            )
    finally:
        app.dependency_overrides.pop(get_profile_snapshots_collection, None)

    assert response.status_code == 200
    assert response.json()["expired_usernames"] == []
    assert response.json()["snapshots"][0]["profile"]["username"] == "creator_one"
    list_profile_snapshots_full.assert_called_once()
    assert list_profile_snapshots_full.call_args.kwargs == {
        "skip": 0,
        "limit": 100,
        "usernames": ["creator_one"],
    }


def test_read_ig_profile_snapshots_advanced_resolves_profile_picture_source(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    fake_collection = object()
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: fake_collection
    mocked_snapshots = [
        {
            "_id": "65c2f0b7f6b7a8c1c3d4e5f9",
            "profile_id": "65c2f0b7f6b7a8c1c3d4e5f6",
            "post_ids": [],
            "reel_ids": [],
            "metrics_id": None,
            "scraped_at": "2024-02-12T15:04:05Z",
            "profile": {
                "_id": "65c2f0b7f6b7a8c1c3d4e5f6",
                "ig_id": "1234567890",
                "username": "creator_one",
                "full_name": "Creator One",
                "biography": "Fitness creator",
                "is_private": False,
                "is_verified": True,
                "profile_pic_url": (
                    "https://scontent.cdninstagram.com/v/t51.2885-19/creator-one.jpg"
                    "?oe=ffffffff"
                ),
                "external_url": "https://example.com/creator-one",
                "updated_date": "2024-02-12T15:04:05Z",
                "follower_count": 1000,
                "following_count": 100,
                "media_count": 50,
                "bio_links": [],
                "ai_categories": [],
                "ai_roles": [],
            },
            "posts": [],
            "reels": [],
            "metrics": None,
        }
    ]
    list_profile_snapshots_full = MagicMock(return_value=mocked_snapshots)

    try:
        with (
            patch(
                "app.api.routes.ig_profile_snapshots.list_profile_snapshots_full",
                new=list_profile_snapshots_full,
            ),
            patch(
                "app.api.routes.ig_profile_snapshots.resolve_profile_picture_data_uri",
                return_value="data:image/jpeg;base64,abc123",
            ) as resolve_profile_picture_data_uri,
        ):
            response = client.get(
                f"{settings.API_V1_STR}/ig-profile-snapshots/advanced",
                headers=normal_user_token_headers,
                params=[("usernames", "creator_one")],
            )
    finally:
        app.dependency_overrides.pop(get_profile_snapshots_collection, None)

    assert response.status_code == 200
    assert (
        response.json()["snapshots"][0]["profile"]["profile_pic_src"]
        == "data:image/jpeg;base64,abc123"
    )
    resolve_profile_picture_data_uri.assert_called_once()


def test_read_ig_profile_snapshots_advanced_rejects_more_than_50_usernames(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    fake_collection = object()
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: fake_collection
    list_profile_snapshots_full = MagicMock()

    try:
        with patch(
            "app.api.routes.ig_profile_snapshots.list_profile_snapshots_full",
            new=list_profile_snapshots_full,
        ):
            response = client.get(
                f"{settings.API_V1_STR}/ig-profile-snapshots/advanced",
                headers=superuser_token_headers,
                params=[("usernames", f"creator_{index}") for index in range(51)],
            )
    finally:
        app.dependency_overrides.pop(get_profile_snapshots_collection, None)

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "too_long"
    list_profile_snapshots_full.assert_not_called()


def test_read_ig_profile_snapshots_requires_superuser_outside_advanced(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/ig-profile-snapshots/",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "The user doesn't have enough privileges"}
