from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_profile_snapshots_collection, get_profiles_collection
from app.core.config import settings
from app.features.brand_intelligence.service import ReportFile
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


def test_generate_reputation_campaign_strategy_allows_empty_creators_for_crisis(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    fake_profiles_collection = object()
    fake_profile_snapshots_collection = object()
    app.dependency_overrides[get_profiles_collection] = lambda: fake_profiles_collection
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: (
        fake_profile_snapshots_collection
    )
    execute_report_generation = AsyncMock(
        return_value=[
            ReportFile(
                filename="reputation_campaign_strategy.pdf",
                content_type="application/pdf",
                content=b"%PDF-1.4",
            )
        ]
    )

    try:
        with patch(
            "app.api.routes.brand_intelligence._execute_report_generation",
            new=execute_report_generation,
        ):
            response = client.post(
                f"{settings.API_V1_STR}/brand-intelligence/reputation-campaign-strategy",
                headers=normal_user_token_headers,
                json={
                    "brand_name": "Acme",
                    "brand_context": "Brand context",
                    "brand_urls": ["https://acme.com"],
                    "brand_goals_type": "Crisis",
                    "brand_goals_context": "Urgent reputation response.",
                    "audience": ["Gen Z"],
                    "timeframe": "3 months",
                    "profiles_list": [],
                    "campaign_type": "all_micro_performance_community_trust",
                    "generate_html": False,
                    "generate_pdf": True,
                },
            )
    finally:
        app.dependency_overrides.pop(get_profiles_collection, None)
        app.dependency_overrides.pop(get_profile_snapshots_collection, None)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    execute_report_generation.assert_awaited_once()
    await_args = execute_report_generation.await_args
    assert await_args is not None
    assert await_args.kwargs["payload"].profiles_list == []
    assert await_args.kwargs["payload"].brand_goals_type == "Crisis"


def test_generate_reputation_campaign_strategy_requires_creators_for_non_crisis(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    fake_profiles_collection = object()
    fake_profile_snapshots_collection = object()
    app.dependency_overrides[get_profiles_collection] = lambda: fake_profiles_collection
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: (
        fake_profile_snapshots_collection
    )

    try:
        response = client.post(
            f"{settings.API_V1_STR}/brand-intelligence/reputation-campaign-strategy",
            headers=normal_user_token_headers,
            json={
                "brand_name": "Acme",
                "brand_context": "Brand context",
                "brand_urls": ["https://acme.com"],
                "brand_goals_type": "Repositioning",
                "brand_goals_context": "Need a new market narrative.",
                "audience": ["Gen Z"],
                "timeframe": "3 months",
                "profiles_list": [],
                "campaign_type": "all_micro_performance_community_trust",
                "generate_html": False,
                "generate_pdf": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_profiles_collection, None)
        app.dependency_overrides.pop(get_profile_snapshots_collection, None)

    assert response.status_code == 422
    assert "creator username" in str(response.json())
