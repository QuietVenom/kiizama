from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

InstagramScrapeJobExecutionMode = Literal["worker", "apify"]


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

    model_config = ConfigDict(from_attributes=True)


class InstagramPostMetricsSchema(BaseModel):
    total_posts: int = 0
    total_likes: int = 0
    total_comments: int = 0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_engagement_rate: float = 0.0
    hashtags_per_post: float = 0.0
    mentions_per_post: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class InstagramReelMetricsSchema(BaseModel):
    total_reels: int = 0
    total_plays: int = 0
    avg_plays: float = 0.0
    avg_reel_likes: float = 0.0
    avg_reel_comments: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class InstagramMetricsSchema(BaseModel):
    post_metrics: InstagramPostMetricsSchema = Field(
        default_factory=InstagramPostMetricsSchema
    )
    reel_metrics: InstagramReelMetricsSchema = Field(
        default_factory=InstagramReelMetricsSchema
    )
    overall_post_engagement_rate: float = 0.0
    reel_engagement_rate_on_plays: float = 0.0
    followers: int = 0
    following: int = 0
    media_count: int = 0
    is_verified: bool = False
    is_private: bool = False

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchProfileResult(BaseModel):
    user: InstagramProfileSchema = Field(default_factory=InstagramProfileSchema)
    recommended_users: list[InstagramSuggestedUserSchema] = Field(default_factory=list)
    posts: list[InstagramPostSchema] = Field(default_factory=list)
    reels: list[InstagramReelSchema] = Field(default_factory=list)
    success: bool = False
    error: str | None = None
    metrics: InstagramMetricsSchema = Field(default_factory=InstagramMetricsSchema)
    ai_categories: list[str] = Field(default_factory=list)
    ai_roles: list[str] = Field(default_factory=list)
    ai_error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchScrapeResponse(BaseModel):
    results: dict[str, InstagramBatchProfileResult] = Field(default_factory=dict)
    counters: InstagramBatchCountersSchema = Field(
        default_factory=InstagramBatchCountersSchema
    )
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchUsernameStatus(BaseModel):
    username: str
    status: Literal["success", "failed", "skipped", "not_found"]
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchScrapeSummaryResponse(BaseModel):
    usernames: list[InstagramBatchUsernameStatus] = Field(default_factory=list)
    counters: InstagramBatchCountersSchema = Field(
        default_factory=InstagramBatchCountersSchema
    )
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstagramScrapeJobReferences(BaseModel):
    all_usernames: list[str] = Field(default_factory=list)
    successful_usernames: list[str] = Field(default_factory=list)
    failed_usernames: list[str] = Field(default_factory=list)
    skipped_usernames: list[str] = Field(default_factory=list)
    not_found_usernames: list[str] = Field(default_factory=list)


class InstagramScrapeJobStatusResponse(BaseModel):
    job_id: str
    execution_mode: InstagramScrapeJobExecutionMode = "worker"
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


class InstagramPublicScrapeRequest(BaseModel):
    usernames: list[str] = Field(min_length=1, max_length=10)

    @field_validator("usernames")
    @classmethod
    def _normalize_usernames(cls, usernames: list[str]) -> list[str]:
        return _normalize_requested_usernames(usernames)

    model_config = ConfigDict(from_attributes=True)


class InstagramBatchScrapeRequest(InstagramPublicScrapeRequest):
    pass


class InstagramScrapeJobCreateRequest(InstagramPublicScrapeRequest):
    pass


class InstagramScrapeJobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued"]

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "InstagramBatchCountersSchema",
    "InstagramBatchProfileResult",
    "InstagramBatchScrapeRequest",
    "InstagramBatchScrapeResponse",
    "InstagramBatchScrapeSummaryResponse",
    "InstagramBatchUsernameStatus",
    "InstagramMetricsSchema",
    "InstagramPostMetricsSchema",
    "InstagramPostSchema",
    "InstagramProfileSchema",
    "InstagramPublicScrapeRequest",
    "InstagramReelMetricsSchema",
    "InstagramReelSchema",
    "InstagramScrapeJobCreateRequest",
    "InstagramScrapeJobCreateResponse",
    "InstagramScrapeJobExecutionMode",
    "InstagramScrapeJobReferences",
    "InstagramScrapeJobStatusResponse",
    "InstagramScrapeJobTerminalEventPayload",
    "InstagramScrapeJobTerminalizationRequest",
    "InstagramScrapeJobTerminalizationResponse",
    "InstagramSuggestedUserSchema",
]
