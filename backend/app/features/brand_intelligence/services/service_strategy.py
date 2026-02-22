from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.features.openai.classes import (
    ReputationCreatorStrategyOutput,
    ReputationStrategyOutput,
)
from app.features.openai.workflows import execute_strategy_template

from ..schemas import (
    ReputationCampaignStrategyConfirmResponse,
    ReputationCreatorStrategyConfirmResponse,
)
from .service_config import (
    REPUTATION_OPENAI_MAX_RETRIES,
    REPUTATION_OPENAI_TIMEOUT_SECONDS,
)


def build_report_context(
    confirmation: ReputationCampaignStrategyConfirmResponse
    | ReputationCreatorStrategyConfirmResponse,
    *,
    ensure_current_metrics: bool = False,
) -> dict[str, Any]:
    context = confirmation.model_dump(mode="json")
    payload = context.pop("payload", {})
    if isinstance(payload, dict):
        context.update(payload)

    if ensure_current_metrics and not context.get("current_metrics"):
        current_metrics = getattr(confirmation, "current_metrics", None)
        if isinstance(current_metrics, Mapping):
            context["current_metrics"] = dict(current_metrics)

    return context


async def generate_reputation_strategy_output(
    context: Mapping[str, Any],
) -> ReputationStrategyOutput:
    return await execute_strategy_template(
        "reputation_campaign_strategy",
        context,
        timeout=REPUTATION_OPENAI_TIMEOUT_SECONDS,
        max_retries=REPUTATION_OPENAI_MAX_RETRIES,
    )


async def generate_reputation_creator_strategy_output(
    context: Mapping[str, Any],
) -> ReputationCreatorStrategyOutput:
    return await execute_strategy_template(
        "reputation_creator_strategy",
        context,
        timeout=REPUTATION_OPENAI_TIMEOUT_SECONDS,
        max_retries=REPUTATION_OPENAI_MAX_RETRIES,
    )


__all__ = [
    "build_report_context",
    "generate_reputation_strategy_output",
    "generate_reputation_creator_strategy_output",
]
