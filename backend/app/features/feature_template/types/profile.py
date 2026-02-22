from __future__ import annotations

from typing import Any

from .base import BaseTemplateWorker


class TemplateProfileWorker(BaseTemplateWorker):
    """Placeholder profile worker. Replace with real scrape/profile logic."""

    async def run(self) -> Any:
        return {"status": "ok", "details": "replace with profile workflow"}
