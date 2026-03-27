from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from typing import Any, Literal, Protocol, TypeAlias, overload

from app.core.resilience import (
    UpstreamBadResponseError,
    mark_dependency_failure,
    mark_dependency_success,
    translate_openai_exception,
)

from .classes import (
    ReputationCreatorStrategyOutput,
    ReputationStrategyOutput,
    deserialize_creator_strategy_response,
    deserialize_reputation_strategy_response,
    get_openai_request_template,
    serialize_creator_strategy_payload,
    serialize_reputation_strategy_payload,
)
from .service import OpenAIService


class SupportsModelDump(Protocol):
    def model_dump(
        self, *, mode: str = "python", **kwargs: Any
    ) -> Mapping[str, Any]: ...


StrategyTemplateName: TypeAlias = Literal[
    "reputation_campaign_strategy",
    "reputation_creator_strategy",
]

StrategyOutput: TypeAlias = ReputationStrategyOutput | ReputationCreatorStrategyOutput
CampaignStrategyTemplateName: TypeAlias = Literal["reputation_campaign_strategy"]
CreatorStrategyTemplateName: TypeAlias = Literal["reputation_creator_strategy"]

_StrategySerializer = Callable[
    [Mapping[str, Any] | SupportsModelDump | Any],
    dict[str, Any],
]
_StrategyDeserializer = Callable[[Any], StrategyOutput]

_STRATEGY_SERIALIZERS: dict[StrategyTemplateName, _StrategySerializer] = {
    "reputation_campaign_strategy": serialize_reputation_strategy_payload,
    "reputation_creator_strategy": serialize_creator_strategy_payload,
}

_STRATEGY_DESERIALIZERS: dict[StrategyTemplateName, _StrategyDeserializer] = {
    "reputation_campaign_strategy": deserialize_reputation_strategy_response,
    "reputation_creator_strategy": deserialize_creator_strategy_response,
}

_STRATEGY_URL_KEYS: dict[StrategyTemplateName, str] = {
    "reputation_campaign_strategy": "brand_urls",
    "reputation_creator_strategy": "creator_urls",
}

STRATEGY_TEMPLATE_NAMES: tuple[StrategyTemplateName, ...] = tuple(
    sorted(_STRATEGY_SERIALIZERS)
)


def build_strategy_request_kwargs(
    template_name: StrategyTemplateName,
    payload: Mapping[str, Any] | SupportsModelDump | Any,
) -> dict[str, Any]:
    serializer = _resolve_strategy_serializer(template_name)
    template = get_openai_request_template(template_name)

    serialized_payload = serializer(payload)
    req_kwargs = template.to_function_kwargs()

    url_key = _STRATEGY_URL_KEYS[template_name]
    has_urls = _has_non_empty_urls(serialized_payload.get(url_key))
    if not has_urls:
        req_kwargs.pop("tools", None)
        req_kwargs.pop("tool_choice", None)
    elif req_kwargs.get("tools"):
        req_kwargs["tool_choice"] = "required"

    req_kwargs["prompt"] = json.dumps(serialized_payload, ensure_ascii=False)
    return req_kwargs


@overload
def parse_strategy_response(
    template_name: CampaignStrategyTemplateName,
    response_text: str,
) -> ReputationStrategyOutput: ...


@overload
def parse_strategy_response(
    template_name: CreatorStrategyTemplateName,
    response_text: str,
) -> ReputationCreatorStrategyOutput: ...


def parse_strategy_response(
    template_name: StrategyTemplateName,
    response_text: str,
) -> StrategyOutput:
    if not response_text or not str(response_text).strip():
        raise ValueError("OpenAI strategy response text is empty")

    deserializer = _resolve_strategy_deserializer(template_name)
    try:
        raw = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid strategy JSON response: {exc}") from exc

    return deserializer(raw)


@overload
async def execute_strategy_template(
    template_name: CampaignStrategyTemplateName,
    payload: Mapping[str, Any] | SupportsModelDump | Any,
    *,
    timeout: int = 180,
    max_retries: int = 2,
    service: OpenAIService | None = None,
) -> ReputationStrategyOutput: ...


@overload
async def execute_strategy_template(
    template_name: CreatorStrategyTemplateName,
    payload: Mapping[str, Any] | SupportsModelDump | Any,
    *,
    timeout: int = 180,
    max_retries: int = 2,
    service: OpenAIService | None = None,
) -> ReputationCreatorStrategyOutput: ...


async def execute_strategy_template(
    template_name: StrategyTemplateName,
    payload: Mapping[str, Any] | SupportsModelDump | Any,
    *,
    timeout: int = 180,
    max_retries: int = 2,
    service: OpenAIService | None = None,
) -> StrategyOutput:
    req_kwargs = build_strategy_request_kwargs(template_name, payload)
    resolved_service = service or OpenAIService(
        timeout=timeout,
        max_retries=max_retries,
    )

    try:
        response_text = await asyncio.to_thread(
            resolved_service.execute,
            "create_response",
            function_kwargs=req_kwargs,
        )
    except Exception as exc:  # pragma: no cover - network/runtime resilience
        translated = translate_openai_exception(
            exc,
            detail=f"OpenAI strategy call failed for '{template_name}': {exc}",
        )
        mark_dependency_failure(
            "openai",
            context=f"openai-strategy:{template_name}",
            detail=translated.detail,
            status="degraded",
            exc=exc,
        )
        raise translated from exc

    try:
        parsed = parse_strategy_response(template_name, str(response_text))
    except Exception as exc:
        translated = UpstreamBadResponseError(
            dependency="openai",
            detail=(
                f"Failed to parse OpenAI strategy response for '{template_name}': {exc}"
            ),
        )
        mark_dependency_failure(
            "openai",
            context=f"openai-strategy:{template_name}",
            detail=translated.detail,
            status="degraded",
            exc=exc,
        )
        raise translated from exc

    mark_dependency_success(
        "openai",
        context=f"openai-strategy:{template_name}",
        detail=f"OpenAI strategy '{template_name}' completed successfully.",
    )
    return parsed


def _resolve_strategy_serializer(
    template_name: StrategyTemplateName,
) -> _StrategySerializer:
    try:
        return _STRATEGY_SERIALIZERS[template_name]
    except KeyError as exc:
        available = ", ".join(STRATEGY_TEMPLATE_NAMES)
        raise KeyError(
            f"Unknown strategy template '{template_name}'. Available: {available}"
        ) from exc


def _resolve_strategy_deserializer(
    template_name: StrategyTemplateName,
) -> _StrategyDeserializer:
    try:
        return _STRATEGY_DESERIALIZERS[template_name]
    except KeyError as exc:
        available = ", ".join(STRATEGY_TEMPLATE_NAMES)
        raise KeyError(
            f"Unknown strategy template '{template_name}'. Available: {available}"
        ) from exc


def _has_non_empty_urls(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list | tuple):
        return any(str(item).strip() for item in value if item is not None)
    return bool(str(value).strip())


__all__ = [
    "StrategyTemplateName",
    "StrategyOutput",
    "STRATEGY_TEMPLATE_NAMES",
    "build_strategy_request_kwargs",
    "parse_strategy_response",
    "execute_strategy_template",
]
