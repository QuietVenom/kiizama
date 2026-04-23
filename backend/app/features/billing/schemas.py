from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from .models import BillingSubscription

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


@dataclass(frozen=True, slots=True)
class AccessSnapshot:
    access_profile: str
    managed_access_source: str | None
    billing_eligible: bool
    trial_eligible: bool
    plan_status: str
    subscription_status: str | None
    latest_invoice_status: str | None
    access_revoked_reason: str | None
    pending_ambassador_activation: bool
    cancel_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    features: list[BillingFeatureUsagePublic]
    notices: list[BillingNoticePublic]

    @property
    def renewal_day(self) -> date | None:
        if self.current_period_end is None:
            return None
        return self.current_period_end.date()


@dataclass(frozen=True, slots=True)
class SubscriptionSyncResult:
    subscription: BillingSubscription
    changed: bool


@dataclass(frozen=True, slots=True)
class RefundContext:
    invoice_id: str | None
    charge_id: str | None
    refund_status: str | None
    is_full_refund: bool


@dataclass(frozen=True, slots=True)
class StripeCustomerSyncError(Exception):
    message: str
    retryable: bool
    http_status: int | None = None
    stripe_request_id: str | None = None


__all__ = [
    "AccessProfile",
    "AccessProfileUpdate",
    "AccessSnapshot",
    "BillingCustomerSyncStatus",
    "BillingCustomerSyncType",
    "BillingEventProcessingStatus",
    "BillingFeatureUsagePublic",
    "BillingNoticeCollectionPublic",
    "BillingNoticePublic",
    "BillingNoticeStatus",
    "BillingNoticeType",
    "BillingSessionPublic",
    "BillingSubscriptionStatus",
    "BillingSummaryPublic",
    "BillingWebhookReceipt",
    "ManagedAccessSource",
    "PlanStatus",
    "RefundContext",
    "StripeCustomerSyncError",
    "SubscriptionSyncResult",
    "UsageCycleStatus",
    "UsageReservationStatus",
    "UsageResultStatus",
    "UsageSourceType",
]
