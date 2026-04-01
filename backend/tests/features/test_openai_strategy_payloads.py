import json

from app.features.brand_intelligence.services.service_profiles import (
    build_creator_profile_summary,
    build_influencer_profiles_directory,
)
from app.features.openai.classes.openai_creator_data import (
    serialize_creator_strategy_payload,
)
from app.features.openai.classes.openai_prompt_metadata import (
    infer_response_language,
)
from app.features.openai.classes.openai_reputation_data import (
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
from app.features.openai.workflows import build_strategy_request_kwargs


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
