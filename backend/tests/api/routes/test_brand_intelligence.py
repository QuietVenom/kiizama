from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_profiles_collection
from app.core.config import settings
from app.main import app


def test_read_profiles_existence(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    fake_collection = object()
    app.dependency_overrides[get_profiles_collection] = lambda: fake_collection
    fetch_profiles_by_usernames = AsyncMock(
        return_value=[
            {
                "username": "creator_one",
                "profile_pic_url": "https://cdn.example.com/creator-one.jpg?oe=ffffffff",
            }
        ]
    )

    try:
        with patch(
            "app.features.brand_intelligence.repository."
            "BrandIntelligenceRepository.fetch_profiles_by_usernames",
            new=fetch_profiles_by_usernames,
        ):
            response = client.get(
                f"{settings.API_V1_STR}/brand-intelligence/profiles-existence",
                headers=normal_user_token_headers,
                params=[
                    ("usernames", "Creator_One"),
                    ("usernames", "missing.user"),
                ],
            )
    finally:
        app.dependency_overrides.pop(get_profiles_collection, None)

    assert response.status_code == 200
    assert response.json() == {
        "profiles": [
            {"username": "creator_one", "exists": True, "expired": False},
            {"username": "missing.user", "exists": False, "expired": True},
        ]
    }
    fetch_profiles_by_usernames.assert_awaited_once_with(
        fake_collection,
        ["creator_one", "missing.user"],
    )


def test_read_profiles_existence_marks_expired_profiles(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    fake_collection = object()
    app.dependency_overrides[get_profiles_collection] = lambda: fake_collection
    fetch_profiles_by_usernames = AsyncMock(
        return_value=[
            {
                "username": "creator_one",
                "profile_pic_url": "https://cdn.example.com/creator-one.jpg?oe=00000000",
            }
        ]
    )

    try:
        with patch(
            "app.features.brand_intelligence.repository."
            "BrandIntelligenceRepository.fetch_profiles_by_usernames",
            new=fetch_profiles_by_usernames,
        ):
            response = client.get(
                f"{settings.API_V1_STR}/brand-intelligence/profiles-existence",
                headers=normal_user_token_headers,
                params=[("usernames", "creator_one")],
            )
    finally:
        app.dependency_overrides.pop(get_profiles_collection, None)

    assert response.status_code == 200
    assert response.json() == {
        "profiles": [
            {"username": "creator_one", "exists": True, "expired": True},
        ]
    }
    fetch_profiles_by_usernames.assert_awaited_once_with(
        fake_collection,
        ["creator_one"],
    )


def test_read_profiles_existence_requires_usernames(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    fake_collection = object()
    app.dependency_overrides[get_profiles_collection] = lambda: fake_collection
    fetch_profiles_by_usernames = AsyncMock()

    try:
        with patch(
            "app.features.brand_intelligence.repository."
            "BrandIntelligenceRepository.fetch_profiles_by_usernames",
            new=fetch_profiles_by_usernames,
        ):
            response = client.get(
                f"{settings.API_V1_STR}/brand-intelligence/profiles-existence",
                headers=normal_user_token_headers,
            )
    finally:
        app.dependency_overrides.pop(get_profiles_collection, None)

    assert response.status_code == 400
    assert response.json() == {"detail": "usernames cannot be empty"}
    fetch_profiles_by_usernames.assert_not_awaited()
