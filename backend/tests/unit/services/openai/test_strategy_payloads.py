import asyncio
import json
from typing import Any

from app.features.brand_intelligence.services.service_profiles import (
    build_creator_profile_summary,
    build_influencer_profiles_directory,
)
from app.features.openai.classes.openai_creator_data import (
    ReputationCreatorStrategyOutput,
    ReputationCreatorStrategySection,
    deserialize_creator_strategy_response,
    render_creator_strategy_sections_html,
    serialize_creator_strategy_payload,
)
from app.features.openai.classes.openai_prompt_metadata import (
    infer_response_language,
)
from app.features.openai.classes.openai_reputation_data import (
    ReputationStrategyOutput,
    ReputationStrategySection,
    deserialize_reputation_strategy_response,
    render_reputation_strategy_sections_html,
    serialize_reputation_strategy_payload,
)
from app.features.openai.classes.openai_requests import (
    CREATOR_OPENAI_REQUEST,
    IG_OPENAI_REQUEST,
    REPUTATION_OPENAI_REQUEST,
)
from app.features.openai.classes.openai_system_prompts import (
    SYSTEM_PROMPT_REPUTATION_CREATOR_OPENAI_REQUEST,
    SYSTEM_PROMPT_REPUTATION_OPENAI_REQUEST,
)
from app.features.openai.types.base import DEFAULT_MODEL
from app.features.openai.workflows import (
    build_strategy_request_kwargs,
    execute_strategy_template,
    parse_strategy_response,
)


def _snapshot(*, username: str, reels_available: bool) -> dict[str, object]:
    return {
        "profile": {
            "username": username,
            "full_name": "Creator One",
            "follower_count": 1200,
            "is_verified": False,
        },
        "metrics": {
            "post_metrics": {
                "total_posts": 12,
                "total_comments": 48,
                "total_likes": 360,
                "avg_engagement_rate": 0.12,
                "hashtags_per_post": 1.5,
                "mentions_per_post": 0.5,
            },
            "reel_metrics": {
                "total_reels": 0,
                "total_plays": 0,
            },
            "overall_post_engagement_rate": 0.13,
            "reel_engagement_rate_on_plays": 0.0,
        },
        "reels": [{"reels": [], "updated_at": "2026-04-05T00:00:00Z"}]
        if reels_available
        else [],
        "reel_ids": ["reel-doc-1"] if reels_available else [],
        "scraped_at": "2026-04-05T00:00:00Z",
    }


class FakeModelDump:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.modes: list[str] = []

    def model_dump(self, *, mode: str = "python", **kwargs: Any) -> dict[str, Any]:
        del kwargs
        self.modes.append(mode)
        return self.payload


def _reputation_payload() -> dict[str, Any]:
    return {
        "brand_name": "Kiizama",
        "brand_context": "Marca de skincare con ingredientes limpios.",
        "brand_url": "https://kiizama.example",
        "brand_goals_type": "Trust & Credibility Acceleration",
        "brand_goals_context": "Queremos fortalecer la confianza de compra.",
        "Audience": ["Gen Z", "Millennials"],
        "timeframe": "6 months",
        "campaign_type": "all_micro_performance_community_trust",
    }


def _creator_payload() -> dict[str, Any]:
    return {
        "creator_username": "Creator.One",
        "creator_context": "Creator focused on wellness and productivity.",
        "creator_url": "https://instagram.com/creator.one",
        "goal_type": "Community Trust",
        "goal_context": "Need to reinforce audience trust during sponsored launches.",
        "Audience": ["Gen Z"],
        "timeframe": "6 months",
        "primary_platforms": ["Instagram", "YouTube"],
    }


def test_infer_response_language_prefers_spanish_signals() -> None:
    assert (
        infer_response_language(
            "Marca de skincare con ingredientes limpios.",
            "Queremos fortalecer la confianza de compra.",
        )
        == "es"
    )


def test_infer_response_language_detects_brazilian_portuguese() -> None:
    assert (
        infer_response_language(
            "Marca de skincare com ingredientes limpos.",
            "Queremos fortalecer a confiança de compra com uma campanha clara.",
        )
        == "pt-BR"
    )


def test_infer_response_language_keeps_english_when_signals_are_clear() -> None:
    assert infer_response_language("brand strategy", "community trust") == "en"


def test_infer_response_language_defaults_to_spanish_for_weak_text() -> None:
    assert infer_response_language("", None) == "es"


def test_build_influencer_profiles_directory_marks_reels_unavailable_without_docs() -> (
    None
):
    directory, missing = build_influencer_profiles_directory(
        ["creator_one"],
        profiles=[],
        snapshots=[_snapshot(username="creator_one", reels_available=False)],
    )

    assert missing == []
    assert directory[0].metrics.reels_metrics_status == "unavailable"


def test_build_influencer_profiles_directory_marks_reels_available_with_docs() -> None:
    directory, missing = build_influencer_profiles_directory(
        ["creator_one"],
        profiles=[],
        snapshots=[_snapshot(username="creator_one", reels_available=True)],
    )

    assert missing == []
    assert directory[0].metrics.reels_metrics_status == "available"


def test_build_creator_profile_summary_marks_reels_unavailable_without_docs() -> None:
    summary = build_creator_profile_summary(
        "creator_one",
        profiles=[],
        snapshots=[_snapshot(username="creator_one", reels_available=False)],
    )

    assert summary["current_metrics"]["reels_metrics_status"] == "unavailable"


def test_build_creator_profile_summary_marks_reels_available_with_docs() -> None:
    summary = build_creator_profile_summary(
        "creator_one",
        profiles=[],
        snapshots=[_snapshot(username="creator_one", reels_available=True)],
    )

    assert summary["current_metrics"]["reels_metrics_status"] == "available"


def test_serialize_reputation_strategy_payload_infers_language_and_preserves_status() -> (
    None
):
    serialized = serialize_reputation_strategy_payload(
        {
            "brand_name": "Kiizama",
            "brand_context": "Marca de skincare con ingredientes limpios.",
            "brand_goals_type": "Trust & Credibility Acceleration",
            "brand_goals_context": "Queremos fortalecer la confianza de compra.",
            "audience": ["Gen Z"],
            "timeframe": "6 months",
            "campaign_type": "all_micro_performance_community_trust",
            "influencer_profiles_directory": [
                {
                    "username": "creator_one",
                    "metrics": {
                        "total_posts": 12,
                        "total_comments": 48,
                        "total_likes": 360,
                        "avg_engagement_rate": 0.12,
                        "hashtags_per_post": 1.5,
                        "mentions_per_post": 0.5,
                        "total_reels": 0,
                        "total_plays": 0,
                        "overall_post_engagement_rate": 0.13,
                        "reel_engagement_rate_on_plays": 0.0,
                        "reels_metrics_status": "unavailable",
                    },
                }
            ],
        }
    )

    assert serialized["response_language"] == "es"
    assert (
        serialized["profiles_list"][0]["metrics"]["reels_metrics_status"]
        == "unavailable"
    )


def test_reputation_strategy_payload_aliases_and_coercion_serializes_expected_contract() -> (
    None
):
    # Arrange
    payload = _reputation_payload() | {
        "influencer_profiles_directory": [
            " Creator_One ",
            12345,
            None,
            {
                "username": "CREATOR_TWO",
                "full_name": " Creator Two ",
                "biography": " ",
                "ai_categories": ("Beauty", None),
                "ai_roles": "Creator",
                "follower_count": "1200",
                "is_verified": "yes",
                "metrics": {
                    "total_posts": "12",
                    "total_comments": True,
                    "total_likes": 30.7,
                    "avg_engagement_rate": "0.12",
                    "hashtags_per_post": "bad-number",
                    "mentions_per_post": None,
                    "total_reels": "3",
                    "total_plays": 1000.9,
                    "overall_post_engagement_rate": "0.14",
                    "reel_engagement_rate_on_plays": False,
                    "reels_metrics_status": "available",
                },
            },
        ],
    }

    # Act
    serialized = serialize_reputation_strategy_payload(payload)

    # Assert
    assert serialized["brand_urls"] == ["https://kiizama.example"]
    assert serialized["audience"] == ["Gen Z", "Millennials"]
    assert [profile["username"] for profile in serialized["profiles_list"]] == [
        "creator_one",
        "12345",
        "creator_two",
    ]
    detailed_profile = serialized["profiles_list"][2]
    assert detailed_profile["full_name"] == "Creator Two"
    assert detailed_profile["biography"] is None
    assert detailed_profile["ai_categories"] == ["Beauty"]
    assert detailed_profile["ai_roles"] == ["Creator"]
    assert detailed_profile["follower_count"] == 1200
    assert detailed_profile["is_verified"] is True
    assert detailed_profile["metrics"] == {
        "total_posts": 12,
        "total_comments": 1,
        "total_likes": 30,
        "avg_engagement_rate": 0.12,
        "hashtags_per_post": 0.0,
        "mentions_per_post": 0.0,
        "total_reels": 3,
        "total_plays": 1000,
        "overall_post_engagement_rate": 0.14,
        "reel_engagement_rate_on_plays": 0.0,
        "reels_metrics_status": "available",
    }


def test_reputation_strategy_cost_analysis_payload_serializes_segments() -> None:
    # Arrange
    payload = _reputation_payload() | {
        "profiles_list": ["creator_one"],
        "cost_estimates": {
            "summary": {
                "currency": "",
                "total_profiles": "3",
                "classified_profiles": 2.9,
                "unclassified_profiles": True,
                "total_min_mxn": "1000",
                "total_max_mxn": "bad",
                "total_average_mxn": 1500.8,
            },
            "summary_by_segment": [
                {
                    "tier_key": "micro",
                    "tier_label": "Micro",
                    "profiles_count": "2",
                    "typical_deliverable": " Reel ",
                    "segment_min_mxn": "100",
                    "segment_max_mxn": 300.9,
                    "segment_average_mxn": None,
                    "notes": " ",
                },
                None,
            ],
        },
    }

    # Act
    serialized = serialize_reputation_strategy_payload(payload)

    # Assert
    cost_analysis = serialized["cost_analysis"]
    assert cost_analysis["summary"] == {
        "currency": "MXN",
        "total_profiles": 3,
        "classified_profiles": 2,
        "unclassified_profiles": 1,
        "total_min_mxn": 1000,
        "total_max_mxn": 0,
        "total_average_mxn": 1500,
    }
    assert cost_analysis["summary_by_segment"] == [
        {
            "tier_key": "micro",
            "tier_label": "Micro",
            "profiles_count": 2,
            "typical_deliverable": "Reel",
            "segment_min_mxn": 100,
            "segment_max_mxn": 300,
            "segment_average_mxn": 0,
            "notes": None,
        }
    ]


def test_reputation_strategy_payload_model_dump_input_is_supported() -> None:
    # Arrange
    payload = FakeModelDump(_reputation_payload() | {"profiles_list": ["creator_one"]})

    # Act
    serialized = serialize_reputation_strategy_payload(payload)

    # Assert
    assert payload.modes == ["json"]
    assert serialized["profiles_list"][0]["username"] == "creator_one"


def test_reputation_strategy_payload_invalid_type_raises_type_error() -> None:
    # Arrange / Act / Assert
    try:
        serialize_reputation_strategy_payload(object())
    except TypeError as exc:
        assert "Unsupported payload type for reputation strategy input" in str(exc)
    else:
        raise AssertionError("Expected invalid reputation payload to raise TypeError")


def test_reputation_strategy_response_deserialization_filters_invalid_sections() -> (
    None
):
    # Arrange
    model_dump_section = FakeModelDump(
        {"id": "details", "title": "Details", "content": "Detailed plan"}
    )
    payload = {
        "meta": {"source": "openai"},
        "assumptions": [FakeModelDump({"assumption": "Market fit"})],
        "verified_facts": [{"claim": "Fact"}],
        "sections": [
            {"id": "", "title": "Missing id", "content": "skip"},
            {"id": "missing-title", "title": "", "content": "skip"},
            {"id": "intro", "title": "Intro", "content": "Hello"},
            model_dump_section,
        ],
        "kpis": [{"name": "CTR"}],
        "influencer_plan": {"creator_count": 3},
        "listening_reporting_plan": {"cadence": "weekly"},
        "execution_roadmap": {"phase": "launch"},
        "costs_summary": {"currency": "MXN"},
        "sources": [FakeModelDump({"url": "https://example.com"})],
    }

    # Act
    output = deserialize_reputation_strategy_response(payload)

    # Assert
    assert [section.id for section in output.sections] == ["intro", "details"]
    assert output.assumptions == [{"assumption": "Market fit"}]
    assert output.sources == [{"url": "https://example.com"}]
    assert output.influencer_plan == {"creator_count": 3}


def test_reputation_strategy_response_invalid_raw_raises_type_error() -> None:
    # Arrange / Act / Assert
    try:
        deserialize_reputation_strategy_response("not-a-mapping")
    except TypeError as exc:
        assert "Unsupported response type for reputation deserialization" in str(exc)
    else:
        raise AssertionError("Expected invalid response to raise TypeError")


def test_reputation_strategy_output_to_dict_preserves_all_sections() -> None:
    # Arrange
    output = ReputationStrategyOutput(
        meta={"source": "test"},
        assumptions=[{"assumption": "A"}],
        verified_facts=[{"claim": "B"}],
        sections=[
            ReputationStrategySection(
                id="intro",
                title="Intro",
                content="Hello",
            )
        ],
        kpis=[{"name": "CTR"}],
        influencer_plan={"count": 2},
        listening_reporting_plan={"cadence": "weekly"},
        execution_roadmap={"step": "launch"},
        costs_summary={"total": 100},
        sources=[{"url": "https://example.com"}],
    )

    # Act
    serialized = output.to_dict()

    # Assert
    assert serialized == {
        "meta": {"source": "test"},
        "assumptions": [{"assumption": "A"}],
        "verified_facts": [{"claim": "B"}],
        "sections": [{"id": "intro", "title": "Intro", "content": "Hello"}],
        "kpis": [{"name": "CTR"}],
        "influencer_plan": {"count": 2},
        "listening_reporting_plan": {"cadence": "weekly"},
        "execution_roadmap": {"step": "launch"},
        "costs_summary": {"total": 100},
        "sources": [{"url": "https://example.com"}],
    }


def test_reputation_strategy_html_renders_assumptions_facts_and_text_blocks() -> None:
    # Arrange
    payload = {
        "assumptions": [
            {"assumption": "Audience trusts reviews", "risk_if_wrong": "Lower CTR"},
            {"assumption": "No risk note"},
            {"assumption": ""},
        ],
        "verified_facts": [
            {"claim": "Brand launched", "source_url": "https://example.com/?a=1&b=2"},
            {"claim": "No source"},
            {"claim": ""},
        ],
        "sections": [
            {
                "id": "intro",
                "title": "Plan <One>",
                "content": "First line\nSecond <line>",
            }
        ],
    }

    # Act
    html = render_reputation_strategy_sections_html(payload)

    # Assert
    assert html.startswith('<article class="reputation-strategy-ai">')
    assert "<strong>Audience trusts reviews</strong><br>Risk: Lower CTR" in html
    assert "<li>No risk note</li>" in html
    assert "https://example.com/?a=1&amp;b=2" in html
    assert "<h2>Plan &lt;One&gt;</h2>" in html
    assert "First line<br>Second &lt;line&gt;" in html


def test_reputation_strategy_html_renders_numbered_bulleted_and_inline_lists() -> None:
    # Arrange
    output = ReputationStrategyOutput(
        sections=[
            ReputationStrategySection(
                id="ordered",
                title="Ordered",
                content="1. Start\n2. Scale",
            ),
            ReputationStrategySection(
                id="bullets",
                title="Bullets",
                content="- Trust\n* Conversion\n• Retention",
            ),
            ReputationStrategySection(
                id="inline",
                title="Inline",
                content="Steps: (1) Recruit creators (2) Measure lift",
            ),
            ReputationStrategySection(id="empty", title="Empty", content="   "),
        ]
    )

    # Act
    html = render_reputation_strategy_sections_html(output)

    # Assert
    assert "<ol><li>Start</li><li>Scale</li></ol>" in html
    assert "<ul><li>Trust</li><li>Conversion</li><li>Retention</li></ul>" in html
    assert "<p>Steps</p><ol><li>Recruit creators</li><li>Measure lift</li></ol>" in html
    assert "<h2>Empty</h2>" not in html


def test_serialize_creator_strategy_payload_infers_language_and_sets_status() -> None:
    serialized = serialize_creator_strategy_payload(
        {
            "creator_username": "creator_one",
            "creator_context": "Creator focused on wellness and productivity.",
            "goal_type": "Community Trust",
            "goal_context": "Need to reinforce audience trust during sponsored launches.",
            "audience": ["Gen Z"],
            "timeframe": "6 months",
            "primary_platforms": ["Instagram"],
            "current_metrics": {
                "total_likes": 220,
                "avg_engagement_rate": 0.12,
            },
        }
    )

    assert serialized["response_language"] == "en"
    assert serialized["current_metrics"]["reels_metrics_status"] == "unavailable"


def test_serialize_creator_strategy_payload_infers_portuguese_when_present() -> None:
    serialized = serialize_creator_strategy_payload(
        {
            "creator_username": "creator_one",
            "creator_context": "Criadora focada em beleza e rotina prática.",
            "goal_type": "Community Trust",
            "goal_context": "Queremos fortalecer a confiança da audiência nas publis.",
            "audience": ["Gen Z"],
            "timeframe": "6 months",
            "primary_platforms": ["Instagram"],
            "current_metrics": {
                "total_likes": 220,
                "avg_engagement_rate": 0.12,
            },
        }
    )

    assert serialized["response_language"] == "pt-BR"
    assert serialized["current_metrics"]["reels_metrics_status"] == "unavailable"


def test_creator_strategy_payload_aliases_and_optional_fields_serializes_expected_contract() -> (
    None
):
    # Arrange
    payload = _creator_payload() | {
        "current_metrics": {"reels_metrics_status": "available", "views": 100},
        "reputation_signals": {
            "strengths": "Trust",
            "weaknesses": [" Low cadence ", None],
            "incidents": "",
            "concerns": ["Disclosure"],
        },
        "collaborators": [" Brand One ", 42],
    }

    # Act
    serialized = serialize_creator_strategy_payload(payload)

    # Assert
    assert serialized["creator_username"] == "Creator.One"
    assert serialized["creator_urls"] == ["https://instagram.com/creator.one"]
    assert serialized["audience"] == ["Gen Z"]
    assert serialized["primary_platforms"] == ["Instagram", "YouTube"]
    assert serialized["current_metrics"] == {
        "reels_metrics_status": "available",
        "views": 100,
    }
    assert serialized["reputation_signals"] == {
        "strengths": ["Trust"],
        "weaknesses": ["Low cadence"],
        "concerns": ["Disclosure"],
    }
    assert serialized["collaborators_list"] == ["Brand One", "42"]


def test_creator_strategy_payload_filters_empty_signal_values() -> None:
    # Arrange
    payload = _creator_payload() | {
        "current_metrics": {},
        "reputation_signals": {
            "strengths": [" ", None],
            "weaknesses": "",
            "incidents": [],
            "concerns": None,
            "ignored": ["not serialized"],
        },
        "collaborators": [],
    }

    # Act
    serialized = serialize_creator_strategy_payload(payload)

    # Assert
    assert "reputation_signals" not in serialized
    assert "collaborators_list" not in serialized
    assert serialized["current_metrics"]["reels_metrics_status"] == "unavailable"


def test_creator_strategy_payload_model_dump_input_is_supported() -> None:
    # Arrange
    payload = FakeModelDump(_creator_payload())

    # Act
    serialized = serialize_creator_strategy_payload(payload)

    # Assert
    assert payload.modes == ["json"]
    assert serialized["creator_urls"] == ["https://instagram.com/creator.one"]


def test_creator_strategy_payload_invalid_type_raises_type_error() -> None:
    # Arrange / Act / Assert
    try:
        serialize_creator_strategy_payload(object())
    except TypeError as exc:
        assert "Unsupported payload type for creator strategy input" in str(exc)
    else:
        raise AssertionError("Expected invalid creator payload to raise TypeError")


def test_creator_strategy_response_deserialization_filters_invalid_sections() -> None:
    # Arrange
    payload = {
        "meta": {"source": "openai"},
        "assumptions": [FakeModelDump({"assumption": "Audience trust"})],
        "verified_facts": [{"claim": "Fact"}],
        "sections": [
            {"id": "", "title": "Missing id", "content": "skip"},
            {"id": "missing-title", "title": "", "content": "skip"},
            FakeModelDump({"id": "intro", "title": "Intro", "content": "Hello"}),
        ],
        "kpis": [FakeModelDump({"name": "Trust score"})],
        "execution_roadmap": {"phase": "launch"},
        "sources": [{"url": "https://example.com"}],
    }

    # Act
    output = deserialize_creator_strategy_response(payload)

    # Assert
    assert [section.id for section in output.sections] == ["intro"]
    assert output.assumptions == [{"assumption": "Audience trust"}]
    assert output.kpis == [{"name": "Trust score"}]
    assert output.execution_roadmap == {"phase": "launch"}


def test_creator_strategy_response_invalid_raw_raises_type_error() -> None:
    # Arrange / Act / Assert
    try:
        deserialize_creator_strategy_response(["not", "mapping"])
    except TypeError as exc:
        assert "Unsupported response type for creator strategy deserialization" in str(
            exc
        )
    else:
        raise AssertionError("Expected invalid creator response to raise TypeError")


def test_creator_strategy_output_to_dict_preserves_response_shape() -> None:
    # Arrange
    output = ReputationCreatorStrategyOutput(
        meta={"source": "test"},
        assumptions=[{"assumption": "A"}],
        verified_facts=[{"claim": "B"}],
        sections=[
            ReputationCreatorStrategySection(
                id="intro",
                title="Intro",
                content="Hello",
            )
        ],
        kpis=[{"name": "Trust"}],
        execution_roadmap={"step": "launch"},
        sources=[{"url": "https://example.com"}],
    )

    # Act
    serialized = output.to_dict()

    # Assert
    assert serialized == {
        "meta": {"source": "test"},
        "assumptions": [{"assumption": "A"}],
        "verified_facts": [{"claim": "B"}],
        "sections": [{"id": "intro", "title": "Intro", "content": "Hello"}],
        "kpis": [{"name": "Trust"}],
        "execution_roadmap": {"step": "launch"},
        "sources": [{"url": "https://example.com"}],
    }


def test_creator_strategy_html_renders_assumptions_sources_and_list_formats() -> None:
    # Arrange
    output = ReputationCreatorStrategyOutput(
        assumptions=[
            {
                "assumption": "Audience trusts creator",
                "risk_if_wrong": "Low conversion",
            },
            {"assumption": "No risk"},
            {"assumption": ""},
        ],
        verified_facts=[
            {"claim": "Follower growth", "source_url": "https://example.com/?x=1&y=2"},
            {"claim": "No URL"},
            {"claim": ""},
        ],
        sections=[
            ReputationCreatorStrategySection(
                id="ordered",
                title="Ordered <Plan>",
                content="1. Audit\n2. Launch",
            ),
            ReputationCreatorStrategySection(
                id="bullets",
                title="Bullets",
                content="- Trust\n- Conversion",
            ),
            ReputationCreatorStrategySection(
                id="inline",
                title="Inline",
                content="Steps: 1. Prepare 2. Publish",
            ),
            ReputationCreatorStrategySection(
                id="paragraph",
                title="Paragraph",
                content="Line one\nLine <two>",
            ),
        ],
    )

    # Act
    html = render_creator_strategy_sections_html(output)

    # Assert
    assert "<strong>Audience trusts creator</strong><br>Risk: Low conversion" in html
    assert "<li>No risk</li>" in html
    assert "https://example.com/?x=1&amp;y=2" in html
    assert "<h2>Ordered &lt;Plan&gt;</h2>" in html
    assert "<ol><li>Audit</li><li>Launch</li></ol>" in html
    assert "<ul><li>Trust</li><li>Conversion</li></ul>" in html
    assert "<p>Steps</p><ol><li>Prepare</li><li>Publish</li></ol>" in html
    assert "Line one<br>Line &lt;two&gt;" in html


def test_build_strategy_request_kwargs_embeds_prompt_metadata() -> None:
    req_kwargs = build_strategy_request_kwargs(
        "reputation_campaign_strategy",
        {
            "brand_name": "Kiizama",
            "brand_context": "Marca de skincare con ingredientes limpios.",
            "brand_goals_type": "Trust & Credibility Acceleration",
            "brand_goals_context": "Queremos fortalecer la confianza de compra.",
            "audience": ["Gen Z"],
            "timeframe": "6 months",
            "campaign_type": "all_micro_performance_community_trust",
            "profiles_list": [
                {
                    "username": "creator_one",
                    "metrics": {
                        "total_posts": 12,
                        "total_comments": 48,
                        "total_likes": 360,
                        "avg_engagement_rate": 0.12,
                        "hashtags_per_post": 1.5,
                        "mentions_per_post": 0.5,
                        "total_reels": 0,
                        "total_plays": 0,
                        "overall_post_engagement_rate": 0.13,
                        "reel_engagement_rate_on_plays": 0.0,
                        "reels_metrics_status": "unavailable",
                    },
                }
            ],
        },
    )

    prompt_payload = json.loads(req_kwargs["prompt"])
    assert prompt_payload["response_language"] == "es"
    assert (
        prompt_payload["profiles_list"][0]["metrics"]["reels_metrics_status"]
        == "unavailable"
    )


def test_parse_strategy_response_rejects_invalid_json() -> None:
    try:
        parse_strategy_response("reputation_creator_strategy", "{not-json")
    except ValueError as exc:
        assert "Invalid strategy JSON response" in str(exc)
    else:
        raise AssertionError("Expected invalid JSON to raise ValueError")


class FakeOpenAIService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(
        self,
        option: str,
        *,
        function_kwargs: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((option, function_kwargs or {}))
        return json.dumps(
            {
                "meta": {"source": "fake"},
                "sections": [
                    {
                        "id": "intro",
                        "title": "Intro",
                        "content": "Creator strategy",
                    }
                ],
            }
        )


def test_execute_strategy_template_dispatches_service_and_parses_output() -> None:
    service = FakeOpenAIService()

    result = asyncio.run(
        execute_strategy_template(
            "reputation_creator_strategy",
            {
                "creator_username": "creator_one",
                "creator_context": "Creator focused on wellness.",
                "goal_type": "Community Trust",
                "goal_context": "Reinforce trust in launches.",
                "audience": ["Gen Z"],
                "timeframe": "6 months",
                "primary_platforms": ["Instagram"],
                "current_metrics": {},
            },
            service=service,
        )
    )

    assert service.calls[0][0] == "create_response"
    assert "prompt" in service.calls[0][1]
    assert result.meta == {"source": "fake"}
    assert result.sections[0].id == "intro"


def test_reputation_prompts_and_models_use_gpt54_contracts() -> None:
    assert DEFAULT_MODEL == "gpt-5.4-mini"
    assert IG_OPENAI_REQUEST.model == "gpt-5.4-nano-2026-03-17"
    assert REPUTATION_OPENAI_REQUEST.model == "gpt-5.4-2026-03-05"
    assert CREATOR_OPENAI_REQUEST.model == "gpt-5.4-2026-03-05"

    for prompt in (
        SYSTEM_PROMPT_REPUTATION_OPENAI_REQUEST,
        SYSTEM_PROMPT_REPUTATION_CREATOR_OPENAI_REQUEST,
    ):
        assert "response_language" in prompt
        assert '["es", "en", "pt-BR"]' in prompt
        assert "reels_metrics_status" in prompt
        assert "post-based metrics as the primary evidence base" in prompt
