"""Service layer for the feature template."""

from collections.abc import Callable
from typing import Any

from .types.base import BaseTemplateWorker


class FeatureTemplateService:
    """Simple async service that delegates to a worker factory."""

    def __init__(self, worker_factory: Callable[[Any], BaseTemplateWorker]):
        self.worker_factory = worker_factory

    async def execute(self, payload: Any) -> Any:
        worker = self.worker_factory(payload)
        return await worker.run()


__all__ = ["FeatureTemplateService"]
