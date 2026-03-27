import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import Column, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel
from uuid6 import uuid7

PRIVATE_SCHEMA = "private"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid7() -> uuid.UUID:
    return uuid.UUID(str(uuid7()))


class IgCredential(SQLModel, table=True):
    __tablename__ = cast(Any, "ig_credentials")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    login_username: str = Field(unique=True, index=True, max_length=255)
    password_encrypted: str
    session_encrypted: str | None = None
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class IgScrapeJob(SQLModel, table=True):
    __tablename__ = cast(Any, "ig_scrape_jobs")
    __table_args__ = (
        Index("idx_ig_scrape_jobs_owner_created_at", "owner_user_id", "created_at"),
        Index("idx_ig_scrape_jobs_status_created_at", "status", "created_at"),
        Index("idx_ig_scrape_jobs_expires_at", "expires_at"),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    owner_user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    status: str = Field(default="queued", max_length=16, index=True)
    attempts: int = 0
    worker_id: str | None = Field(default=None, max_length=255)
    leased_until: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    heartbeat_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    failed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    summary: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    references: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = None
    notification_id: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class IgProfile(SQLModel, table=True):
    __tablename__ = cast(Any, "ig_profiles")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    ig_id: str = Field(unique=True, index=True, max_length=64)
    username: str = Field(unique=True, index=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    biography: str | None = None
    is_private: bool = False
    is_verified: bool = False
    profile_pic_url: str | None = Field(default=None, max_length=2048)
    profile_pic_src: str | None = None
    external_url: str | None = Field(default=None, max_length=2048)
    follower_count: int = 0
    following_count: int = 0
    media_count: int = 0
    bio_links: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )
    ai_categories: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )
    ai_roles: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    posts_documents: list["IgPostsDocument"] = Relationship(  # noqa: UP037
        back_populates="profile"
    )
    reels_documents: list["IgReelsDocument"] = Relationship(  # noqa: UP037
        back_populates="profile"
    )
    snapshots: list["IgProfileSnapshot"] = Relationship(  # noqa: UP037
        back_populates="profile"
    )


class IgPostsDocument(SQLModel, table=True):
    __tablename__ = cast(Any, "ig_posts_documents")
    __table_args__ = (
        Index("idx_ig_posts_documents_profile_updated_at", "profile_id", "updated_at"),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    profile_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.ig_profiles.id",
        nullable=False,
        index=True,
    )
    items: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    profile: IgProfile | None = Relationship(back_populates="posts_documents")
    snapshots: list["IgProfileSnapshot"] = Relationship(  # noqa: UP037
        back_populates="posts_document"
    )


class IgReelsDocument(SQLModel, table=True):
    __tablename__ = cast(Any, "ig_reels_documents")
    __table_args__ = (
        Index("idx_ig_reels_documents_profile_updated_at", "profile_id", "updated_at"),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    profile_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.ig_profiles.id",
        nullable=False,
        index=True,
    )
    items: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    profile: IgProfile | None = Relationship(back_populates="reels_documents")
    snapshots: list["IgProfileSnapshot"] = Relationship(  # noqa: UP037
        back_populates="reels_document"
    )


class IgMetrics(SQLModel, table=True):
    __tablename__ = cast(Any, "ig_metrics")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    total_posts: int = 0
    total_likes: int = 0
    total_comments: int = 0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_engagement_rate: float = 0.0
    hashtags_per_post: float = 0.0
    mentions_per_post: float = 0.0
    total_reels: int = 0
    total_plays: int = 0
    avg_plays: float = 0.0
    avg_reel_likes: float = 0.0
    avg_reel_comments: float = 0.0
    overall_post_engagement_rate: float = 0.0
    reel_engagement_rate_on_plays: float = 0.0
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    snapshots: list["IgProfileSnapshot"] = Relationship(  # noqa: UP037
        back_populates="metrics"
    )


class IgProfileSnapshot(SQLModel, table=True):
    __tablename__ = cast(Any, "ig_profile_snapshots")
    __table_args__ = (
        Index(
            "idx_ig_profile_snapshots_profile_scraped_at", "profile_id", "scraped_at"
        ),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    profile_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.ig_profiles.id",
        nullable=False,
        index=True,
    )
    posts_document_id: uuid.UUID | None = Field(
        default=None,
        foreign_key=f"{PRIVATE_SCHEMA}.ig_posts_documents.id",
    )
    reels_document_id: uuid.UUID | None = Field(
        default=None,
        foreign_key=f"{PRIVATE_SCHEMA}.ig_reels_documents.id",
    )
    metrics_id: uuid.UUID | None = Field(
        default=None,
        foreign_key=f"{PRIVATE_SCHEMA}.ig_metrics.id",
    )
    scraped_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    profile: IgProfile | None = Relationship(back_populates="snapshots")
    posts_document: IgPostsDocument | None = Relationship(back_populates="snapshots")
    reels_document: IgReelsDocument | None = Relationship(back_populates="snapshots")
    metrics: IgMetrics | None = Relationship(back_populates="snapshots")


__all__ = [
    "PRIVATE_SCHEMA",
    "IgCredential",
    "IgMetrics",
    "IgPostsDocument",
    "IgProfile",
    "IgProfileSnapshot",
    "IgReelsDocument",
    "IgScrapeJob",
    "generate_uuid7",
    "utcnow",
]
