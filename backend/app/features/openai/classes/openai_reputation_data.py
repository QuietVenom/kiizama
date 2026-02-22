from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from html import escape
from typing import Any, Protocol, cast


class SupportsModelDump(Protocol):
    def model_dump(
        self, *, mode: str = "python", **kwargs: Any
    ) -> Mapping[str, Any]: ...


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_mapping(
    value: Mapping[str, Any] | SupportsModelDump | Any,
    *,
    error_message: str,
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value

    if callable(getattr(value, "model_dump", None)):
        dumpable = cast(SupportsModelDump, value)
        return dumpable.model_dump(mode="json")

    raise TypeError(error_message)


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _normalize_string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if item is not None]


@dataclass(slots=True)
class ReputationInfluencerMetricsInput:
    total_posts: int = 0
    total_comments: int = 0
    total_likes: int = 0
    avg_engagement_rate: float = 0.0
    hashtags_per_post: float = 0.0
    mentions_per_post: float = 0.0
    total_reels: int = 0
    total_plays: int = 0
    overall_engagement_rate: float = 0.0

    @classmethod
    def from_payload(
        cls,
        payload: ReputationInfluencerMetricsInput
        | Mapping[str, Any]
        | SupportsModelDump,
    ) -> ReputationInfluencerMetricsInput:
        if isinstance(payload, cls):
            return payload

        raw_payload = _as_mapping(
            payload,
            error_message="Unsupported payload type for influencer metrics",
        )
        return cls(
            total_posts=_safe_int(raw_payload.get("total_posts")),
            total_comments=_safe_int(raw_payload.get("total_comments")),
            total_likes=_safe_int(raw_payload.get("total_likes")),
            avg_engagement_rate=_safe_float(raw_payload.get("avg_engagement_rate")),
            hashtags_per_post=_safe_float(raw_payload.get("hashtags_per_post")),
            mentions_per_post=_safe_float(raw_payload.get("mentions_per_post")),
            total_reels=_safe_int(raw_payload.get("total_reels")),
            total_plays=_safe_int(raw_payload.get("total_plays")),
            overall_engagement_rate=_safe_float(
                raw_payload.get("overall_engagement_rate")
            ),
        )


@dataclass(slots=True)
class ReputationInfluencerProfileInput:
    username: str
    full_name: str | None = None
    biography: str | None = None
    ai_categories: list[str] = field(default_factory=list)
    ai_roles: list[str] = field(default_factory=list)
    follower_count: int = 0
    is_verified: bool = False
    metrics: ReputationInfluencerMetricsInput = field(
        default_factory=ReputationInfluencerMetricsInput
    )

    @classmethod
    def from_payload(
        cls,
        payload: ReputationInfluencerProfileInput
        | Mapping[str, Any]
        | SupportsModelDump,
    ) -> ReputationInfluencerProfileInput:
        if isinstance(payload, cls):
            return payload

        raw_payload = _as_mapping(
            payload,
            error_message="Unsupported payload type for influencer profile",
        )

        metrics_source = raw_payload.get("metrics")
        if metrics_source is None:
            metrics = ReputationInfluencerMetricsInput()
        else:
            metrics = ReputationInfluencerMetricsInput.from_payload(metrics_source)

        username = str(raw_payload.get("username", "")).strip().lower()

        full_name_value = raw_payload.get("full_name")
        biography_value = raw_payload.get("biography")

        return cls(
            username=username,
            full_name=(
                str(full_name_value).strip() if full_name_value is not None else None
            )
            or None,
            biography=(
                str(biography_value).strip() if biography_value is not None else None
            )
            or None,
            ai_categories=_normalize_string_list(raw_payload.get("ai_categories")),
            ai_roles=_normalize_string_list(raw_payload.get("ai_roles")),
            follower_count=_safe_int(raw_payload.get("follower_count")),
            is_verified=_coerce_bool(raw_payload.get("is_verified"), False),
            metrics=metrics,
        )


@dataclass(slots=True)
class ReputationCostAnalysisSummaryInput:
    currency: str = "MXN"
    total_profiles: int = 0
    classified_profiles: int = 0
    unclassified_profiles: int = 0
    total_min_mxn: int = 0
    total_max_mxn: int = 0
    total_average_mxn: int = 0

    @classmethod
    def from_payload(
        cls,
        payload: ReputationCostAnalysisSummaryInput
        | Mapping[str, Any]
        | SupportsModelDump,
    ) -> ReputationCostAnalysisSummaryInput:
        if isinstance(payload, cls):
            return payload

        raw_payload = _as_mapping(
            payload,
            error_message="Unsupported payload type for cost analysis summary",
        )
        return cls(
            currency=str(raw_payload.get("currency", "MXN")) or "MXN",
            total_profiles=_safe_int(raw_payload.get("total_profiles")),
            classified_profiles=_safe_int(raw_payload.get("classified_profiles")),
            unclassified_profiles=_safe_int(raw_payload.get("unclassified_profiles")),
            total_min_mxn=_safe_int(raw_payload.get("total_min_mxn")),
            total_max_mxn=_safe_int(raw_payload.get("total_max_mxn")),
            total_average_mxn=_safe_int(raw_payload.get("total_average_mxn")),
        )


@dataclass(slots=True)
class ReputationCostSegmentInput:
    tier_key: str = ""
    tier_label: str = ""
    profiles_count: int = 0
    typical_deliverable: str | None = None
    segment_min_mxn: int = 0
    segment_max_mxn: int = 0
    segment_average_mxn: int = 0
    notes: str | None = None

    @classmethod
    def from_payload(
        cls,
        payload: ReputationCostSegmentInput | Mapping[str, Any] | SupportsModelDump,
    ) -> ReputationCostSegmentInput:
        if isinstance(payload, cls):
            return payload

        raw_payload = _as_mapping(
            payload,
            error_message="Unsupported payload type for cost segment",
        )
        typical_deliverable = raw_payload.get("typical_deliverable")
        notes_value = raw_payload.get("notes")

        return cls(
            tier_key=str(raw_payload.get("tier_key", "")),
            tier_label=str(raw_payload.get("tier_label", "")),
            profiles_count=_safe_int(raw_payload.get("profiles_count")),
            typical_deliverable=(
                str(typical_deliverable).strip()
                if typical_deliverable is not None
                else None
            )
            or None,
            segment_min_mxn=_safe_int(raw_payload.get("segment_min_mxn")),
            segment_max_mxn=_safe_int(raw_payload.get("segment_max_mxn")),
            segment_average_mxn=_safe_int(raw_payload.get("segment_average_mxn")),
            notes=(str(notes_value).strip() if notes_value is not None else None)
            or None,
        )


@dataclass(slots=True)
class ReputationCostAnalysisInput:
    summary: ReputationCostAnalysisSummaryInput = field(
        default_factory=ReputationCostAnalysisSummaryInput
    )
    summary_by_segment: list[ReputationCostSegmentInput] = field(default_factory=list)

    @classmethod
    def from_payload(
        cls,
        payload: ReputationCostAnalysisInput | Mapping[str, Any] | SupportsModelDump,
    ) -> ReputationCostAnalysisInput:
        if isinstance(payload, cls):
            return payload

        raw_payload = _as_mapping(
            payload,
            error_message="Unsupported payload type for cost analysis",
        )

        summary_source = raw_payload.get("summary")
        if summary_source is None:
            summary = ReputationCostAnalysisSummaryInput()
        else:
            summary = ReputationCostAnalysisSummaryInput.from_payload(summary_source)

        segments = [
            ReputationCostSegmentInput.from_payload(item)
            for item in _as_list(raw_payload.get("summary_by_segment"))
            if item is not None
        ]

        return cls(summary=summary, summary_by_segment=segments)


@dataclass(slots=True)
class ReputationCampaignStrategyInput:
    """
    OpenAI-focused payload for the reputation strategy request.

    Supports both raw request data and enriched strategy context
    (influencer profiles + cost analysis).
    """

    brand_name: str
    brand_context: str
    brand_urls: list[str] = field(default_factory=list)
    brand_goals_type: str = ""
    brand_goals_context: str = ""
    audience: list[str] = field(default_factory=list)
    timeframe: str = ""
    profiles_list: list[ReputationInfluencerProfileInput] = field(default_factory=list)
    campaign_type: str = ""
    cost_analysis: ReputationCostAnalysisInput | None = None

    @classmethod
    def from_payload(
        cls,
        payload: ReputationCampaignStrategyInput
        | Mapping[str, Any]
        | SupportsModelDump,
    ) -> ReputationCampaignStrategyInput:
        """Build typed strategy input from mapping or Pydantic model."""

        if isinstance(payload, cls):
            return payload

        raw_payload = _as_mapping(
            payload,
            error_message="Unsupported payload type for reputation strategy input",
        )

        brand_urls_source = raw_payload.get("brand_urls")
        if brand_urls_source is None:
            brand_urls_source = raw_payload.get("brand_url")

        audience_source = raw_payload.get("audience")
        if audience_source is None:
            audience_source = raw_payload.get("Audience")

        profiles_source = raw_payload.get("influencer_profiles_directory")
        if profiles_source is None:
            profiles_source = raw_payload.get("profiles_list")

        profiles_list: list[ReputationInfluencerProfileInput] = []
        for item in _as_list(profiles_source):
            if item is None:
                continue

            if isinstance(item, str | int | float):
                username = str(item).strip().lower()
                if username:
                    profiles_list.append(
                        ReputationInfluencerProfileInput(username=username)
                    )
                continue

            profile = ReputationInfluencerProfileInput.from_payload(item)
            if profile.username:
                profiles_list.append(profile)

        cost_source = raw_payload.get("cost_analysis")
        if cost_source is None:
            cost_source = raw_payload.get("cost_estimates")

        cost_analysis = (
            ReputationCostAnalysisInput.from_payload(cost_source)
            if cost_source is not None
            else None
        )

        return cls(
            brand_name=str(raw_payload.get("brand_name", "")),
            brand_context=str(raw_payload.get("brand_context", "")),
            brand_urls=[
                str(url) for url in _as_list(brand_urls_source) if url is not None
            ],
            brand_goals_type=str(raw_payload.get("brand_goals_type", "")),
            brand_goals_context=str(raw_payload.get("brand_goals_context", "")),
            audience=[
                str(item) for item in _as_list(audience_source) if item is not None
            ],
            timeframe=str(raw_payload.get("timeframe", "")),
            profiles_list=profiles_list,
            campaign_type=str(raw_payload.get("campaign_type", "")),
            cost_analysis=cost_analysis,
        )


def _serialize_metrics(metrics: ReputationInfluencerMetricsInput) -> dict[str, Any]:
    return {
        "total_posts": metrics.total_posts,
        "total_comments": metrics.total_comments,
        "total_likes": metrics.total_likes,
        "avg_engagement_rate": metrics.avg_engagement_rate,
        "hashtags_per_post": metrics.hashtags_per_post,
        "mentions_per_post": metrics.mentions_per_post,
        "total_reels": metrics.total_reels,
        "total_plays": metrics.total_plays,
        "overall_engagement_rate": metrics.overall_engagement_rate,
    }


def _serialize_influencer_profile(
    profile: ReputationInfluencerProfileInput,
) -> dict[str, Any]:
    return {
        "username": profile.username,
        "full_name": profile.full_name,
        "biography": profile.biography,
        "ai_categories": profile.ai_categories,
        "ai_roles": profile.ai_roles,
        "follower_count": profile.follower_count,
        "is_verified": profile.is_verified,
        "metrics": _serialize_metrics(profile.metrics),
    }


def _serialize_cost_analysis(
    cost_analysis: ReputationCostAnalysisInput,
) -> dict[str, Any]:
    return {
        "summary": {
            "currency": cost_analysis.summary.currency,
            "total_profiles": cost_analysis.summary.total_profiles,
            "classified_profiles": cost_analysis.summary.classified_profiles,
            "unclassified_profiles": cost_analysis.summary.unclassified_profiles,
            "total_min_mxn": cost_analysis.summary.total_min_mxn,
            "total_max_mxn": cost_analysis.summary.total_max_mxn,
            "total_average_mxn": cost_analysis.summary.total_average_mxn,
        },
        "summary_by_segment": [
            {
                "tier_key": segment.tier_key,
                "tier_label": segment.tier_label,
                "profiles_count": segment.profiles_count,
                "typical_deliverable": segment.typical_deliverable,
                "segment_min_mxn": segment.segment_min_mxn,
                "segment_max_mxn": segment.segment_max_mxn,
                "segment_average_mxn": segment.segment_average_mxn,
                "notes": segment.notes,
            }
            for segment in cost_analysis.summary_by_segment
        ],
    }


def serialize_reputation_strategy_payload(
    payload: ReputationCampaignStrategyInput | Mapping[str, Any] | SupportsModelDump,
) -> dict[str, Any]:
    """
    Convert the reputation strategy input into an OpenAI-ready JSON payload.

    Keeps a stable key contract aligned with the system prompt.
    """

    reputation_input = ReputationCampaignStrategyInput.from_payload(payload)
    serialized: dict[str, Any] = {
        "brand_name": reputation_input.brand_name,
        "brand_context": reputation_input.brand_context,
        "brand_urls": reputation_input.brand_urls,
        "brand_goals_type": reputation_input.brand_goals_type,
        "brand_goals_context": reputation_input.brand_goals_context,
        "audience": reputation_input.audience,
        "timeframe": reputation_input.timeframe,
        "profiles_list": [
            _serialize_influencer_profile(profile)
            for profile in reputation_input.profiles_list
        ],
        "campaign_type": reputation_input.campaign_type,
    }

    if reputation_input.cost_analysis is not None:
        serialized["cost_analysis"] = _serialize_cost_analysis(
            reputation_input.cost_analysis
        )

    return serialized


@dataclass(slots=True)
class ReputationStrategySection:
    id: str
    title: str
    content: str


@dataclass(slots=True)
class ReputationStrategyOutput:
    meta: dict[str, Any] = field(default_factory=dict)
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    verified_facts: list[dict[str, Any]] = field(default_factory=list)
    sections: list[ReputationStrategySection] = field(default_factory=list)
    kpis: list[dict[str, Any]] = field(default_factory=list)
    influencer_plan: dict[str, Any] = field(default_factory=dict)
    listening_reporting_plan: dict[str, Any] = field(default_factory=dict)
    execution_roadmap: dict[str, Any] = field(default_factory=dict)
    costs_summary: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta,
            "assumptions": self.assumptions,
            "verified_facts": self.verified_facts,
            "sections": [
                {
                    "id": section.id,
                    "title": section.title,
                    "content": section.content,
                }
                for section in self.sections
            ],
            "kpis": self.kpis,
            "influencer_plan": self.influencer_plan,
            "listening_reporting_plan": self.listening_reporting_plan,
            "execution_roadmap": self.execution_roadmap,
            "costs_summary": self.costs_summary,
            "sources": self.sources,
        }


def _coerce_mapping_list(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in _as_list(value):
        if isinstance(item, Mapping):
            result.append({str(key): val for key, val in item.items()})
        elif callable(getattr(item, "model_dump", None)):
            dumpable = cast(SupportsModelDump, item)
            dumped = dumpable.model_dump(mode="json")
            if isinstance(dumped, Mapping):
                result.append({str(key): val for key, val in dumped.items()})
    return result


def _coerce_mapping_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): val for key, val in value.items()}
    return {}


def deserialize_reputation_strategy_response(
    raw: Any,
) -> ReputationStrategyOutput:
    if not isinstance(raw, Mapping):
        raise TypeError("Unsupported response type for reputation deserialization")

    sections: list[ReputationStrategySection] = []
    for item in _coerce_mapping_list(raw.get("sections")):
        section_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        content = str(item.get("content", "")).strip()
        if not section_id or not title:
            continue
        sections.append(
            ReputationStrategySection(
                id=section_id,
                title=title,
                content=content,
            )
        )

    return ReputationStrategyOutput(
        meta=_coerce_mapping_dict(raw.get("meta")),
        assumptions=_coerce_mapping_list(raw.get("assumptions")),
        verified_facts=_coerce_mapping_list(raw.get("verified_facts")),
        sections=sections,
        kpis=_coerce_mapping_list(raw.get("kpis")),
        influencer_plan=_coerce_mapping_dict(raw.get("influencer_plan")),
        listening_reporting_plan=_coerce_mapping_dict(
            raw.get("listening_reporting_plan")
        ),
        execution_roadmap=_coerce_mapping_dict(raw.get("execution_roadmap")),
        costs_summary=_coerce_mapping_dict(raw.get("costs_summary")),
        sources=_coerce_mapping_list(raw.get("sources")),
    )


_INLINE_NUMBERED_MARKER_PATTERN = re.compile(
    r"(?:^|\s)(?:\((\d{1,2})\)|(\d{1,2})[.)])\s+"
)
_LINE_NUMBERED_MARKER_PATTERN = re.compile(r"^(?:\(\d{1,2}\)|\d{1,2}[.)])\s+(.+)$")
_LINE_BULLET_MARKER_PATTERN = re.compile(r"^[-*•]\s+(.+)$")


def _render_ordered_list(items: list[str]) -> str:
    rows = [f"<li>{escape(item)}</li>" for item in items if item.strip()]
    if not rows:
        return ""
    return f"<ol>{''.join(rows)}</ol>"


def _render_unordered_list(items: list[str]) -> str:
    rows = [f"<li>{escape(item)}</li>" for item in items if item.strip()]
    if not rows:
        return ""
    return f"<ul>{''.join(rows)}</ul>"


def _extract_inline_numbered_items(text: str) -> tuple[str, list[str]] | None:
    matches = list(_INLINE_NUMBERED_MARKER_PATTERN.finditer(text))
    if len(matches) < 2:
        return None

    prefix = text[: matches[0].start()].strip(" \t:;-")
    items: list[str] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        item = text[start:end].strip(" \t;")
        if item:
            items.append(item)

    if len(items) < 2:
        return None

    return prefix, items


def _render_block(block: str) -> str:
    raw_lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not raw_lines:
        return ""

    numbered_lines: list[str] = []
    for line in raw_lines:
        match = _LINE_NUMBERED_MARKER_PATTERN.match(line)
        if not match:
            numbered_lines = []
            break
        numbered_lines.append(match.group(1).strip())
    if numbered_lines:
        return _render_ordered_list(numbered_lines)

    bullet_lines: list[str] = []
    for line in raw_lines:
        match = _LINE_BULLET_MARKER_PATTERN.match(line)
        if not match:
            bullet_lines = []
            break
        bullet_lines.append(match.group(1).strip())
    if bullet_lines:
        return _render_unordered_list(bullet_lines)

    normalized_text = " ".join(raw_lines).strip()
    inline_numbered = _extract_inline_numbered_items(normalized_text)
    if inline_numbered is not None:
        prefix, items = inline_numbered
        rendered_parts: list[str] = []
        if prefix:
            rendered_parts.append(f"<p>{escape(prefix)}</p>")
        rendered_parts.append(_render_ordered_list(items))
        return "".join(rendered_parts)

    escaped_lines = [escape(line) for line in raw_lines]
    return f"<p>{'<br>'.join(escaped_lines)}</p>"


def _render_text_blocks(value: str) -> str:
    blocks = [block.strip() for block in value.split("\n\n") if block.strip()]
    if not blocks:
        return ""

    paragraphs: list[str] = []
    for block in blocks:
        rendered = _render_block(block)
        if not rendered:
            continue
        paragraphs.append(rendered)
    return "".join(paragraphs)


def render_reputation_strategy_sections_html(
    payload: ReputationStrategyOutput | Mapping[str, Any],
) -> str:
    output = (
        payload
        if isinstance(payload, ReputationStrategyOutput)
        else deserialize_reputation_strategy_response(payload)
    )

    parts: list[str] = ['<article class="reputation-strategy-ai">']

    if output.assumptions:
        parts.append("<section><h2>Assumptions</h2><ul>")
        for item in output.assumptions:
            text = str(item.get("assumption", "")).strip()
            risk = str(item.get("risk_if_wrong", "")).strip()
            if not text:
                continue
            if risk:
                parts.append(
                    f"<li><strong>{escape(text)}</strong><br>Risk: {escape(risk)}</li>"
                )
            else:
                parts.append(f"<li>{escape(text)}</li>")
        parts.append("</ul></section>")

    if output.verified_facts:
        parts.append("<section><h2>Verified Facts</h2><ul>")
        for item in output.verified_facts:
            claim = str(item.get("claim", "")).strip()
            source_url = str(item.get("source_url", "")).strip()
            if not claim:
                continue
            if source_url:
                safe_url = escape(source_url, quote=True)
                parts.append(
                    f"<li>{escape(claim)} "
                    f'(<a href="{safe_url}" target="_blank" rel="noopener">{safe_url}</a>)</li>'
                )
            else:
                parts.append(f"<li>{escape(claim)}</li>")
        parts.append("</ul></section>")

    for section in output.sections:
        title = escape(section.title)
        content_html = _render_text_blocks(section.content)
        if not content_html:
            continue
        parts.append(f"<section><h2>{title}</h2>{content_html}</section>")

    parts.append("</article>")
    return "".join(parts)


__all__ = [
    "ReputationInfluencerMetricsInput",
    "ReputationInfluencerProfileInput",
    "ReputationCostAnalysisSummaryInput",
    "ReputationCostSegmentInput",
    "ReputationCostAnalysisInput",
    "ReputationCampaignStrategyInput",
    "serialize_reputation_strategy_payload",
    "ReputationStrategySection",
    "ReputationStrategyOutput",
    "deserialize_reputation_strategy_response",
    "render_reputation_strategy_sections_html",
]
