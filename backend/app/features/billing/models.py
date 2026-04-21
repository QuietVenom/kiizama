from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Literal, cast

from kiizama_scrape_core.ig_scraper.sqlmodels import PRIVATE_SCHEMA
from pydantic import BaseModel
from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.core.ids import generate_uuid7

AccessProfile = Literal["standard", "ambassador"]
ManagedAccessSource = Literal["admin", "ambassador"]
PlanStatus = Literal["trial", "base", "ambassador", "none"]
BillingSubscriptionStatus = Literal[
    "trialing",
    "active",
    "paused",
    "canceled",
    "incomplete",
    "incomplete_expired",
    "past_due",
    "unpaid",
]
BillingEventProcessingStatus = Literal["pending", "processed", "ignored", "failed"]
BillingCustomerSyncType = Literal["customer_email_update"]
BillingCustomerSyncStatus = Literal["pending", "processing", "succeeded", "failed"]
BillingNoticeType = Literal[
    "invoice_upcoming",
    "trial_will_end",
    "subscription_paused",
    "access_revoked",
]
BillingNoticeStatus = Literal["unread", "read", "dismissed"]
UsageSourceType = Literal["subscription", "override", "managed"]
UsageCycleStatus = Literal["open", "closed", "revoked"]
UsageReservationStatus = Literal["reserved", "finalized", "released"]
UsageResultStatus = Literal["success", "partial_success", "no_charge", "reversed"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LuBillingFeature(SQLModel, table=True):
    __tablename__ = cast(Any, "lu_billing_feature")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=64)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=255)


class SubscriptionPlan(SQLModel, table=True):
    __tablename__ = cast(Any, "subscription_plan")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=32)
    name: str = Field(max_length=120)
    billing_source: str = Field(max_length=32)
    is_active: bool = True


class SubscriptionPlanFeatureLimit(SQLModel, table=True):
    __tablename__ = cast(Any, "subscription_plan_feature_limit")
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "feature_id",
            name="uq_private_subscription_plan_feature_limit_plan_feature",
        ),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    plan_id: int = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.subscription_plan.id",
        nullable=False,
        index=True,
    )
    feature_id: int = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.lu_billing_feature.id",
        nullable=False,
        index=True,
    )
    monthly_limit: int = Field(default=0, ge=0)
    is_unlimited: bool = False


class UserBillingAccount(SQLModel, table=True):
    __tablename__ = cast(Any, "user_billing_account")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
        unique=True,
    )
    stripe_customer_id: str | None = Field(
        default=None, max_length=255, index=True, unique=True
    )
    has_used_trial: bool = False
    trial_started_at: datetime | None = None
    trial_ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class BillingSubscription(SQLModel, table=True):
    __tablename__ = cast(Any, "billing_subscription")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    stripe_subscription_id: str = Field(unique=True, index=True, max_length=255)
    stripe_customer_id: str = Field(index=True, max_length=255)
    stripe_price_id: str | None = Field(default=None, max_length=255)
    plan_code: str = Field(max_length=32, default="base")
    status: str = Field(max_length=32, index=True)
    collection_method: str | None = Field(default=None, max_length=64)
    cancel_at_period_end: bool = False
    cancel_at: datetime | None = None
    cancellation_reason: str | None = Field(default=None, max_length=64)
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    paused_at: datetime | None = None
    canceled_at: datetime | None = None
    ended_at: datetime | None = None
    latest_invoice_id: str | None = Field(default=None, max_length=255)
    latest_invoice_status: str | None = Field(default=None, max_length=64)
    access_revoked_at: datetime | None = None
    access_revoked_reason: str | None = Field(default=None, max_length=128)
    last_stripe_event_created: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class BillingWebhookEvent(SQLModel, table=True):
    __tablename__ = cast(Any, "billing_webhook_event")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    stripe_event_id: str = Field(unique=True, index=True, max_length=255)
    event_type: str = Field(index=True, max_length=64)
    stripe_customer_id: str | None = Field(default=None, index=True, max_length=255)
    stripe_subscription_id: str | None = Field(default=None, index=True, max_length=255)
    stripe_invoice_id: str | None = Field(default=None, index=True, max_length=255)
    payload_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    processing_status: str = Field(default="pending", max_length=32, index=True)
    processing_error: str | None = Field(default=None)
    processed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class BillingCustomerSyncTask(SQLModel, table=True):
    __tablename__ = cast(Any, "billing_customer_sync_task")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    stripe_customer_id: str = Field(index=True, max_length=255)
    sync_type: str = Field(default="customer_email_update", max_length=64, index=True)
    desired_email: str = Field(max_length=255)
    status: str = Field(default="pending", max_length=32, index=True)
    attempt_count: int = Field(default=0, ge=0)
    next_attempt_at: datetime = Field(
        default_factory=utcnow, nullable=False, index=True
    )
    last_error: str | None = Field(default=None)
    last_http_status: int | None = Field(default=None)
    last_stripe_request_id: str | None = Field(default=None, max_length=255)
    succeeded_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class UserAccessOverride(SQLModel, table=True):
    __tablename__ = cast(Any, "user_access_override")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    code: str = Field(max_length=64, index=True)
    is_unlimited: bool = False
    starts_at: datetime = Field(default_factory=utcnow, nullable=False)
    ends_at: datetime | None = None
    revoked_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=255)
    created_by_admin_id: uuid.UUID | None = Field(
        default=None,
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
    )
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class UsageCycle(SQLModel, table=True):
    __tablename__ = cast(Any, "usage_cycle")
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_type",
            "source_id",
            "period_start",
            "period_end",
            name="uq_private_usage_cycle_subscription_period",
        ),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    source_type: str = Field(max_length=32)
    source_id: uuid.UUID | None = Field(default=None, index=True)
    plan_code: str = Field(max_length=32, index=True)
    period_start: datetime = Field(nullable=False)
    period_end: datetime | None = None
    status: str = Field(default="open", max_length=32, index=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class UsageCycleFeature(SQLModel, table=True):
    __tablename__ = cast(Any, "usage_cycle_feature")
    __table_args__ = (
        UniqueConstraint(
            "usage_cycle_id",
            "feature_code",
            name="uq_private_usage_cycle_feature_cycle_feature",
        ),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    usage_cycle_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.usage_cycle.id",
        nullable=False,
        index=True,
    )
    feature_code: str = Field(max_length=64, index=True)
    limit_count: int = Field(default=0, ge=0)
    used_count: int = Field(default=0, ge=0)
    reserved_count: int = Field(default=0, ge=0)
    is_unlimited: bool = False
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class UsageReservation(SQLModel, table=True):
    __tablename__ = cast(Any, "usage_reservation")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    request_key: str = Field(unique=True, index=True, max_length=255)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    usage_cycle_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.usage_cycle.id",
        nullable=False,
        index=True,
    )
    feature_code: str = Field(max_length=64, index=True)
    endpoint_key: str = Field(max_length=128)
    reserved_count: int = Field(default=0, ge=0)
    consumed_count: int = Field(default=0, ge=0)
    status: str = Field(default="reserved", max_length=32, index=True)
    job_id: str | None = Field(default=None, index=True, max_length=255)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    finalized_at: datetime | None = None


class UsageEvent(SQLModel, table=True):
    __tablename__ = cast(Any, "usage_event")
    __table_args__ = {"schema": PRIVATE_SCHEMA}

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    usage_cycle_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.usage_cycle.id",
        nullable=False,
        index=True,
    )
    feature_code: str = Field(max_length=64, index=True)
    endpoint_key: str = Field(max_length=128)
    request_key: str = Field(max_length=255, index=True)
    job_id: str | None = Field(default=None, index=True, max_length=255)
    quantity_requested: int = Field(default=0, ge=0)
    quantity_consumed: int = Field(default=0, ge=0)
    result_status: str = Field(default="success", max_length=32, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class BillingNotice(SQLModel, table=True):
    __tablename__ = cast(Any, "billing_notice")
    __table_args__ = (
        UniqueConstraint(
            "notice_key",
            name="uq_private_billing_notice_notice_key",
        ),
        {"schema": PRIVATE_SCHEMA},
    )

    id: uuid.UUID = Field(default_factory=generate_uuid7, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key=f"{PRIVATE_SCHEMA}.user.id",
        nullable=False,
        index=True,
    )
    notice_type: str = Field(max_length=64, index=True)
    status: str = Field(default="unread", max_length=32, index=True)
    notice_key: str = Field(max_length=255, index=True)
    stripe_event_id: str | None = Field(default=None, max_length=255, index=True)
    stripe_subscription_id: str | None = Field(default=None, max_length=255, index=True)
    stripe_invoice_id: str | None = Field(default=None, max_length=255, index=True)
    title: str = Field(max_length=160)
    message: str = Field(max_length=500)
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    read_at: datetime | None = None
    dismissed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class BillingFeatureUsagePublic(BaseModel):
    code: str
    name: str
    limit: int | None
    used: int
    reserved: int
    remaining: int | None
    is_unlimited: bool = False


class BillingNoticePublic(BaseModel):
    id: uuid.UUID
    notice_type: BillingNoticeType
    status: BillingNoticeStatus
    title: str
    message: str
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class BillingSummaryPublic(BaseModel):
    access_profile: AccessProfile
    managed_access_source: ManagedAccessSource | None = None
    billing_eligible: bool
    trial_eligible: bool
    plan_status: PlanStatus
    subscription_status: str | None = None
    latest_invoice_status: str | None = None
    access_revoked_reason: str | None = None
    pending_ambassador_activation: bool = False
    cancel_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    renewal_day: date | None = None
    features: list[BillingFeatureUsagePublic]
    notices: list[BillingNoticePublic] = []


class BillingSessionPublic(BaseModel):
    url: str


class BillingWebhookReceipt(BaseModel):
    received: bool = True


class BillingNoticeCollectionPublic(BaseModel):
    data: list[BillingNoticePublic]


class AccessProfileUpdate(BaseModel):
    access_profile: AccessProfile


__all__ = [
    "AccessProfile",
    "AccessProfileUpdate",
    "BillingCustomerSyncStatus",
    "BillingCustomerSyncTask",
    "BillingCustomerSyncType",
    "BillingEventProcessingStatus",
    "BillingNotice",
    "BillingNoticeCollectionPublic",
    "BillingNoticePublic",
    "BillingNoticeStatus",
    "BillingNoticeType",
    "BillingSessionPublic",
    "BillingSubscription",
    "BillingSubscriptionStatus",
    "BillingSummaryPublic",
    "BillingWebhookEvent",
    "BillingWebhookReceipt",
    "BillingFeatureUsagePublic",
    "LuBillingFeature",
    "ManagedAccessSource",
    "PlanStatus",
    "SubscriptionPlan",
    "SubscriptionPlanFeatureLimit",
    "UsageCycle",
    "UsageCycleFeature",
    "UsageCycleStatus",
    "UsageEvent",
    "UsageReservation",
    "UsageReservationStatus",
    "UsageResultStatus",
    "UsageSourceType",
    "UserAccessOverride",
    "UserBillingAccount",
    "utcnow",
]
