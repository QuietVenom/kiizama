from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlsplit


def instagram_cdn_expiry(
    url: str,
) -> tuple[datetime | None, float | None]:
    """
    Return (expires_at_utc, seconds_left) if `oe` exists, else (None, None).
    """
    if not url:
        return None, None

    qs = parse_qs(urlsplit(url).query)
    oe = (qs.get("oe") or [""])[0]
    if not oe:
        return None, None

    try:
        ts = int(oe, 16)
    except (TypeError, ValueError):
        return None, None

    expires_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    seconds_left = (expires_utc - datetime.now(timezone.utc)).total_seconds()
    return expires_utc, seconds_left


def should_refresh_profile(existing_profile: Mapping[str, Any] | None) -> bool:
    if not existing_profile:
        return True

    profile_pic_url = existing_profile.get("profile_pic_url")
    if not profile_pic_url:
        return True

    _, seconds_left = instagram_cdn_expiry(profile_pic_url)
    if seconds_left is None:
        return True
    return seconds_left <= 0
