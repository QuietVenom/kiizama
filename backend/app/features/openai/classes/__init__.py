"""Dataclasses and lightweight containers for the OpenAI feature."""

from .openai_creator_data import (
    ReputationCreatorStrategyInput,
    ReputationCreatorStrategyOutput,
    deserialize_creator_strategy_response,
    render_creator_strategy_sections_html,
    serialize_creator_strategy_payload,
)
from .openai_ig_catalogs import IG_CATEGORY_LABELS, IG_ROLE_LABELS
from .openai_ig_data import (
    InstagramProfileAnalysisBatchInput,
    InstagramProfileAnalysisBatchResult,
    InstagramProfileAnalysisInput,
    InstagramProfileAnalysisResult,
    deserialize_profile_analysis_response,
    serialize_profile_analysis_payload,
)
from .openai_reputation_data import (
    ReputationCampaignStrategyInput,
    ReputationStrategyOutput,
    deserialize_reputation_strategy_response,
    render_reputation_strategy_sections_html,
    serialize_reputation_strategy_payload,
)
from .openai_requests import (
    CREATOR_OPENAI_REQUEST,
    IG_OPENAI_REQUEST,
    OPENAI_REQUEST_TEMPLATES,
    REPUTATION_OPENAI_REQUEST,
    get_openai_request_template,
)
from .templates import OpenAIRequestTemplate

__all__ = [
    "OpenAIRequestTemplate",
    "IG_OPENAI_REQUEST",
    "REPUTATION_OPENAI_REQUEST",
    "CREATOR_OPENAI_REQUEST",
    "OPENAI_REQUEST_TEMPLATES",
    "get_openai_request_template",
    "InstagramProfileAnalysisInput",
    "InstagramProfileAnalysisResult",
    "InstagramProfileAnalysisBatchInput",
    "InstagramProfileAnalysisBatchResult",
    "serialize_profile_analysis_payload",
    "deserialize_profile_analysis_response",
    "IG_CATEGORY_LABELS",
    "IG_ROLE_LABELS",
    "ReputationCampaignStrategyInput",
    "ReputationStrategyOutput",
    "serialize_reputation_strategy_payload",
    "deserialize_reputation_strategy_response",
    "render_reputation_strategy_sections_html",
    "ReputationCreatorStrategyInput",
    "ReputationCreatorStrategyOutput",
    "serialize_creator_strategy_payload",
    "deserialize_creator_strategy_response",
    "render_creator_strategy_sections_html",
]
