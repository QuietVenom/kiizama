import asyncio
from typing import Any

from app.features.brand_intelligence import service as brand_service
from app.features.brand_intelligence.schemas import ReputationCampaignStrategyRequest


class FakeBrandRepository:
    def __init__(
        self,
        *,
        profiles: list[dict[str, Any]] | None = None,
        snapshots: list[dict[str, Any]] | None = None,
    ) -> None:
        self.profiles = profiles or []
        self.snapshots = snapshots or []
        self.profile_calls: list[list[str]] = []
        self.snapshot_calls: list[list[str]] = []

    async def fetch_profiles_by_usernames(
        self,
        profiles_collection: object,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        del profiles_collection
        self.profile_calls.append(usernames)
        return self.profiles

    async def fetch_snapshots_full_by_usernames(
        self,
        profile_snapshots_collection: object,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        del profile_snapshots_collection
        self.snapshot_calls.append(usernames)
        return self.snapshots


class FakeStrategyOutput:
    def __init__(self, label: str) -> None:
        self.label = label

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "sections": [{"id": "s1", "title": "Strategy"}]}


class FakeCampaignReportGenerator:
    created_kwargs: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.__class__.created_kwargs.append(kwargs)


class FakeCreatorReportGenerator:
    created_kwargs: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.__class__.created_kwargs.append(kwargs)


def _campaign_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "brand_name": "Acme",
        "brand_context": "Brand context",
        "brand_urls": ["https://acme.com"],
        "brand_goals_type": "Crisis",
        "brand_goals_context": "Urgent reputation response.",
        "audience": ["Gen Z"],
        "timeframe": "3 months",
        "profiles_list": ["creator_one", "missing_creator"],
        "campaign_type": "all_micro_performance_community_trust",
        "generate_html": True,
        "generate_pdf": False,
    }
    return payload | overrides


def _creator_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "creator_username": "missing_creator",
        "creator_context": "Creator context",
        "creator_urls": ["https://instagram.com/missing_creator"],
        "goal_type": "Community Trust",
        "goal_context": "Build credibility.",
        "audience": ["Gen Z"],
        "timeframe": "3 months",
        "primary_platforms": ["Instagram"],
        "generate_html": True,
        "generate_pdf": False,
    }
    return payload | overrides


def test_brand_profile_existence_duplicate_usernames_preserves_request_shape() -> None:
    # Arrange
    repository = FakeBrandRepository(
        profiles=[
            {
                "username": "creator_one",
                "profile_pic_url": "https://cdn.example.com/profile.jpg?oe=00000000",
            }
        ]
    )

    # Act
    result = asyncio.run(
        brand_service.check_profile_usernames_existence(
            [" Creator_One ", "creator_one", "missing_creator"],
            profiles_collection=object(),
            repository=repository,
        )
    )

    # Assert
    assert repository.profile_calls == [["creator_one", "missing_creator"]]
    assert [profile.username for profile in result.profiles] == [
        "creator_one",
        "creator_one",
        "missing_creator",
    ]
    assert [profile.exists for profile in result.profiles] == [True, True, False]
    assert [profile.expired for profile in result.profiles] == [True, True, True]


def test_brand_campaign_confirmation_builds_catalog_costs_missing_profiles() -> None:
    # Arrange
    repository = FakeBrandRepository(
        profiles=[
            {
                "username": "creator_one",
                "full_name": "Creator One",
                "follower_count": 1500,
                "ai_categories": ["Beauty"],
            }
        ],
        snapshots=[
            {
                "profile": {"username": "creator_one", "biography": "Bio"},
                "metrics": {
                    "post_metrics": {
                        "total_posts": 3,
                        "total_likes": 900,
                        "avg_engagement_rate": 0.15,
                    }
                },
            }
        ],
    )
    request = ReputationCampaignStrategyRequest(**_campaign_payload())

    # Act
    confirmation = asyncio.run(
        brand_service.confirm_reputation_campaign_strategy(
            request,
            profiles_collection=object(),
            profile_snapshots_collection=object(),
            repository=repository,
        )
    )

    # Assert
    assert repository.profile_calls == [["creator_one", "missing_creator"]]
    assert confirmation.status == "confirmed"
    assert confirmation.selected_campaign_types[0].name == request.campaign_type
    assert confirmation.missing_profiles == ["missing_creator"]
    assert confirmation.influencer_profiles_directory[0].username == "creator_one"
    assert confirmation.cost_analysis.summary.total_profiles == 1
    assert confirmation.cost_analysis.summary.classified_profiles == 1
    assert confirmation.campaign_type_catalog
    assert confirmation.cost_tier_directory


def test_brand_creator_confirmation_missing_creator_returns_empty_summary() -> None:
    # Arrange
    repository = FakeBrandRepository()

    # Act
    confirmation = asyncio.run(
        brand_service.confirm_reputation_creator_strategy(
            _creator_payload(),
            profiles_collection=object(),
            profile_snapshots_collection=object(),
            repository=repository,
        )
    )

    # Assert
    assert repository.profile_calls == [["missing_creator"]]
    assert repository.snapshot_calls == [["missing_creator"]]
    assert confirmation.status == "confirmed"
    assert confirmation.missing_creator is True
    assert confirmation.creator_full_name is None
    assert confirmation.creator_follower_count == 0
    assert confirmation.current_metrics["creator_follower_count"] == 0


def test_brand_campaign_report_generation_renders_html_and_pdf_files(
    monkeypatch,
) -> None:
    # Arrange
    captured: dict[str, Any] = {}

    async def fake_generate_strategy_output(
        context: dict[str, Any],
    ) -> FakeStrategyOutput:
        captured["strategy_context"] = context
        return FakeStrategyOutput("campaign")

    async def fake_generate_report_files(
        **kwargs: Any,
    ) -> list[brand_service.ReportFile]:
        captured["report_kwargs"] = kwargs
        return [
            brand_service.ReportFile(
                filename="campaign.html",
                content_type="text/html",
                content=b"<html>campaign</html>",
            )
        ]

    monkeypatch.setattr(
        brand_service,
        "generate_reputation_strategy_output",
        fake_generate_strategy_output,
    )
    monkeypatch.setattr(
        brand_service,
        "render_reputation_strategy_sections_html",
        lambda output: f"<section>{output.label}</section>",
    )
    monkeypatch.setattr(
        brand_service,
        "ReputationCampaignStrategyReportGenerator",
        FakeCampaignReportGenerator,
    )
    monkeypatch.setattr(
        brand_service, "generate_report_files", fake_generate_report_files
    )

    # Act
    files = asyncio.run(
        brand_service.generate_reputation_campaign_strategy_report(
            profiles_collection=object(),
            profile_snapshots_collection=object(),
            payload=_campaign_payload(profiles_list=[]),
            repository=FakeBrandRepository(),
        )
    )

    # Assert
    assert files[0].filename == "campaign.html"
    assert captured["strategy_context"]["brand_name"] == "Acme"
    assert captured["report_kwargs"]["context"]["reputation_strategy"]["label"] == (
        "campaign"
    )
    assert captured["report_kwargs"]["context"]["report_main_body"] == (
        "<section>campaign</section>"
    )
    assert captured["report_kwargs"]["generate_html"] is True
    assert captured["report_kwargs"]["generate_pdf"] is False
    assert FakeCampaignReportGenerator.created_kwargs[-1]["template_name"]


def test_brand_creator_report_generation_uses_current_metrics_and_creator_html(
    monkeypatch,
) -> None:
    # Arrange
    captured: dict[str, Any] = {}

    async def fake_generate_creator_output(
        context: dict[str, Any],
    ) -> FakeStrategyOutput:
        captured["strategy_context"] = context
        return FakeStrategyOutput("creator")

    async def fake_generate_report_files(
        **kwargs: Any,
    ) -> list[brand_service.ReportFile]:
        captured["report_kwargs"] = kwargs
        return [
            brand_service.ReportFile(
                filename="creator.pdf",
                content_type="application/pdf",
                content=b"%PDF",
            )
        ]

    monkeypatch.setattr(
        brand_service,
        "generate_reputation_creator_strategy_output",
        fake_generate_creator_output,
    )
    monkeypatch.setattr(
        brand_service,
        "render_creator_strategy_sections_html",
        lambda output: f"<section>{output.label}</section>",
    )
    monkeypatch.setattr(
        brand_service,
        "ReputationCreatorStrategyReportGenerator",
        FakeCreatorReportGenerator,
    )
    monkeypatch.setattr(
        brand_service, "generate_report_files", fake_generate_report_files
    )

    # Act
    files = asyncio.run(
        brand_service.generate_reputation_creator_strategy_report(
            profiles_collection=object(),
            profile_snapshots_collection=object(),
            payload=_creator_payload(generate_html=False, generate_pdf=True),
            repository=FakeBrandRepository(
                snapshots=[
                    {
                        "profile": {
                            "username": "missing_creator",
                            "full_name": "Creator One",
                        },
                        "metrics": {
                            "post_metrics": {
                                "total_likes": 120,
                                "avg_engagement_rate": 0.1,
                            }
                        },
                    }
                ]
            ),
        )
    )

    # Assert
    assert files[0].filename == "creator.pdf"
    assert captured["strategy_context"]["creator_username"] == "missing_creator"
    assert captured["strategy_context"]["current_metrics"]["total_likes"] == 120
    assert captured["report_kwargs"]["context"]["reputation_strategy"]["label"] == (
        "creator"
    )
    assert captured["report_kwargs"]["context"]["report_main_body"] == (
        "<section>creator</section>"
    )
    assert captured["report_kwargs"]["generate_html"] is False
    assert captured["report_kwargs"]["generate_pdf"] is True
    assert FakeCreatorReportGenerator.created_kwargs[-1]["template_name"]
