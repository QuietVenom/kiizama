from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import get_default_max_concurrent
from .constants import DEFAULT_USER_AGENT


class InstagramPostSchema(BaseModel):
    code: str | None = None
    caption_text: str | None = None
    is_paid_partnership: bool | None = None
    sponsor_tags: Any = None
    coauthor_producers: list[str] = Field(default_factory=list)
    comment_count: int | None = None
    like_count: int | None = None
    usertags: list[str] = Field(default_factory=list)
    timestamp: int | None = None
    media_type: int | None = None
    product_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramReelSchema(BaseModel):
    code: str | None = None
    play_count: int | None = None
    comment_count: int | None = None
    like_count: int | None = None
    media_type: int | None = None
    product_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramSuggestedUserSchema(BaseModel):
    username: str | None = None
    id: str | None = None
    full_name: str | None = None
    profile_pic_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramProfileSchema(BaseModel):
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
    bio_links: list[dict[str, Any]] = Field(default_factory=list)
    category_name: str | None = None
    has_guides: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchCountersSchema(BaseModel):
    requested: int = 0
    successful: int = 0
    failed: int = 0
    not_found: int = 0


class InstagramPostMetricsSchema(BaseModel):
    total_posts: int = 0
    total_likes: int = 0
    total_comments: int = 0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_engagement_rate: float = 0.0
    hashtags_per_post: float = 0.0
    mentions_per_post: float = 0.0


class InstagramReelMetricsSchema(BaseModel):
    total_reels: int = 0
    total_plays: int = 0
    avg_plays: float = 0.0
    avg_reel_likes: float = 0.0
    avg_reel_comments: float = 0.0


class InstagramMetricsSchema(BaseModel):
    user: InstagramProfileSchema = Field(default_factory=InstagramProfileSchema)
    post_metrics: InstagramPostMetricsSchema = Field(
        default_factory=InstagramPostMetricsSchema
    )
    reel_metrics: InstagramReelMetricsSchema = Field(
        default_factory=InstagramReelMetricsSchema
    )
    overall_engagement_rate: float = 0.0
    followers: int = 0
    following: int = 0
    media_count: int = 0
    is_verified: bool = False
    is_private: bool = False
    recommended_users: list[InstagramSuggestedUserSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchProfileResult(BaseModel):
    user: InstagramProfileSchema = Field(default_factory=InstagramProfileSchema)
    recommended_users: list[InstagramSuggestedUserSchema] = Field(default_factory=list)
    posts: list[InstagramPostSchema] = Field(default_factory=list)
    reels: list[InstagramReelSchema] = Field(default_factory=list)
    success: bool = False
    error: str | None = None
    metrics: InstagramMetricsSchema = Field(default_factory=InstagramMetricsSchema)
    ai_categories: list[str] = Field(
        default_factory=list,
        description="OpenAI-predicted categories for the profile content.",
    )
    ai_roles: list[str] = Field(
        default_factory=list,
        description="OpenAI-predicted roles for the profile tone/positioning.",
    )
    ai_error: str | None = Field(
        default=None,
        description="Error details when AI analysis fails.",
    )

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchUsernameStatus(BaseModel):
    username: str
    status: Literal["success", "failed", "skipped", "not_found"]
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchScrapeResponse(BaseModel):
    results: dict[str, InstagramBatchProfileResult] = Field(default_factory=dict)
    counters: InstagramBatchCountersSchema = Field(
        default_factory=InstagramBatchCountersSchema
    )
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchScrapeSummaryResponse(BaseModel):
    usernames: list[InstagramBatchUsernameStatus] = Field(default_factory=list)
    counters: InstagramBatchCountersSchema = Field(
        default_factory=InstagramBatchCountersSchema
    )
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchRecommendationsResponse(BaseModel):
    usernames: list[InstagramBatchUsernameStatus] = Field(default_factory=list)
    recommendations: dict[str, list[InstagramSuggestedUserSchema]] = Field(
        default_factory=dict
    )
    counters: InstagramBatchCountersSchema = Field(
        default_factory=InstagramBatchCountersSchema
    )
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


def _normalize_requested_usernames(usernames: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_username in usernames:
        username = raw_username.strip().lower()
        if not username or username in seen:
            continue
        seen.add(username)
        normalized.append(username)

    if not normalized:
        raise ValueError("At least one non-empty username is required.")

    return normalized


class InstagramBaseScrapeRequest(BaseModel):
    # TEMP: Cap payload size to 10 usernames per request.
    usernames: list[str] = Field(min_length=1, max_length=10)
    timeout_ms: int = 30000
    headless: bool = True
    user_agent: str = DEFAULT_USER_AGENT
    locale: str = "en-US"
    max_posts: int = 12
    # Defaults to IG_SCRAPER_MAX_CONCURRENT when the caller omits the field.
    max_concurrent: int = Field(default_factory=get_default_max_concurrent, ge=1)
    measure_network_bytes: bool = Field(
        default=False,
        description=(
            "When true, tracks total downloaded bytes from Playwright responses "
            "(session validation + scraping)."
        ),
    )
    proxy: str | None = None

    @field_validator("usernames")
    @classmethod
    def _normalize_usernames(cls, usernames: list[str]) -> list[str]:
        return _normalize_requested_usernames(usernames)


# TEMP: Snapshot request model intentionally excludes `recommended_limit`.
class InstagramBatchScrapeRequest(InstagramBaseScrapeRequest):
    pass


# TEMP: `recommended_limit` is only exposed for recommendations endpoint payloads.
class InstagramBatchRecommendationsRequest(InstagramBatchScrapeRequest):
    recommended_limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum recommended users returned per profile.",
    )


# TEMP: Async snapshot jobs intentionally exclude `recommended_limit`.
class InstagramScrapeJobCreateRequest(InstagramBaseScrapeRequest):
    pass


class InstagramScrapeJobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued"]


class InstagramScrapeJobReferences(BaseModel):
    all_usernames: list[str] = Field(default_factory=list)
    successful_usernames: list[str] = Field(default_factory=list)
    failed_usernames: list[str] = Field(default_factory=list)
    skipped_usernames: list[str] = Field(default_factory=list)
    not_found_usernames: list[str] = Field(default_factory=list)


class InstagramScrapeJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    attempts: int = 0
    lease_owner: str | None = None
    leased_until: datetime | None = None
    heartbeat_at: datetime | None = None
    summary: InstagramBatchScrapeSummaryResponse | None = None
    references: InstagramScrapeJobReferences | None = None
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramScrapeJobTerminalizationRequest(BaseModel):
    status: Literal["done", "failed"]
    attempt: int = Field(ge=1)
    worker_id: str = Field(min_length=1)
    completed_at: datetime
    summary: InstagramBatchScrapeSummaryResponse
    error: str | None = None


class InstagramScrapeJobTerminalEventPayload(BaseModel):
    event_version: Literal[1] = 1
    notification_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    status: Literal["done", "failed"]
    created_at: datetime
    completed_at: datetime
    requested_usernames: list[str] = Field(default_factory=list)
    ready_usernames: list[str] = Field(default_factory=list)
    successful_usernames: list[str] = Field(default_factory=list)
    skipped_usernames: list[str] = Field(default_factory=list)
    failed_usernames: list[str] = Field(default_factory=list)
    not_found_usernames: list[str] = Field(default_factory=list)
    counters: InstagramBatchCountersSchema = Field(
        default_factory=InstagramBatchCountersSchema
    )
    error: str | None = None


class InstagramScrapeJobTerminalizationResponse(BaseModel):
    job_id: str
    decision: Literal["accepted_new", "accepted_pending", "duplicate", "conflict"]
    status: Literal["done", "failed"]
    notification_id: str = Field(min_length=1)
    terminal_event_id: str | None = None


__all__ = [
    "InstagramPostSchema",
    "InstagramProfileSchema",
    "InstagramReelSchema",
    "InstagramSuggestedUserSchema",
    "InstagramBatchCountersSchema",
    "InstagramPostMetricsSchema",
    "InstagramReelMetricsSchema",
    "InstagramMetricsSchema",
    "InstagramBatchProfileResult",
    "InstagramBatchUsernameStatus",
    "InstagramBatchScrapeRequest",
    "InstagramBatchRecommendationsRequest",
    "InstagramBatchScrapeResponse",
    "InstagramBatchScrapeSummaryResponse",
    "InstagramBatchRecommendationsResponse",
    "InstagramScrapeJobCreateRequest",
    "InstagramScrapeJobCreateResponse",
    "InstagramScrapeJobReferences",
    "InstagramScrapeJobStatusResponse",
    "InstagramScrapeJobTerminalEventPayload",
    "InstagramScrapeJobTerminalizationRequest",
    "InstagramScrapeJobTerminalizationResponse",
]
