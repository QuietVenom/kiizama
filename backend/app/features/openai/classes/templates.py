from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..types.base import DEFAULT_MODEL


@dataclass(slots=True)
class OpenAIRequestTemplate:
    """
    Encapsulate preset arguments for `OpenAIResponseService.create_response`.

    Use this to store common OpenAI call parameters so callers only need to
    select the template and forward the generated kwargs.
    """

    temperature: float | None = None
    model: str | None = DEFAULT_MODEL
    system_prompt: str | None = None
    response_format: dict[str, Any] | None = None
    text: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any = None
    include: list[str] | None = None

    def to_function_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments for `create_response` without `None` values."""

        raw_kwargs: dict[str, Any] = {
            "temperature": self.temperature,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "response_format": self.response_format,
            "text": self.text,
            "tools": self.tools,
            "tool_choice": self.tool_choice,
            "include": self.include,
        }
        return {key: value for key, value in raw_kwargs.items() if value is not None}
