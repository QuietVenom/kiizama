from __future__ import annotations

import os
from pathlib import Path

TEMPLATES_DIR = (
    Path(__file__).resolve().parent.parent.parent / "templates" / "social_media_report"
)
CAMPAIGN_TEMPLATE_PATH = TEMPLATES_DIR / "reputation_campaign_strategy.html"
CREATOR_TEMPLATE_PATH = TEMPLATES_DIR / "reputation_creator_strategy.html"

REPUTATION_OPENAI_TIMEOUT_SECONDS = int(
    os.getenv("REPUTATION_OPENAI_TIMEOUT_SECONDS", "180")
)
REPUTATION_OPENAI_MAX_RETRIES = int(os.getenv("REPUTATION_OPENAI_MAX_RETRIES", "2"))

__all__ = [
    "TEMPLATES_DIR",
    "CAMPAIGN_TEMPLATE_PATH",
    "CREATOR_TEMPLATE_PATH",
    "REPUTATION_OPENAI_TIMEOUT_SECONDS",
    "REPUTATION_OPENAI_MAX_RETRIES",
]
