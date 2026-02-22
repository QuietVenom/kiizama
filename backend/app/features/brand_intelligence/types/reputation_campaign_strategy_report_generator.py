from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from app.features.general.types import HtmlPdfReportGenerator, enrich_profile_picture


class ReputationCampaignStrategyReportGenerator(HtmlPdfReportGenerator):
    """HTML/PDF generator for the Reputation Campaign Strategy template."""

    def __init__(
        self,
        template_path: str,
        template_name: str = "reputation_campaign_strategy.html",
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

        influencers = context.get("influencer_profiles_directory")
        if isinstance(influencers, list):
            for influencer in influencers:
                if isinstance(influencer, dict):
                    enrich_profile_picture(influencer, logger=self.logger)

        return context


__all__ = ["ReputationCampaignStrategyReportGenerator"]
