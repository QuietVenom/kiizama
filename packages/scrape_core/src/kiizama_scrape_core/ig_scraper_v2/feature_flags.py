from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from sqlalchemy import text

RECOMMENDED_BACKGROUND_JOBS_FEATURE_FLAG = (
    "IG_SCRAPER_RECOMMENDED_BACKGROUND_JOBS_ENABLED"
)


def is_feature_flag_enabled(
    *,
    session_factory: Callable[[], AbstractContextManager[Any]],
    key: str,
    default: bool = False,
    logger: logging.Logger | None = None,
) -> bool:
    try:
        with session_factory() as session:
            result = session.execute(
                text(
                    """
                    SELECT is_enabled
                    FROM private.feature_flag
                    WHERE key = :key
                    LIMIT 1
                    """
                ),
                {"key": key},
            ).first()
    except Exception:
        if logger:
            logger.exception(
                "Failed to read feature flag %s from database; using default=%s.",
                key,
                default,
            )
        return default

    if result is None:
        return default

    if isinstance(result, bool):
        return result

    return bool(result[0])


def is_recommended_background_jobs_enabled(
    *,
    session_factory: Callable[[], AbstractContextManager[Any]],
    logger: logging.Logger | None = None,
) -> bool:
    return is_feature_flag_enabled(
        session_factory=session_factory,
        key=RECOMMENDED_BACKGROUND_JOBS_FEATURE_FLAG,
        default=False,
        logger=logger,
    )


__all__ = [
    "RECOMMENDED_BACKGROUND_JOBS_FEATURE_FLAG",
    "is_feature_flag_enabled",
    "is_recommended_background_jobs_enabled",
]
