"""Pydantic schemas for OpenAI template catalog and strategy workflows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .workflows import StrategyTemplateName


class OpenAIRequestTemplateRecordSchema(BaseModel):
    name: str
    model: str | None = None
    has_system_prompt: bool = False
    has_text_schema: bool = False
    has_tools: bool = False


class OpenAIRequestTemplateCatalogResponse(BaseModel):
    items: list[OpenAIRequestTemplateRecordSchema] = Field(default_factory=list)


class OpenAIStrategyWorkflowRequest(BaseModel):
    template_name: StrategyTemplateName
    payload: dict[str, Any] = Field(default_factory=dict)


class OpenAIStrategyWorkflowKwargs(BaseModel):
    template_name: StrategyTemplateName
    function_kwargs: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "StrategyTemplateName",
    "OpenAIRequestTemplateRecordSchema",
    "OpenAIRequestTemplateCatalogResponse",
    "OpenAIStrategyWorkflowRequest",
    "OpenAIStrategyWorkflowKwargs",
]
