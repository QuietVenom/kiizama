"""Core logic classes for the Instagram scraper feature."""

from ..classes import SessionValidationResult
from .apify_ig_scraper import (
    ApifyInstagramExternalUrl,
    ApifyInstagramLatestPost,
    ApifyInstagramProfileItem,
    ApifyInstagramProfileScraper,
    ApifyInstagramRelatedProfile,
    ApifyInstagramTaggedUser,
)
from .base import BaseInstagramWorker
from .instagram_batch_scraper import InstagramBatchScraper, scrape_multiple_profiles
from .login_flow import InstagramLoginFlow, LoginFlowResult
from .session_validator import InstagramSessionValidator

__all__ = [
    "BaseInstagramWorker",
    "InstagramBatchScraper",
    "scrape_multiple_profiles",
    "InstagramLoginFlow",
    "LoginFlowResult",
    "InstagramSessionValidator",
    "SessionValidationResult",
    "ApifyInstagramExternalUrl",
    "ApifyInstagramLatestPost",
    "ApifyInstagramProfileItem",
    "ApifyInstagramProfileScraper",
    "ApifyInstagramRelatedProfile",
    "ApifyInstagramTaggedUser",
]
