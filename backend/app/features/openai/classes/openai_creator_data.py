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


def _coerce_mapping_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): val for key, val in value.items()}
    return {}


def _coerce_mapping_list(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in _as_list(value):
        if isinstance(item, Mapping):
            result.append({str(key): val for key, val in item.items()})
            continue

        if callable(getattr(item, "model_dump", None)):
            dumpable = cast(SupportsModelDump, item)
            dumped = dumpable.model_dump(mode="json")
            if isinstance(dumped, Mapping):
                result.append({str(key): val for key, val in dumped.items()})
    return result


def _normalize_reputation_signals(value: Any) -> dict[str, list[str]]:
    raw = _coerce_mapping_dict(value)
    if not raw:
        return {}

    allowed_keys = ("strengths", "weaknesses", "incidents", "concerns")
    normalized: dict[str, list[str]] = {}
    for key in allowed_keys:
        items = [
            str(item).strip()
            for item in _as_list(raw.get(key))
            if item is not None and str(item).strip()
        ]
        if items:
            normalized[key] = items
    return normalized


@dataclass(slots=True)
class ReputationCreatorStrategyInput:
    creator_username: str
    creator_context: str
    creator_urls: list[str] = field(default_factory=list)
    goal_type: str = ""
    goal_context: str = ""
    audience: list[str] = field(default_factory=list)
    timeframe: str = ""
    primary_platforms: list[str] = field(default_factory=list)
    current_metrics: dict[str, Any] = field(default_factory=dict)
    reputation_signals: dict[str, Any] = field(default_factory=dict)
    collaborators_list: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(
        cls,
        payload: ReputationCreatorStrategyInput | Mapping[str, Any] | SupportsModelDump,
    ) -> ReputationCreatorStrategyInput:
        if isinstance(payload, cls):
            return payload

        raw_payload = _as_mapping(
            payload,
            error_message="Unsupported payload type for creator strategy input",
        )

        creator_urls_source = raw_payload.get("creator_urls")
        if creator_urls_source is None:
            creator_urls_source = raw_payload.get("creator_url")

        audience_source = raw_payload.get("audience")
        if audience_source is None:
            audience_source = raw_payload.get("Audience")

        collaborators_source = raw_payload.get("collaborators_list")
        if collaborators_source is None:
            collaborators_source = raw_payload.get("collaborators")

        return cls(
            creator_username=str(raw_payload.get("creator_username", "")).strip(),
            creator_context=str(raw_payload.get("creator_context", "")).strip(),
            creator_urls=[
                str(url).strip()
                for url in _as_list(creator_urls_source)
                if url is not None and str(url).strip()
            ],
            goal_type=str(raw_payload.get("goal_type", "")).strip(),
            goal_context=str(raw_payload.get("goal_context", "")).strip(),
            audience=[
                str(item).strip()
                for item in _as_list(audience_source)
                if item is not None and str(item).strip()
            ],
            timeframe=str(raw_payload.get("timeframe", "")).strip(),
            primary_platforms=[
                str(item).strip()
                for item in _as_list(raw_payload.get("primary_platforms"))
                if item is not None and str(item).strip()
            ],
            current_metrics=_coerce_mapping_dict(raw_payload.get("current_metrics")),
            reputation_signals=_normalize_reputation_signals(
                raw_payload.get("reputation_signals")
            ),
            collaborators_list=[
                str(item).strip()
                for item in _as_list(collaborators_source)
                if item is not None and str(item).strip()
            ],
        )


def serialize_creator_strategy_payload(
    payload: ReputationCreatorStrategyInput | Mapping[str, Any] | SupportsModelDump,
) -> dict[str, Any]:
    creator_input = ReputationCreatorStrategyInput.from_payload(payload)

    serialized: dict[str, Any] = {
        "creator_username": creator_input.creator_username,
        "creator_context": creator_input.creator_context,
        "creator_urls": creator_input.creator_urls,
        "goal_type": creator_input.goal_type,
        "goal_context": creator_input.goal_context,
        "audience": creator_input.audience,
        "timeframe": creator_input.timeframe,
        "primary_platforms": creator_input.primary_platforms,
        "current_metrics": creator_input.current_metrics,
    }

    if creator_input.reputation_signals:
        serialized["reputation_signals"] = creator_input.reputation_signals
    if creator_input.collaborators_list:
        serialized["collaborators_list"] = creator_input.collaborators_list

    return serialized


@dataclass(slots=True)
class ReputationCreatorStrategySection:
    id: str
    title: str
    content: str


@dataclass(slots=True)
class ReputationCreatorStrategyOutput:
    meta: dict[str, Any] = field(default_factory=dict)
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    verified_facts: list[dict[str, Any]] = field(default_factory=list)
    sections: list[ReputationCreatorStrategySection] = field(default_factory=list)
    kpis: list[dict[str, Any]] = field(default_factory=list)
    execution_roadmap: dict[str, Any] = field(default_factory=dict)
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
            "execution_roadmap": self.execution_roadmap,
            "sources": self.sources,
        }


def deserialize_creator_strategy_response(
    raw: Any,
) -> ReputationCreatorStrategyOutput:
    if not isinstance(raw, Mapping):
        raise TypeError(
            "Unsupported response type for creator strategy deserialization"
        )

    sections: list[ReputationCreatorStrategySection] = []
    for item in _coerce_mapping_list(raw.get("sections")):
        section_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        content = str(item.get("content", "")).strip()
        if not section_id or not title:
            continue
        sections.append(
            ReputationCreatorStrategySection(
                id=section_id,
                title=title,
                content=content,
            )
        )

    return ReputationCreatorStrategyOutput(
        meta=_coerce_mapping_dict(raw.get("meta")),
        assumptions=_coerce_mapping_list(raw.get("assumptions")),
        verified_facts=_coerce_mapping_list(raw.get("verified_facts")),
        sections=sections,
        kpis=_coerce_mapping_list(raw.get("kpis")),
        execution_roadmap=_coerce_mapping_dict(raw.get("execution_roadmap")),
        sources=_coerce_mapping_list(raw.get("sources")),
    )


_INLINE_NUMBERED_MARKER_PATTERN = re.compile(
    r"(?:^|\s)(?:\((\d{1,2})\)|(\d{1,2})[.)])\s+"
)
_LINE_NUMBERED_MARKER_PATTERN = re.compile(r"^(?:\(\d{1,2}\)|\d{1,2}[.)])\s+(.+)$")
_LINE_BULLET_MARKER_PATTERN = re.compile(r"^[-*]\s+(.+)$")


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

    rendered_blocks: list[str] = []
    for block in blocks:
        rendered = _render_block(block)
        if rendered:
            rendered_blocks.append(rendered)
    return "".join(rendered_blocks)


def render_creator_strategy_sections_html(
    payload: ReputationCreatorStrategyOutput | Mapping[str, Any],
) -> str:
    output = (
        payload
        if isinstance(payload, ReputationCreatorStrategyOutput)
        else deserialize_creator_strategy_response(payload)
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
    "ReputationCreatorStrategyInput",
    "serialize_creator_strategy_payload",
    "ReputationCreatorStrategySection",
    "ReputationCreatorStrategyOutput",
    "deserialize_creator_strategy_response",
    "render_creator_strategy_sections_html",
]
