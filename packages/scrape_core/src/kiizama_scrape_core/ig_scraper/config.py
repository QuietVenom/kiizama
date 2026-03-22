from __future__ import annotations

import os

DEFAULT_MAX_CONCURRENT = 2
MAX_CONCURRENT_ENV_VAR = "IG_SCRAPER_MAX_CONCURRENT"


def get_default_max_concurrent() -> int:
    raw = os.getenv(MAX_CONCURRENT_ENV_VAR)
    if raw is None or not raw.strip():
        return DEFAULT_MAX_CONCURRENT

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{MAX_CONCURRENT_ENV_VAR} must be a valid integer.") from exc

    if value < 1:
        raise ValueError(f"{MAX_CONCURRENT_ENV_VAR} must be greater than zero.")

    return value


__all__ = [
    "DEFAULT_MAX_CONCURRENT",
    "MAX_CONCURRENT_ENV_VAR",
    "get_default_max_concurrent",
]
