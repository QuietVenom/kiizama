from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CredentialCandidate:
    id: str
    login_username: str | None
    encrypted_password: str | None
    session: dict[str, Any] | None

    def has_session(self) -> bool:
        return bool(self.session)

    def has_login(self) -> bool:
        return bool(self.login_username and self.encrypted_password)


@dataclass(slots=True)
class SessionValidationResult:
    success: bool
    credential_id: str | None
    storage_state: dict[str, Any] | None
    message: str
    error: str | None = None


@dataclass(slots=True)
class InstagramPost:
    code: str | None = None
    caption_text: str | None = None
    is_paid_partnership: bool | None = None
    sponsor_tags: Any = None
    coauthor_producers: list[str] = field(default_factory=list)
    comment_count: int | None = None
    like_count: int | None = None
    usertags: list[str] = field(default_factory=list)
    timestamp: int | None = None
    media_type: int | None = None
    product_type: str | None = None


@dataclass(slots=True)
class InstagramReel:
    code: str | None = None
    play_count: int | None = None
    comment_count: int | None = None
    like_count: int | None = None
    media_type: int | None = None
    product_type: str | None = None


@dataclass(slots=True)
class InstagramSuggestedUser:
    username: str | None = None
    id: str | None = None
    full_name: str | None = None
    profile_pic_url: str | None = None


@dataclass(slots=True)
class InstagramProfile:
    id: str | None = None
    username: str | None = None
    full_name: str | None = None
    profile_pic_url: str | None = None
    biography: str | None = None
    is_private: bool | None = None
    is_regulated_c18: bool | None = None
    is_verified: bool | None = None
    account_type: int | None = None
    follower_count: int | None = None
    following_count: int | None = None
    media_count: int | None = None
    external_url: str | None = None
    bio_links: list[dict[str, Any]] = field(default_factory=list)
    category_name: str | None = None
    has_guides: bool | None = None


@dataclass(slots=True)
class InstagramScrapeResult:
    user: InstagramProfile = field(default_factory=InstagramProfile)
    recommended_users: list[InstagramSuggestedUser] = field(default_factory=list)
    posts: list[InstagramPost] = field(default_factory=list)
    reels: list[InstagramReel] = field(default_factory=list)
    success: bool = False
    error: str | None = None


@dataclass(slots=True)
class InstagramNavigateResult:
    status: str = "error"
    message: str = "Unknown error"
    profile_url: str = ""
    scrape: InstagramScrapeResult = field(default_factory=InstagramScrapeResult)
    success: bool = False
    error: str | None = None


__all__ = [
    "InstagramNavigateResult",
    "InstagramPost",
    "InstagramProfile",
    "InstagramReel",
    "InstagramScrapeResult",
    "InstagramSuggestedUser",
]
