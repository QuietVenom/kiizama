from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit


def instagram_cdn_expiry(
    url: str,
) -> tuple[datetime | None, float | None]:
    if not url:
        return None, None

    qs = parse_qs(urlsplit(url).query)
    oe = (qs.get("oe") or [""])[0]
    if not oe:
        return None, None

    try:
        timestamp = int(oe, 16)
    except (TypeError, ValueError):
        return None, None

    expires_at = datetime.fromtimestamp(timestamp, tz=UTC)
    seconds_left = (expires_at - datetime.now(UTC)).total_seconds()
    return expires_at, seconds_left


def should_refresh_profile(existing_profile: Mapping[str, Any] | None) -> bool:
    if not existing_profile:
        return True

    profile_pic_url = existing_profile.get("profile_pic_url")
    if not profile_pic_url:
        return True

    _, seconds_left = instagram_cdn_expiry(str(profile_pic_url))
    if seconds_left is None:
        return True
    return seconds_left <= 0


__all__ = ["instagram_cdn_expiry", "should_refresh_profile"]
