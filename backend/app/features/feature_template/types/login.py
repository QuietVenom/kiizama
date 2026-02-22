from __future__ import annotations

from typing import Any

from .base import BaseTemplateWorker


class TemplateLoginWorker(BaseTemplateWorker):
    """Placeholder worker. Replace with real login/navigation logic."""

    async def run(self) -> Any:
        return {"status": "ok", "details": "replace with real implementation"}
