from __future__ import annotations

from typing import Any


class BaseTemplateWorker:
    """Minimal async worker skeleton used by the template feature."""

    def __init__(self, payload: Any):
        self.payload = payload

    async def run(self) -> Any:  # pragma: no cover - override in subclasses
        raise NotImplementedError
