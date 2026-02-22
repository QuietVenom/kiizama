from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from app.features.general.types import HtmlPdfReportGenerator, enrich_profile_picture


class ReputationCreatorStrategyReportGenerator(HtmlPdfReportGenerator):
    """HTML/PDF generator for the Reputation Creator Strategy template."""

    def __init__(
        self,
        template_path: str,
        template_name: str = "reputation_creator_strategy.html",
    ):
        super().__init__(template_path=template_path, template_name=template_name)
        self.logger = logging.getLogger(__name__)

    def build_context(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            context = dict(data)
        elif isinstance(data, Mapping):
            context = dict(data)
        elif hasattr(data, "model_dump"):
            context = data.model_dump(mode="json")
        else:
            return {}

        enrich_profile_picture(
            context,
            logger=self.logger,
            url_field="creator_profile_pic_url",
            src_field="creator_profile_pic_url",
        )
        return context


__all__ = ["ReputationCreatorStrategyReportGenerator"]
