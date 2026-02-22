"""Repository layer for the feature template."""

from collections.abc import Sequence

from .classes import ExampleEntity


class FeatureTemplateRepository:
    """Replace with real persistence calls when wiring the feature."""

    async def list_entities(self) -> Sequence[ExampleEntity]:
        return []
