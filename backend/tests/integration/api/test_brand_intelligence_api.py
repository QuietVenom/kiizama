from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_profile_snapshots_collection, get_profiles_collection
from app.api.routes import brand_intelligence
from app.core.config import settings
from app.core.resilience import UpstreamUnavailableError
from app.features.brand_intelligence.service import ReportFile
from app.main import app


def _valid_campaign_payload() -> dict[str, object]:
    return {
        "brand_name": "Acme",
        "brand_context": "Brand context",
        "brand_urls": ["https://acme.com"],
        "brand_goals_type": "Crisis",
        "brand_goals_context": "Urgent reputation response.",
        "audience": ["Gen Z"],
        "timeframe": "3 months",
        "profiles_list": [],
        "campaign_type": "all_micro_performance_community_trust",
        "generate_html": True,
        "generate_pdf": False,
    }


def _valid_creator_payload() -> dict[str, object]:
    return {
        "creator_username": "creator_one",
        "creator_urls": ["https://instagram.com/creator_one"],
        "creator_context": "Creator context",
        "goal_type": "Community Trust",
        "goal_context": "Build a safer creator narrative.",
        "audience": ["Gen Z"],
        "timeframe": "3 months",
        "primary_platforms": ["Instagram"],
        "generate_html": True,
        "generate_pdf": False,
    }


def _install_brand_collections() -> None:
    fake_profiles_collection = object()
    fake_profile_snapshots_collection = object()
    app.dependency_overrides[get_profiles_collection] = lambda: fake_profiles_collection
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: (
        fake_profile_snapshots_collection
    )


def _clear_brand_collections() -> None:
    app.dependency_overrides.pop(get_profiles_collection, None)
    app.dependency_overrides.pop(get_profile_snapshots_collection, None)


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


def test_generate_reputation_campaign_strategy_returns_standard_503_payload(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    fake_profiles_collection = object()
    fake_profile_snapshots_collection = object()
    app.dependency_overrides[get_profiles_collection] = lambda: fake_profiles_collection
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: (
        fake_profile_snapshots_collection
    )
    execute_report_generation = AsyncMock(
        side_effect=UpstreamUnavailableError(
            dependency="openai",
            detail="OpenAI strategy service is unavailable.",
        )
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

    assert response.status_code == 503
    assert response.json() == {
        "detail": "OpenAI strategy service is unavailable.",
        "dependency": "openai",
        "retryable": True,
    }


def test_brand_campaign_strategy_lookup_error_releases_reservation_and_returns_404(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    calls: dict[str, Any] = {}

    async def generate_report(**_: object) -> list[ReportFile]:
        raise LookupError("Profile snapshots missing")

    async def publish_billing_event(**kwargs: object) -> None:
        calls.setdefault("events", []).append(kwargs["event_name"])

    _install_brand_collections()
    monkeypatch.setattr(
        brand_intelligence,
        "generate_reputation_campaign_strategy_report",
        generate_report,
    )
    monkeypatch.setattr(
        brand_intelligence,
        "reserve_feature_usage",
        lambda **kwargs: calls.setdefault("reserved", kwargs),
    )
    monkeypatch.setattr(
        brand_intelligence,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )
    monkeypatch.setattr(
        brand_intelligence, "publish_billing_event", publish_billing_event
    )

    try:
        # Act
        response = client.post(
            f"{settings.API_V1_STR}/brand-intelligence/reputation-campaign-strategy",
            headers=normal_user_token_headers,
            json=_valid_campaign_payload(),
        )
    finally:
        _clear_brand_collections()

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile snapshots missing"}
    assert calls["reserved"]
    assert calls["released"]["metadata"] == {"error": "Profile snapshots missing"}
    assert calls["events"] == ["account.usage.updated"]


def test_brand_campaign_strategy_value_error_releases_reservation_and_returns_400(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    calls: dict[str, Any] = {}

    async def generate_report(**_: object) -> list[ReportFile]:
        raise ValueError("Invalid strategy context")

    async def publish_billing_event(**kwargs: object) -> None:
        calls.setdefault("events", []).append(kwargs["event_name"])

    _install_brand_collections()
    monkeypatch.setattr(
        brand_intelligence,
        "generate_reputation_campaign_strategy_report",
        generate_report,
    )
    monkeypatch.setattr(brand_intelligence, "reserve_feature_usage", lambda **_: None)
    monkeypatch.setattr(
        brand_intelligence,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )
    monkeypatch.setattr(
        brand_intelligence, "publish_billing_event", publish_billing_event
    )

    try:
        # Act
        response = client.post(
            f"{settings.API_V1_STR}/brand-intelligence/reputation-campaign-strategy",
            headers=normal_user_token_headers,
            json=_valid_campaign_payload(),
        )
    finally:
        _clear_brand_collections()

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid strategy context"}
    assert calls["released"]["metadata"] == {"error": "Invalid strategy context"}
    assert calls["events"] == ["account.usage.updated"]


def test_brand_campaign_strategy_unexpected_error_releases_reservation_and_reraises(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    calls: dict[str, Any] = {}

    async def generate_report(**_: object) -> list[ReportFile]:
        raise RuntimeError("strategy generator failed")

    async def publish_billing_event(**kwargs: object) -> None:
        calls.setdefault("events", []).append(kwargs["event_name"])

    _install_brand_collections()
    monkeypatch.setattr(
        brand_intelligence,
        "generate_reputation_campaign_strategy_report",
        generate_report,
    )
    monkeypatch.setattr(brand_intelligence, "reserve_feature_usage", lambda **_: None)
    monkeypatch.setattr(
        brand_intelligence,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )
    monkeypatch.setattr(
        brand_intelligence, "publish_billing_event", publish_billing_event
    )

    try:
        # Act / Assert
        with pytest.raises(RuntimeError, match="strategy generator failed"):
            client.post(
                f"{settings.API_V1_STR}/brand-intelligence/reputation-campaign-strategy",
                headers=normal_user_token_headers,
                json=_valid_campaign_payload(),
            )
    finally:
        _clear_brand_collections()

    assert "metadata" not in calls["released"]
    assert calls["events"] == ["account.usage.updated"]


def test_brand_creator_strategy_multiple_files_returns_zip_response(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    # Arrange
    _install_brand_collections()
    execute_report_generation = AsyncMock(
        return_value=[
            ReportFile(
                filename="creator.html",
                content_type="text/html",
                content=b"<html>creator</html>",
            ),
            ReportFile(
                filename="creator.pdf",
                content_type="application/pdf",
                content=b"%PDF-1.4",
            ),
        ]
    )

    try:
        with patch(
            "app.api.routes.brand_intelligence._execute_report_generation",
            new=execute_report_generation,
        ):
            # Act
            response = client.post(
                f"{settings.API_V1_STR}/brand-intelligence/reputation-creator-strategy",
                headers=normal_user_token_headers,
                json=_valid_creator_payload(),
            )
    finally:
        _clear_brand_collections()

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert (
        'filename="reputation_creator_strategy_reports.zip"'
        in response.headers["content-disposition"]
    )
    assert response.content.startswith(b"PK")
    execute_report_generation.assert_awaited_once()
