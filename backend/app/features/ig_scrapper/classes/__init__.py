"""Data container classes (dataclasses) for the Instagram scraper feature."""

from .data import (
    CredentialCandidate,
    InstagramNavigateResult,
    InstagramPost,
    InstagramProfile,
    InstagramReel,
    InstagramScrapeResult,
    InstagramSuggestedUser,
    SessionValidationResult,
)

__all__ = [
    "CredentialCandidate",
    "SessionValidationResult",
    "InstagramNavigateResult",
    "InstagramPost",
    "InstagramProfile",
    "InstagramReel",
    "InstagramScrapeResult",
    "InstagramSuggestedUser",
]
