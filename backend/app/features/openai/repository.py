"""Repository helpers for OpenAI request templates."""

from collections.abc import Mapping, Sequence

from .classes import (
    OPENAI_REQUEST_TEMPLATES,
    OpenAIRequestTemplate,
    get_openai_request_template,
)
from .models import OpenAIRequestTemplateRecord, build_openai_request_template_record


class OpenAIRequestTemplateRepository:
    """Read-only repository over in-memory OpenAI request templates."""

    def list_template_names(self) -> tuple[str, ...]:
        return tuple(sorted(OPENAI_REQUEST_TEMPLATES))

    def list_templates(self) -> Mapping[str, OpenAIRequestTemplate]:
        return dict(OPENAI_REQUEST_TEMPLATES)

    def list_template_records(self) -> list[OpenAIRequestTemplateRecord]:
        return [
            build_openai_request_template_record(name, template)
            for name, template in sorted(OPENAI_REQUEST_TEMPLATES.items())
        ]

    def get_template(self, name: str) -> OpenAIRequestTemplate:
        return get_openai_request_template(name)

    async def list_entities(self) -> Sequence[OpenAIRequestTemplate]:
        return list(self.list_templates().values())


# Backwards-compatible alias for existing imports.
FeatureTemplateRepository = OpenAIRequestTemplateRepository


__all__ = [
    "OpenAIRequestTemplateRepository",
    "FeatureTemplateRepository",
]
