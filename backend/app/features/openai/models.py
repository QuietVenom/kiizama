"""Lightweight models used by OpenAI feature helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .classes import OpenAIRequestTemplate


@dataclass(frozen=True, slots=True)
class OpenAIRequestTemplateRecord:
    """Serializable metadata snapshot for a request template."""

    name: str
    model: str | None
    has_system_prompt: bool
    has_text_schema: bool
    has_tools: bool


def build_openai_request_template_record(
    name: str,
    template: OpenAIRequestTemplate,
) -> OpenAIRequestTemplateRecord:
    return OpenAIRequestTemplateRecord(
        name=name,
        model=template.model,
        has_system_prompt=bool(template.system_prompt),
        has_text_schema=bool(template.text),
        has_tools=bool(template.tools),
    )


__all__ = [
    "OpenAIRequestTemplateRecord",
    "build_openai_request_template_record",
]
