from __future__ import annotations

import uuid
from typing import Any

AMBASSADOR_OVERRIDE_CODE = "ambassador"
MANAGED_USAGE_SOURCE_TYPE = "managed"
MANAGED_PLAN_CODE = "managed"
MANAGED_USAGE_NAMESPACE = uuid.UUID("88e50131-2736-4d9e-bf48-25515de421ce")
ACCOUNT_TOPIC = "account"
ACCOUNT_SOURCE = "billing"
ACCOUNT_KIND = "state"
IDEMPOTENCY_HEADER_NAME = "Idempotency-Key"
TRIAL_PLAN_CODE = "trial"
BASE_PLAN_CODE = "base"
STRIPE_SIGNATURE_TOLERANCE_SECONDS = 300
STRIPE_CUSTOMER_SYNC_TYPE = "customer_email_update"
STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS = [60, 300, 900, 3600, 21600, 86400]
STRIPE_ALLOWED_ACTIVE_STATUSES = {"trialing", "active"}
STRIPE_BLOCKED_STATUSES = {
    "paused",
    "canceled",
    "incomplete",
    "incomplete_expired",
    "past_due",
    "unpaid",
}
FEATURE_SEED = (
    ("social_media_report", "Social Media Reports", "Report generation credits."),
    ("reputation_strategy", "Reputation Strategy", "Brand intelligence credits."),
    ("ig_scraper_apify", "Profiles", "Instagram profile scraping credits."),
)
PLAN_SEED: dict[str, dict[str, Any]] = {
    TRIAL_PLAN_CODE: {
        "name": "Trial",
        "billing_source": "internal",
        "limits": {
            "social_media_report": 3,
            "reputation_strategy": 2,
            "ig_scraper_apify": 15,
        },
    },
    BASE_PLAN_CODE: {
        "name": "Base",
        "billing_source": "stripe",
        "limits": {
            "social_media_report": 20,
            "reputation_strategy": 5,
            "ig_scraper_apify": 50,
        },
    },
}
FEATURE_ENDPOINT_KEYS = {
    "social_media_report": "social-media-report.instagram",
    "reputation_strategy.campaign": "brand-intelligence.reputation-campaign-strategy",
    "reputation_strategy.creator": "brand-intelligence.reputation-creator-strategy",
    "ig_scraper_apify": "ig-scraper.jobs.apify",
}
PUBLIC_FEATURE_CODE_ALIASES = {
    "ig_scraper_apify": "ig_scraper",
}


def public_feature_code(feature_code: str) -> str:
    return PUBLIC_FEATURE_CODE_ALIASES.get(feature_code, feature_code)


__all__ = [
    "ACCOUNT_KIND",
    "ACCOUNT_SOURCE",
    "ACCOUNT_TOPIC",
    "AMBASSADOR_OVERRIDE_CODE",
    "BASE_PLAN_CODE",
    "FEATURE_ENDPOINT_KEYS",
    "FEATURE_SEED",
    "IDEMPOTENCY_HEADER_NAME",
    "MANAGED_PLAN_CODE",
    "MANAGED_USAGE_NAMESPACE",
    "MANAGED_USAGE_SOURCE_TYPE",
    "PLAN_SEED",
    "PUBLIC_FEATURE_CODE_ALIASES",
    "STRIPE_ALLOWED_ACTIVE_STATUSES",
    "STRIPE_BLOCKED_STATUSES",
    "STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS",
    "STRIPE_CUSTOMER_SYNC_TYPE",
    "STRIPE_SIGNATURE_TOLERANCE_SECONDS",
    "TRIAL_PLAN_CODE",
    "public_feature_code",
]
