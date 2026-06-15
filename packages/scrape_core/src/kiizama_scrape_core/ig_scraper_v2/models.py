from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ProfileOpenStatus(StrEnum):
    SUCCESS = "success"
    INVALID_USERNAME = "invalid_username"
    NOT_FOUND = "not_found"
    AUTH_LOST = "auth_lost"
    CHALLENGE = "challenge"
    WRONG_PROFILE = "wrong_profile"
    NAVIGATION_ERROR = "navigation_error"


@dataclass(frozen=True, slots=True)
class ProfileOpenResult:
    requested_username: str
    normalized_username: str
    final_url: str
    matched_username: str | None
    status: ProfileOpenStatus
    success: bool
    error: str | None = None


@dataclass(slots=True)
class BatchScrapeCounters:
    requested: int = 0
    successful: int = 0
    failed: int = 0
    not_found: int = 0


@dataclass(frozen=True, slots=True)
class InstagramBatchScrapeRunResult:
    success: bool
    credential_id: str | None
    session_message: str
    results: dict[str, dict[str, Any]]
    counters: BatchScrapeCounters
    error: str | None = None


__all__ = [
    "BatchScrapeCounters",
    "InstagramBatchScrapeRunResult",
    "ProfileOpenResult",
    "ProfileOpenStatus",
]
