from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, cast


def coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return cast(dict[str, Any], value.model_dump())
    return {}


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def safe_username(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def safe_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def snapshot_is_more_recent(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    left_scraped = left.get("scraped_at")
    right_scraped = right.get("scraped_at")
    if left_scraped is None:
        return False
    if right_scraped is None:
        return True
    return bool(left_scraped > right_scraped)


def build_campaign_template_name(brand_name: str) -> str:
    normalized = safe_slug(brand_name) or "brand"
    return f"reputation_campaign_strategy_{normalized}.html"


def build_creator_template_name(creator_username: str) -> str:
    normalized = re.sub(r"[^a-z0-9._]+", "_", creator_username.strip().lower())
    normalized = normalized.strip("_") or "creator"
    return f"reputation_creator_strategy_{normalized}.html"


def safe_slug(value: str | None) -> str:
    if not value:
        return ""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return slug.lower()


__all__ = [
    "coerce_mapping",
    "normalize_string_list",
    "safe_username",
    "string_or_none",
    "safe_int",
    "safe_float",
    "snapshot_is_more_recent",
    "build_campaign_template_name",
    "build_creator_template_name",
]
