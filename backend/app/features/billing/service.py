from __future__ import annotations

import asyncio
import hashlib
import hmac
import importlib
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, cast

import httpx
from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.features.user_events.repository import get_user_events_repository
from app.features.user_events.schemas import UserEventEnvelope

from .models import (
    BillingCustomerSyncTask,
    BillingFeatureUsagePublic,
    BillingNotice,
    BillingNoticePublic,
    BillingSubscription,
    BillingSummaryPublic,
    BillingWebhookEvent,
    LuBillingFeature,
    SubscriptionPlan,
    SubscriptionPlanFeatureLimit,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
    UserAccessOverride,
    UserBillingAccount,
    utcnow,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.models import User

AMBASSADOR_OVERRIDE_CODE = "ambassador"
MANAGED_USAGE_SOURCE_TYPE = "managed"
MANAGED_PLAN_CODE = "managed"
MANAGED_USAGE_NAMESPACE = uuid.UUID("88e50131-2736-4d9e-bf48-25515de421ce")
ACCOUNT_TOPIC = "account"
ACCOUNT_SOURCE = "billing"
ACCOUNT_KIND = "state"
IDEMPOTENCY_HEADER_NAME = "Idempotency-Key"
TRIAL_PLAN_CODE = "trial"
BASE_PLAN_CODE = "base"
STRIPE_SIGNATURE_TOLERANCE_SECONDS = 300
STRIPE_CUSTOMER_SYNC_TYPE = "customer_email_update"
STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS = [60, 300, 900, 3600, 21600, 86400]
STRIPE_ALLOWED_ACTIVE_STATUSES = {"trialing", "active"}
STRIPE_BLOCKED_STATUSES = {
    "paused",
    "canceled",
    "incomplete",
    "incomplete_expired",
    "past_due",
    "unpaid",
}
FEATURE_SEED = (
    ("social_media_report", "Social Media Reports", "Report generation credits."),
    ("reputation_strategy", "Reputation Strategy", "Brand intelligence credits."),
    ("ig_scraper_apify", "Profiles", "Instagram profile scraping credits."),
)
PLAN_SEED = {
    TRIAL_PLAN_CODE: {
        "name": "Trial",
        "billing_source": "internal",
        "limits": {
            "social_media_report": 3,
            "reputation_strategy": 2,
            "ig_scraper_apify": 15,
        },
    },
    BASE_PLAN_CODE: {
        "name": "Base",
        "billing_source": "stripe",
        "limits": {
            "social_media_report": 20,
            "reputation_strategy": 5,
            "ig_scraper_apify": 50,
        },
    },
}
FEATURE_ENDPOINT_KEYS = {
    "social_media_report": "social-media-report.instagram",
    "reputation_strategy.campaign": "brand-intelligence.reputation-campaign-strategy",
    "reputation_strategy.creator": "brand-intelligence.reputation-creator-strategy",
    "ig_scraper_apify": "ig-scraper.jobs.apify",
}
StripeRequestPayload = dict[str, str]
PUBLIC_FEATURE_CODE_ALIASES = {
    "ig_scraper_apify": "ig_scraper",
}


class BillingError(HTTPException):
    pass


class BillingAccessError(BillingError):
    def __init__(
        self, detail: str = "No active plan is available for this user."
    ) -> None:
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class BillingLimitExceededError(BillingError):
    def __init__(self, feature_code: str) -> None:
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Credit limit exceeded for feature "
                f"'{_public_feature_code(feature_code)}'."
            ),
        )


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


def seed_billing_catalog(*, session: Session) -> None:
    existing_features = {
        item.code: item for item in session.exec(select(LuBillingFeature)).all()
    }
    for code, name, description in FEATURE_SEED:
        feature = existing_features.get(code)
        if feature is None:
            feature = LuBillingFeature(code=code, name=name, description=description)
            session.add(feature)
            session.flush()
            existing_features[code] = feature
        elif feature.name != name or feature.description != description:
            feature.name = name
            feature.description = description
            session.add(feature)

    existing_plans = {
        item.code: item for item in session.exec(select(SubscriptionPlan)).all()
    }
    for code, payload in PLAN_SEED.items():
        plan = existing_plans.get(code)
        if plan is None:
            plan = SubscriptionPlan(
                code=code,
                name=str(payload["name"]),
                billing_source=str(payload["billing_source"]),
                is_active=True,
            )
            session.add(plan)
            session.flush()
            existing_plans[code] = plan
        else:
            plan.name = str(payload["name"])
            plan.billing_source = str(payload["billing_source"])
            plan.is_active = True
            session.add(plan)

    existing_limits = {
        (item.plan_id, item.feature_id): item
        for item in session.exec(select(SubscriptionPlanFeatureLimit)).all()
    }
    for code, payload in PLAN_SEED.items():
        plan = existing_plans[code]
        limits = cast(dict[str, int], payload["limits"])
        for feature_code, monthly_limit in limits.items():
            feature = existing_features[feature_code]
            limit = existing_limits.get((cast(int, plan.id), cast(int, feature.id)))
            if limit is None:
                limit = SubscriptionPlanFeatureLimit(
                    plan_id=cast(int, plan.id),
                    feature_id=cast(int, feature.id),
                    monthly_limit=monthly_limit,
                    is_unlimited=False,
                )
            else:
                limit.monthly_limit = monthly_limit
                limit.is_unlimited = False
            session.add(limit)
    session.commit()


def _stripe_headers() -> dict[str, str]:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured.",
        )
    return {"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}"}


async def _stripe_request_raw(
    method: str,
    path: str,
    *,
    data: StripeRequestPayload | None = None,
    params: StripeRequestPayload | None = None,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        **_stripe_headers(),
    }
    if extra_headers:
        headers.update(extra_headers)
    async with httpx.AsyncClient(
        base_url=settings.STRIPE_API_BASE,
        timeout=20.0,
    ) as client:
        return await client.request(
            method,
            path,
            data=data,
            params=params,
            headers=headers,
        )


async def _stripe_request(
    method: str,
    path: str,
    *,
    data: StripeRequestPayload | None = None,
    params: StripeRequestPayload | None = None,
) -> dict[str, Any]:
    response = await _stripe_request_raw(
        method,
        path,
        data=data,
        params=params,
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe request failed.",
        )
    return cast(dict[str, Any], response.json())


async def _set_subscription_cancel_at_period_end(
    *,
    stripe_subscription_id: str,
    cancel_at_period_end: bool,
) -> None:
    await _stripe_request(
        "POST",
        f"/v1/subscriptions/{stripe_subscription_id}",
        data={"cancel_at_period_end": "true" if cancel_at_period_end else "false"},
    )


async def _cancel_stripe_subscription_immediately(
    *, stripe_subscription_id: str
) -> None:
    await _stripe_request("DELETE", f"/v1/subscriptions/{stripe_subscription_id}")


async def _delete_stripe_customer(stripe_customer_id: str) -> None:
    await _stripe_request("DELETE", f"/v1/customers/{stripe_customer_id}")


async def ensure_stripe_customer(
    *,
    session: Session,
    user: Any,
) -> UserBillingAccount:
    account = _get_or_create_billing_account(session=session, user_id=user.id)
    if account.stripe_customer_id:
        return account

    payload: StripeRequestPayload = {
        "email": user.email,
        "metadata[user_id]": str(user.id),
    }
    if user.full_name:
        payload["name"] = user.full_name

    customer = await _stripe_request("POST", "/v1/customers", data=payload)
    account.stripe_customer_id = str(customer["id"])
    account.updated_at = utcnow()
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


async def create_checkout_session(*, session: Session, user: Any) -> str:
    _ensure_user_can_use_stripe_billing(session=session, user_id=user.id)
    if not settings.STRIPE_BASE_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe price is not configured.",
        )

    access = get_access_snapshot(session=session, user_id=user.id)
    if not access.billing_eligible:
        raise BillingAccessError("This user cannot purchase a plan.")
    if (
        access.subscription_status in STRIPE_ALLOWED_ACTIVE_STATUSES
        and access.access_revoked_reason is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active subscription already exists for this user.",
        )

    account = await ensure_stripe_customer(session=session, user=user)
    data: StripeRequestPayload = {
        "mode": "subscription",
        "customer": cast(str, account.stripe_customer_id),
        "line_items[0][price]": settings.STRIPE_BASE_PRICE_ID,
        "line_items[0][quantity]": "1",
        "success_url": _settings_payments_return_url(),
        "cancel_url": _settings_payments_return_url(),
        "metadata[user_id]": str(user.id),
        "subscription_data[metadata][user_id]": str(user.id),
    }
    if not account.has_used_trial:
        data["payment_method_collection"] = "if_required"
        data["subscription_data[trial_period_days]"] = str(settings.BILLING_TRIAL_DAYS)
        data[
            "subscription_data[trial_settings][end_behavior][missing_payment_method]"
        ] = "pause"

    stripe_session = await _stripe_request("POST", "/v1/checkout/sessions", data=data)
    url = stripe_session.get("url")
    if not isinstance(url, str) or not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe checkout session did not return a redirect URL.",
        )
    return url


async def create_portal_session(*, session: Session, user: Any) -> str:
    _ensure_user_can_use_stripe_billing(session=session, user_id=user.id)
    account = _get_billing_account(session=session, user_id=user.id)
    if account is None or not account.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer is available for this user.",
        )

    portal_session = await _stripe_request(
        "POST",
        "/v1/billing_portal/sessions",
        data={
            "customer": account.stripe_customer_id,
            "return_url": _settings_payments_return_url(),
        },
    )
    url = portal_session.get("url")
    if not isinstance(url, str) or not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe customer portal did not return a redirect URL.",
        )
    return url


def _settings_payments_return_url() -> str:
    return f"{settings.FRONTEND_HOST}/settings?tab=payments&billing_return=1"


def _ensure_user_can_use_stripe_billing(
    *, session: Session, user_id: uuid.UUID
) -> None:
    user = _get_user(session=session, user_id=user_id)
    override = get_active_access_override(session=session, user_id=user_id)
    if _get_managed_access_source(user=user, active_override=override) is not None:
        raise BillingAccessError(
            "This user is managed internally and cannot use Stripe billing."
        )


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _customer_sync_idempotency_key(task: BillingCustomerSyncTask) -> str:
    return f"billing-customer-email-sync:{task.id}:{task.desired_email}"


def _customer_sync_backoff_seconds(task: BillingCustomerSyncTask) -> int:
    schedule_index = min(
        max(task.attempt_count - 1, 0),
        len(STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS) - 1,
    )
    base_seconds = STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS[schedule_index]
    max_jitter_seconds = min(max(base_seconds // 10, 1), 60)
    digest = hashlib.sha256(f"{task.id}:{task.attempt_count}".encode()).digest()
    jitter_seconds = int.from_bytes(digest[:2], "big") % (max_jitter_seconds + 1)
    return base_seconds + jitter_seconds


def _extract_stripe_error_message(response: httpx.Response) -> str:
    try:
        payload = cast(dict[str, Any], response.json())
    except ValueError:
        return response.text or "Stripe request failed."
    error = cast(dict[str, Any] | None, payload.get("error"))
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return response.text or "Stripe request failed."


def _upsert_customer_email_sync_task(
    *,
    session: Session,
    user_id: uuid.UUID,
    stripe_customer_id: str,
    desired_email: str,
) -> BillingCustomerSyncTask:
    now = utcnow()
    status_column = cast(Any, BillingCustomerSyncTask.status)
    existing = session.exec(
        select(BillingCustomerSyncTask)
        .where(
            BillingCustomerSyncTask.user_id == user_id,
            BillingCustomerSyncTask.stripe_customer_id == stripe_customer_id,
            BillingCustomerSyncTask.sync_type == STRIPE_CUSTOMER_SYNC_TYPE,
            status_column.in_(("pending", "processing")),
        )
        .order_by(cast(Any, BillingCustomerSyncTask.created_at).desc())
    ).first()
    if existing is not None:
        existing.desired_email = desired_email
        existing.status = "pending"
        existing.attempt_count = 0
        existing.next_attempt_at = now
        existing.last_error = None
        existing.last_http_status = None
        existing.last_stripe_request_id = None
        existing.succeeded_at = None
        existing.updated_at = now
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    task = BillingCustomerSyncTask(
        user_id=user_id,
        stripe_customer_id=stripe_customer_id,
        sync_type=STRIPE_CUSTOMER_SYNC_TYPE,
        desired_email=desired_email,
        status="pending",
        next_attempt_at=now,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def _mark_customer_sync_task_succeeded(
    *,
    session: Session,
    task: BillingCustomerSyncTask,
    stripe_request_id: str | None,
) -> None:
    now = utcnow()
    task.status = "succeeded"
    task.attempt_count += 1
    task.succeeded_at = now
    task.next_attempt_at = now
    task.last_error = None
    task.last_http_status = 200
    task.last_stripe_request_id = stripe_request_id
    task.updated_at = now
    session.add(task)
    session.commit()


def _mark_customer_sync_task_pending_retry(
    *,
    session: Session,
    task: BillingCustomerSyncTask,
    error: StripeCustomerSyncError,
) -> None:
    now = utcnow()
    task.status = "pending"
    task.attempt_count += 1
    task.next_attempt_at = now + timedelta(seconds=_customer_sync_backoff_seconds(task))
    task.last_error = error.message
    task.last_http_status = error.http_status
    task.last_stripe_request_id = error.stripe_request_id
    task.updated_at = now
    session.add(task)
    session.commit()


def _mark_customer_sync_task_failed(
    *,
    session: Session,
    task: BillingCustomerSyncTask,
    error: StripeCustomerSyncError,
) -> None:
    now = utcnow()
    task.status = "failed"
    task.attempt_count += 1
    task.next_attempt_at = now
    task.last_error = error.message
    task.last_http_status = error.http_status
    task.last_stripe_request_id = error.stripe_request_id
    task.updated_at = now
    session.add(task)
    session.commit()


async def _update_stripe_customer_email(
    *,
    task: BillingCustomerSyncTask,
) -> str | None:
    try:
        response = await _stripe_request_raw(
            "POST",
            f"/v1/customers/{task.stripe_customer_id}",
            data={"email": task.desired_email},
            extra_headers={
                IDEMPOTENCY_HEADER_NAME: _customer_sync_idempotency_key(task)
            },
        )
    except HTTPException as exc:
        raise StripeCustomerSyncError(
            message=str(exc.detail),
            retryable=False,
            http_status=exc.status_code,
        ) from exc
    except httpx.TimeoutException as exc:
        raise StripeCustomerSyncError(
            message="Stripe customer email sync timed out.",
            retryable=True,
        ) from exc
    except httpx.HTTPError as exc:
        raise StripeCustomerSyncError(
            message=f"Stripe customer email sync failed: {exc}",
            retryable=True,
        ) from exc

    stripe_request_id = cast(str | None, response.headers.get("Request-Id"))
    if response.status_code >= 400:
        raise StripeCustomerSyncError(
            message=_extract_stripe_error_message(response),
            retryable=response.status_code == 429 or response.status_code >= 500,
            http_status=response.status_code,
            stripe_request_id=stripe_request_id,
        )
    return stripe_request_id


async def _attempt_customer_email_sync_task(
    *,
    session: Session,
    task: BillingCustomerSyncTask,
) -> None:
    logger.info(
        "Attempting Stripe customer email sync task_id=%s user_id=%s stripe_customer_id=%s "
        "desired_email=%s attempt=%s",
        task.id,
        task.user_id,
        task.stripe_customer_id,
        task.desired_email,
        task.attempt_count + 1,
    )
    try:
        stripe_request_id = await _update_stripe_customer_email(task=task)
    except StripeCustomerSyncError as exc:
        if exc.retryable:
            _mark_customer_sync_task_pending_retry(
                session=session, task=task, error=exc
            )
            logger.warning(
                "Stripe customer email sync retryable failure task_id=%s user_id=%s "
                "stripe_customer_id=%s desired_email=%s attempt=%s http_status=%s "
                "request_id=%s error=%s",
                task.id,
                task.user_id,
                task.stripe_customer_id,
                task.desired_email,
                task.attempt_count,
                exc.http_status,
                exc.stripe_request_id,
                exc.message,
            )
            return
        _mark_customer_sync_task_failed(session=session, task=task, error=exc)
        logger.error(
            "Stripe customer email sync terminal failure task_id=%s user_id=%s "
            "stripe_customer_id=%s desired_email=%s attempt=%s http_status=%s "
            "request_id=%s error=%s",
            task.id,
            task.user_id,
            task.stripe_customer_id,
            task.desired_email,
            task.attempt_count,
            exc.http_status,
            exc.stripe_request_id,
            exc.message,
        )
        return

    _mark_customer_sync_task_succeeded(
        session=session,
        task=task,
        stripe_request_id=stripe_request_id,
    )
    logger.info(
        "Stripe customer email sync succeeded task_id=%s user_id=%s stripe_customer_id=%s "
        "desired_email=%s attempt=%s request_id=%s",
        task.id,
        task.user_id,
        task.stripe_customer_id,
        task.desired_email,
        task.attempt_count,
        stripe_request_id,
    )


def _claim_next_customer_sync_task(
    *, session: Session
) -> BillingCustomerSyncTask | None:
    now = utcnow()
    stale_before = now - timedelta(
        seconds=settings.STRIPE_CUSTOMER_SYNC_STALE_PROCESSING_SECONDS
    )
    status_column = cast(Any, BillingCustomerSyncTask.status)
    next_attempt_at_column = cast(Any, BillingCustomerSyncTask.next_attempt_at)
    updated_at_column = cast(Any, BillingCustomerSyncTask.updated_at)
    task = session.exec(
        select(BillingCustomerSyncTask)
        .where(
            BillingCustomerSyncTask.sync_type == STRIPE_CUSTOMER_SYNC_TYPE,
            or_(
                and_(
                    status_column == "pending",
                    next_attempt_at_column <= now,
                ),
                and_(
                    status_column == "processing",
                    updated_at_column < stale_before,
                ),
            ),
        )
        .order_by(
            cast(Any, BillingCustomerSyncTask.next_attempt_at).asc(),
            cast(Any, BillingCustomerSyncTask.created_at).asc(),
        )
        .with_for_update(skip_locked=True)
    ).first()
    if task is None:
        session.rollback()
        return None
    task.status = "processing"
    task.updated_at = now
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


async def process_pending_customer_sync_tasks_async(
    *,
    session: Session,
    max_tasks: int = 10,
) -> int:
    processed = 0
    while processed < max_tasks:
        task = _claim_next_customer_sync_task(session=session)
        if task is None:
            break
        await _attempt_customer_email_sync_task(session=session, task=task)
        processed += 1
    return processed


async def queue_customer_email_sync_async(
    *,
    session: Session,
    user: Any,
    previous_email: str | None,
) -> bool:
    previous_normalized = _normalize_email(previous_email)
    current_normalized = _normalize_email(str(user.email))
    if previous_normalized == current_normalized:
        return False

    account = _get_billing_account(session=session, user_id=user.id)
    if account is None or not account.stripe_customer_id:
        return False

    _upsert_customer_email_sync_task(
        session=session,
        user_id=user.id,
        stripe_customer_id=account.stripe_customer_id,
        desired_email=str(user.email),
    )
    return True


def queue_customer_email_sync(
    *,
    session: Session,
    user: Any,
    previous_email: str | None,
) -> bool:
    return asyncio.run(
        queue_customer_email_sync_async(
            session=session,
            user=user,
            previous_email=previous_email,
        )
    )


def build_billing_summary(
    *, session: Session, user_id: uuid.UUID
) -> BillingSummaryPublic:
    snapshot = get_access_snapshot(session=session, user_id=user_id)
    return BillingSummaryPublic(
        access_profile=cast(Any, snapshot.access_profile),
        managed_access_source=cast(Any, snapshot.managed_access_source),
        billing_eligible=snapshot.billing_eligible,
        trial_eligible=snapshot.trial_eligible,
        plan_status=cast(Any, snapshot.plan_status),
        subscription_status=snapshot.subscription_status,
        latest_invoice_status=snapshot.latest_invoice_status,
        access_revoked_reason=snapshot.access_revoked_reason,
        pending_ambassador_activation=snapshot.pending_ambassador_activation,
        cancel_at=snapshot.cancel_at,
        current_period_start=snapshot.current_period_start,
        current_period_end=snapshot.current_period_end,
        renewal_day=snapshot.renewal_day,
        features=snapshot.features,
        notices=snapshot.notices,
    )


def _has_sticky_refund_revocation(subscription: BillingSubscription | None) -> bool:
    return bool(
        subscription is not None
        and subscription.access_revoked_at is not None
        and subscription.access_revoked_reason == "refunded"
        and subscription.latest_invoice_status == "refunded"
    )


def get_access_snapshot(*, session: Session, user_id: uuid.UUID) -> AccessSnapshot:
    user = _get_user(session=session, user_id=user_id)
    account = _get_billing_account(session=session, user_id=user_id)
    override = get_active_access_override(session=session, user_id=user_id)
    pending_override = get_pending_access_override(session=session, user_id=user_id)
    notices = list_billing_notice_public(session=session, user_id=user_id)
    access_profile = _resolve_access_profile(
        active_override=override,
        pending_override=pending_override,
    )
    managed_access_source = _get_managed_access_source(
        user=user,
        active_override=override,
    )
    if managed_access_source is not None:
        managed_cycle = ensure_open_managed_usage_cycle(
            session=session, user_id=user_id
        )
        return AccessSnapshot(
            access_profile=access_profile,
            managed_access_source=managed_access_source,
            billing_eligible=False,
            trial_eligible=False,
            plan_status="ambassador"
            if managed_access_source == "ambassador"
            else "none",
            subscription_status=None,
            latest_invoice_status=None,
            access_revoked_reason=None,
            pending_ambassador_activation=False,
            cancel_at=None,
            current_period_start=managed_cycle.period_start,
            current_period_end=managed_cycle.period_end,
            features=_build_cycle_feature_usage(session=session, cycle=managed_cycle),
            notices=notices,
        )

    subscription = _get_latest_billing_subscription(session=session, user_id=user_id)
    trial_eligible = not bool(account and account.has_used_trial)
    if subscription is None:
        return AccessSnapshot(
            access_profile=access_profile,
            managed_access_source=None,
            billing_eligible=pending_override is None,
            trial_eligible=trial_eligible,
            plan_status="none",
            subscription_status=None,
            latest_invoice_status=None,
            access_revoked_reason=None,
            pending_ambassador_activation=pending_override is not None,
            cancel_at=None,
            current_period_start=None,
            current_period_end=None,
            features=(
                _build_zero_feature_usage(session=session)
                if pending_override is None
                else _build_unlimited_feature_usage(session=session)
            ),
            notices=notices,
        )

    plan_status = _subscription_plan_status(subscription)
    has_sticky_refund_revocation = _has_sticky_refund_revocation(subscription)
    is_access_allowed = (
        subscription.status in STRIPE_ALLOWED_ACTIVE_STATUSES
        and subscription.access_revoked_at is None
    )
    cycle: UsageCycle | None
    if has_sticky_refund_revocation:
        cycle = None
        features = _build_blocked_feature_usage(
            session=session,
            plan_code=plan_status
            if plan_status in {TRIAL_PLAN_CODE, BASE_PLAN_CODE}
            else None,
        )
    elif is_access_allowed:
        cycle = ensure_open_usage_cycle_for_subscription(
            session=session,
            subscription=subscription,
        )
        features = _build_cycle_feature_usage(session=session, cycle=cycle)
    else:
        cycle = _get_latest_usage_cycle_for_subscription(
            session=session,
            subscription=subscription,
        )
        if cycle is not None:
            features = _build_cycle_feature_usage(session=session, cycle=cycle)
        else:
            features = _build_blocked_feature_usage(
                session=session,
                plan_code=plan_status
                if plan_status in {TRIAL_PLAN_CODE, BASE_PLAN_CODE}
                else None,
            )

    return AccessSnapshot(
        access_profile=access_profile,
        managed_access_source=None,
        billing_eligible=pending_override is None,
        trial_eligible=trial_eligible,
        plan_status=plan_status,
        subscription_status="canceled"
        if has_sticky_refund_revocation
        else subscription.status,
        latest_invoice_status=subscription.latest_invoice_status,
        access_revoked_reason=subscription.access_revoked_reason,
        pending_ambassador_activation=pending_override is not None,
        cancel_at=None
        if has_sticky_refund_revocation
        else _scheduled_cancel_at(subscription),
        current_period_start=None
        if has_sticky_refund_revocation
        else subscription.current_period_start,
        current_period_end=None
        if has_sticky_refund_revocation
        else subscription.current_period_end,
        features=features,
        notices=notices,
    )


async def set_access_profile_async(
    *,
    session: Session,
    user_id: uuid.UUID,
    access_profile: str,
    created_by_admin_id: uuid.UUID | None = None,
) -> bool:
    now = utcnow()
    active_override = get_active_access_override(session=session, user_id=user_id)
    pending_override = get_pending_access_override(session=session, user_id=user_id)
    subscription = _get_latest_billing_subscription(session=session, user_id=user_id)
    billing_changed = False

    if access_profile == "ambassador":
        if (
            subscription is not None
            and subscription.status in STRIPE_ALLOWED_ACTIVE_STATUSES
            and subscription.access_revoked_at is None
            and subscription.current_period_end is not None
        ):
            await _set_subscription_cancel_at_period_end(
                stripe_subscription_id=subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            subscription.cancel_at_period_end = True
            subscription.updated_at = now
            session.add(subscription)
            _upsert_pending_ambassador_override(
                session=session,
                user_id=user_id,
                starts_at=subscription.current_period_end,
                created_by_admin_id=created_by_admin_id,
            )
            session.commit()
            return True

        if active_override is None:
            _create_access_override(
                session=session,
                user_id=user_id,
                starts_at=now,
                created_by_admin_id=created_by_admin_id,
            )
            billing_changed = True
        else:
            active_override.revoked_at = None
            active_override.ends_at = None
            active_override.updated_at = now
            active_override.is_unlimited = True
            active_override.created_by_admin_id = created_by_admin_id
            session.add(active_override)
            billing_changed = True
        _close_open_usage_cycles(session=session, user_id=user_id)
        session.commit()
        return billing_changed

    if active_override is not None:
        active_override.revoked_at = now
        active_override.updated_at = now
        session.add(active_override)
        billing_changed = True
    if pending_override is not None:
        pending_override.revoked_at = now
        pending_override.updated_at = now
        session.add(pending_override)
        billing_changed = True
        if (
            subscription is not None
            and subscription.status in STRIPE_ALLOWED_ACTIVE_STATUSES
            and subscription.cancel_at_period_end
        ):
            await _set_subscription_cancel_at_period_end(
                stripe_subscription_id=subscription.stripe_subscription_id,
                cancel_at_period_end=False,
            )
            subscription.cancel_at_period_end = False
            subscription.updated_at = now
            session.add(subscription)
    session.commit()
    return billing_changed


def set_access_profile(
    *,
    session: Session,
    user_id: uuid.UUID,
    access_profile: str,
    created_by_admin_id: uuid.UUID | None = None,
) -> bool:
    return asyncio.run(
        set_access_profile_async(
            session=session,
            user_id=user_id,
            access_profile=access_profile,
            created_by_admin_id=created_by_admin_id,
        )
    )


def list_billing_notice_public(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> list[BillingNoticePublic]:
    now = utcnow()
    created_at_column = cast(Any, BillingNotice.created_at)
    notices = session.exec(
        select(BillingNotice)
        .where(
            BillingNotice.user_id == user_id,
            BillingNotice.status != "dismissed",
        )
        .order_by(created_at_column.desc())
    ).all()
    result: list[BillingNoticePublic] = []
    for notice in notices:
        if notice.expires_at is not None and notice.expires_at < now:
            continue
        result.append(
            BillingNoticePublic(
                id=notice.id,
                notice_type=cast(Any, notice.notice_type),
                status=cast(Any, notice.status),
                title=notice.title,
                message=notice.message,
                effective_at=notice.effective_at,
                expires_at=notice.expires_at,
                created_at=notice.created_at,
            )
        )
    return result


def mark_billing_notice_status(
    *,
    session: Session,
    user_id: uuid.UUID,
    notice_id: uuid.UUID,
    status_value: str,
) -> BillingNoticePublic:
    notice = session.get(BillingNotice, notice_id)
    if notice is None or notice.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing notice not found."
        )
    notice.status = status_value
    notice.updated_at = utcnow()
    if status_value == "read":
        notice.read_at = notice.updated_at
    if status_value == "dismissed":
        notice.dismissed_at = notice.updated_at
    session.add(notice)
    session.commit()
    session.refresh(notice)
    return BillingNoticePublic(
        id=notice.id,
        notice_type=cast(Any, notice.notice_type),
        status=cast(Any, notice.status),
        title=notice.title,
        message=notice.message,
        effective_at=notice.effective_at,
        expires_at=notice.expires_at,
        created_at=notice.created_at,
    )


def _create_access_override(
    *,
    session: Session,
    user_id: uuid.UUID,
    starts_at: datetime,
    created_by_admin_id: uuid.UUID | None,
) -> UserAccessOverride:
    override = UserAccessOverride(
        user_id=user_id,
        code=AMBASSADOR_OVERRIDE_CODE,
        is_unlimited=True,
        starts_at=starts_at,
        created_by_admin_id=created_by_admin_id,
        notes="Ambassador access",
    )
    session.add(override)
    return override


def _upsert_pending_ambassador_override(
    *,
    session: Session,
    user_id: uuid.UUID,
    starts_at: datetime,
    created_by_admin_id: uuid.UUID | None,
) -> UserAccessOverride:
    pending = get_pending_access_override(session=session, user_id=user_id)
    if pending is None:
        return _create_access_override(
            session=session,
            user_id=user_id,
            starts_at=starts_at,
            created_by_admin_id=created_by_admin_id,
        )
    pending.starts_at = starts_at
    pending.revoked_at = None
    pending.updated_at = utcnow()
    pending.created_by_admin_id = created_by_admin_id
    pending.is_unlimited = True
    session.add(pending)
    return pending


def _pending_ambassador_starts_at_for_subscription(
    *,
    subscription: BillingSubscription,
) -> datetime | None:
    if subscription.current_period_end is not None:
        return subscription.current_period_end
    if subscription.cancel_at is not None:
        return subscription.cancel_at
    if subscription.ended_at is not None:
        return subscription.ended_at
    return subscription.canceled_at


def _sync_pending_ambassador_override_for_subscription(
    *,
    session: Session,
    user_id: uuid.UUID,
    subscription: BillingSubscription,
) -> bool:
    pending_override = get_pending_access_override(session=session, user_id=user_id)
    if pending_override is None:
        return False

    starts_at = _pending_ambassador_starts_at_for_subscription(
        subscription=subscription
    )
    if starts_at is None or pending_override.starts_at == starts_at:
        return False

    pending_override.starts_at = starts_at
    pending_override.updated_at = utcnow()
    session.add(pending_override)
    return True


async def sync_superuser_billing_access_async(
    *,
    session: Session,
    user_id: uuid.UUID,
    is_superuser: bool,
) -> bool:
    if not is_superuser:
        return False

    subscription = _get_latest_billing_subscription(session=session, user_id=user_id)
    if (
        subscription is None
        or subscription.status not in STRIPE_ALLOWED_ACTIVE_STATUSES
        or subscription.access_revoked_at is not None
        or subscription.current_period_end is None
        or subscription.cancel_at_period_end
    ):
        return False

    await _set_subscription_cancel_at_period_end(
        stripe_subscription_id=subscription.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    subscription.cancel_at_period_end = True
    subscription.updated_at = utcnow()
    session.add(subscription)
    session.commit()
    return True


def ensure_user_is_billable(
    *, session: Session, user_id: uuid.UUID
) -> BillingSubscription:
    user = _get_user(session=session, user_id=user_id)
    override = get_active_access_override(session=session, user_id=user_id)
    if _get_managed_access_source(user=user, active_override=override) is not None:
        raise BillingAccessError(
            "This user is managed internally and cannot purchase plans."
        )

    subscription = _get_latest_billing_subscription(session=session, user_id=user_id)
    if (
        subscription is None
        or subscription.status not in STRIPE_ALLOWED_ACTIVE_STATUSES
        or subscription.access_revoked_at is not None
    ):
        raise BillingAccessError()
    return subscription


def build_usage_request_key(
    *,
    user_id: uuid.UUID,
    request_scope: str,
    idempotency_key: str | None,
) -> str:
    if idempotency_key and idempotency_key.strip():
        return f"{request_scope}:{user_id}:{idempotency_key.strip()}"
    return f"{request_scope}:{uuid.uuid4()}"


def reserve_feature_usage(
    *,
    session: Session,
    user_id: uuid.UUID,
    feature_code: str,
    endpoint_key: str,
    max_units_requested: int,
    request_key: str,
    job_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageReservation | None:
    if max_units_requested <= 0:
        return None

    user = _get_user(session=session, user_id=user_id)
    active_override = get_active_access_override(session=session, user_id=user_id)
    managed_access_source = _get_managed_access_source(
        user=user,
        active_override=active_override,
    )

    existing = session.exec(
        select(UsageReservation).where(UsageReservation.request_key == request_key)
    ).first()
    if existing is not None:
        return existing

    if managed_access_source is not None:
        cycle = ensure_open_managed_usage_cycle(session=session, user_id=user_id)
    else:
        subscription = ensure_user_is_billable(session=session, user_id=user_id)
        cycle = ensure_open_usage_cycle_for_subscription(
            session=session, subscription=subscription
        )

    feature_statement = select(UsageCycleFeature).where(
        UsageCycleFeature.usage_cycle_id == cycle.id,
        UsageCycleFeature.feature_code == feature_code,
    )
    feature_statement = feature_statement.with_for_update()
    cycle_feature = session.exec(feature_statement).one()
    if not cycle_feature.is_unlimited:
        remaining = (
            cycle_feature.limit_count
            - cycle_feature.used_count
            - cycle_feature.reserved_count
        )
        if remaining < max_units_requested:
            session.rollback()
            raise BillingLimitExceededError(feature_code)

    cycle_feature.reserved_count += max_units_requested
    cycle_feature.updated_at = utcnow()
    reservation = UsageReservation(
        request_key=request_key,
        user_id=user_id,
        usage_cycle_id=cycle.id,
        feature_code=feature_code,
        endpoint_key=endpoint_key,
        reserved_count=max_units_requested,
        consumed_count=0,
        status="reserved",
        job_id=job_id,
        metadata_json=metadata or {},
    )
    session.add(cycle_feature)
    session.add(reservation)
    session.commit()
    session.refresh(reservation)
    return reservation


def attach_job_id_to_reservation(
    *,
    session: Session,
    request_key: str,
    job_id: str,
) -> None:
    reservation = session.exec(
        select(UsageReservation).where(UsageReservation.request_key == request_key)
    ).first()
    if reservation is None:
        return
    reservation.job_id = job_id
    session.add(reservation)
    session.commit()


def finalize_usage_reservation(
    *,
    session: Session,
    request_key: str | None = None,
    job_id: str | None = None,
    quantity_consumed: int,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent | None:
    reservation = _get_reservation_for_update(
        session=session,
        request_key=request_key,
        job_id=job_id,
    )
    if reservation is None:
        return None
    if reservation.status in {"finalized", "released"}:
        return None

    feature = session.exec(
        select(UsageCycleFeature)
        .where(
            UsageCycleFeature.usage_cycle_id == reservation.usage_cycle_id,
            UsageCycleFeature.feature_code == reservation.feature_code,
        )
        .with_for_update()
    ).one()

    consumed = max(0, min(quantity_consumed, reservation.reserved_count))
    feature.used_count += consumed
    feature.reserved_count = max(0, feature.reserved_count - reservation.reserved_count)
    feature.updated_at = utcnow()

    reservation.consumed_count = consumed
    reservation.status = "finalized" if consumed > 0 else "released"
    reservation.finalized_at = utcnow()
    if metadata:
        reservation.metadata_json = reservation.metadata_json | metadata

    result_status = "success"
    if consumed == 0:
        result_status = "no_charge"
    elif consumed < reservation.reserved_count:
        result_status = "partial_success"

    event = UsageEvent(
        user_id=reservation.user_id,
        usage_cycle_id=reservation.usage_cycle_id,
        feature_code=reservation.feature_code,
        endpoint_key=reservation.endpoint_key,
        request_key=reservation.request_key,
        job_id=reservation.job_id,
        quantity_requested=reservation.reserved_count,
        quantity_consumed=consumed,
        result_status=result_status,
        metadata_json=metadata or reservation.metadata_json,
    )
    session.add(feature)
    session.add(reservation)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def release_usage_reservation(
    *,
    session: Session,
    request_key: str | None = None,
    job_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent | None:
    return finalize_usage_reservation(
        session=session,
        request_key=request_key,
        job_id=job_id,
        quantity_consumed=0,
        metadata=metadata,
    )


async def publish_billing_event(
    *,
    session: Session,
    user_id: uuid.UUID,
    event_name: str,
) -> None:
    try:
        summary = build_billing_summary(session=session, user_id=user_id)
        repository = get_user_events_repository()
        await repository.publish_event(
            user_id=str(user_id),
            event_name=event_name,
            envelope=UserEventEnvelope(
                topic=ACCOUNT_TOPIC,
                source=ACCOUNT_SOURCE,
                kind=ACCOUNT_KIND,
                notification_id=f"{event_name}:{user_id}:{uuid.uuid4()}",
                payload=summary.model_dump(mode="json"),
            ),
        )
    except Exception:
        logger.exception(
            "Failed to publish billing SSE event",
            extra={"user_id": str(user_id), "event_name": event_name},
        )


def verify_stripe_signature(*, payload: bytes, signature_header: str) -> None:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured.",
        )
    parts = [item.strip() for item in signature_header.split(",") if item.strip()]
    timestamp: int | None = None
    signatures: list[str] = []
    for part in parts:
        key, _, value = part.partition("=")
        if key == "t":
            timestamp = int(value)
        elif key == "v1":
            signatures.append(value)
    if timestamp is None or not signatures:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature."
        )
    if abs(int(time.time()) - timestamp) > STRIPE_SIGNATURE_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Expired Stripe signature."
        )
    signed_payload = str(timestamp).encode() + b"." + payload
    expected = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, item) for item in signatures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature."
        )


async def process_stripe_webhook(
    *,
    session: Session,
    payload: dict[str, Any],
) -> uuid.UUID | None:
    event_id = str(payload.get("id") or "").strip()
    event_type = str(payload.get("type") or "").strip()
    obj = cast(dict[str, Any], payload.get("data", {}).get("object", {}) or {})
    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe event payload.",
        )

    existing = session.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == event_id
        )
    ).first()
    if existing is not None:
        return None

    record = BillingWebhookEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        stripe_customer_id=_extract_stripe_customer_id(obj),
        stripe_subscription_id=_extract_subscription_id(obj),
        stripe_invoice_id=_extract_invoice_id(obj),
        payload_json=payload,
        processing_status="pending",
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    user_id_to_notify: uuid.UUID | None = None
    try:
        if event_type == "checkout.session.completed":
            subscription_id = _extract_subscription_id(obj)
            if subscription_id:
                subscription_data = await fetch_stripe_subscription(subscription_id)
                sync_result = sync_subscription_from_stripe_data(
                    session=session,
                    subscription_data=subscription_data,
                    event_created=_event_created_at(payload),
                )
                if sync_result.changed:
                    user_id_to_notify = sync_result.subscription.user_id
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.paused",
            "customer.subscription.resumed",
        }:
            sync_result = sync_subscription_from_stripe_data(
                session=session,
                subscription_data=obj,
                event_created=_event_created_at(payload),
            )
            if sync_result.changed:
                user_id_to_notify = sync_result.subscription.user_id
        elif event_type == "invoice.paid":
            subscription_id = _extract_subscription_id(obj)
            if subscription_id:
                subscription_data = await fetch_stripe_subscription(subscription_id)
                sync_result = sync_subscription_from_stripe_data(
                    session=session,
                    subscription_data=subscription_data,
                    event_created=_event_created_at(payload),
                    latest_invoice_id=_extract_invoice_id(obj),
                    latest_invoice_status=str(obj.get("status") or "paid"),
                )
                if sync_result.changed:
                    user_id_to_notify = sync_result.subscription.user_id
        elif event_type == "invoice.payment_failed":
            subscription_id = _extract_subscription_id(obj)
            invoice_id = _extract_invoice_id(obj)
            if not subscription_id and invoice_id:
                invoice_data = await fetch_stripe_invoice(invoice_id)
                subscription_id = _extract_subscription_id(invoice_data)
            if subscription_id:
                subscription_data = await fetch_stripe_subscription(subscription_id)
                sync_result = sync_subscription_from_stripe_data(
                    session=session,
                    subscription_data=subscription_data,
                    event_created=_event_created_at(payload),
                    latest_invoice_id=invoice_id,
                    latest_invoice_status=str(obj.get("status") or "open"),
                )
                if sync_result.changed:
                    user_id_to_notify = sync_result.subscription.user_id
            else:
                user_id_to_notify = _process_invoice_payment_failed(
                    session=session, obj=obj
                )
        elif event_type == "invoice.upcoming":
            user_id_to_notify = _process_invoice_upcoming_notice(
                session=session,
                obj=obj,
                stripe_event_id=event_id,
            )
        elif event_type == "customer.subscription.trial_will_end":
            user_id_to_notify = _process_trial_will_end_notice(
                session=session,
                obj=obj,
                stripe_event_id=event_id,
            )
        elif event_type in {
            "refund.created",
            "refund.updated",
            "refund.failed",
            # Legacy compatibility while Stripe webhook config migrates to refund.* events.
            "charge.refunded",
        }:
            user_id_to_notify = await _process_refund_event(
                session=session,
                obj=obj,
                event_type=event_type,
                stripe_event_id=event_id,
            )

        record.processing_status = "processed"
        record.processed_at = utcnow()
        session.add(record)
        session.commit()
    except Exception as exc:
        record.processing_status = "failed"
        record.processing_error = str(exc)
        record.processed_at = utcnow()
        session.add(record)
        session.commit()
        raise

    return user_id_to_notify


async def fetch_stripe_subscription(subscription_id: str) -> dict[str, Any]:
    return await _stripe_request(
        "GET",
        f"/v1/subscriptions/{subscription_id}",
        params={"expand[]": "latest_invoice"},
    )


async def fetch_stripe_invoice(invoice_id: str) -> dict[str, Any]:
    return await _stripe_request(
        "GET",
        f"/v1/invoices/{invoice_id}",
    )


async def fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
    return await _stripe_request(
        "GET",
        f"/v1/charges/{charge_id}",
        params={"expand[]": "invoice"},
    )


def sync_subscription_from_stripe_data(
    *,
    session: Session,
    subscription_data: dict[str, Any],
    event_created: datetime | None = None,
    latest_invoice_id: str | None = None,
    latest_invoice_status: str | None = None,
) -> SubscriptionSyncResult:
    stripe_subscription_id = str(subscription_data.get("id") or "").strip()
    if not stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe subscription payload is missing an id.",
        )
    stripe_customer_id = str(subscription_data.get("customer") or "").strip()
    if not stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe subscription payload is missing a customer id.",
        )

    subscription = _get_subscription_by_stripe_id(
        session=session,
        stripe_subscription_id=stripe_subscription_id,
    )
    user_id = (
        subscription.user_id
        if subscription is not None
        else _resolve_user_id_from_subscription_payload(
            session=session,
            subscription_data=subscription_data,
            stripe_customer_id=stripe_customer_id,
        )
    )

    account = _get_billing_account(session=session, user_id=user_id)
    account_was_created = account is None
    if account is None:
        account = _get_or_create_billing_account(session=session, user_id=user_id)
    account_state_before = (
        None if account_was_created else _billing_account_state(account)
    )
    subscription_state_before = (
        None if subscription is None else _billing_subscription_state(subscription)
    )

    if account.stripe_customer_id != stripe_customer_id:
        account.stripe_customer_id = stripe_customer_id
        account.updated_at = utcnow()
        session.add(account)

    if subscription is None:
        subscription = BillingSubscription(
            user_id=user_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status=str(subscription_data.get("status") or "incomplete"),
        )

    had_sticky_refund_revocation = _has_sticky_refund_revocation(subscription)
    status_value = str(subscription_data.get("status") or subscription.status)
    current_period_start, current_period_end = _extract_subscription_period_bounds(
        subscription_data
    )
    subscription.stripe_customer_id = stripe_customer_id
    subscription.stripe_price_id = _extract_price_id(subscription_data)
    subscription.plan_code = BASE_PLAN_CODE
    subscription.status = status_value
    subscription.collection_method = cast(
        str | None, subscription_data.get("collection_method")
    )
    subscription.cancel_at_period_end = bool(
        subscription_data.get("cancel_at_period_end")
    )
    subscription.cancel_at = _extract_cancel_at(subscription_data)
    subscription.cancellation_reason = _extract_cancellation_reason(subscription_data)
    subscription.current_period_start = current_period_start
    subscription.current_period_end = current_period_end
    subscription.trial_start = _timestamp_to_datetime(
        subscription_data.get("trial_start")
    )
    subscription.trial_end = _timestamp_to_datetime(subscription_data.get("trial_end"))
    paused_at = cast(dict[str, Any] | None, subscription_data.get("pause_collection"))
    subscription.paused_at = (
        utcnow()
        if status_value == "paused" and paused_at is not None
        else subscription.paused_at
    )
    subscription.canceled_at = _timestamp_to_datetime(
        subscription_data.get("canceled_at")
    )
    subscription.ended_at = _timestamp_to_datetime(subscription_data.get("ended_at"))
    if not had_sticky_refund_revocation:
        subscription.latest_invoice_id = (
            latest_invoice_id
            or _extract_latest_invoice_id(subscription_data)
            or subscription.latest_invoice_id
        )
        subscription.latest_invoice_status = (
            latest_invoice_status
            or _extract_latest_invoice_status(subscription_data)
            or subscription.latest_invoice_status
        )
    if (
        status_value in STRIPE_ALLOWED_ACTIVE_STATUSES
        and not had_sticky_refund_revocation
    ):
        subscription.access_revoked_at = None
        subscription.access_revoked_reason = None
    subscription.last_stripe_event_created = event_created
    subscription.updated_at = utcnow()
    session.add(subscription)

    if status_value == "trialing":
        account.has_used_trial = True
        account.trial_started_at = subscription.trial_start
        account.trial_ended_at = subscription.trial_end
        account.updated_at = utcnow()
        session.add(account)

    if (
        status_value in STRIPE_ALLOWED_ACTIVE_STATUSES
        and subscription.access_revoked_at is None
    ):
        ensure_open_usage_cycle_for_subscription(
            session=session, subscription=subscription
        )
    else:
        _close_open_usage_cycles(session=session, user_id=user_id)

    override_changed = _sync_pending_ambassador_override_for_subscription(
        session=session,
        user_id=user_id,
        subscription=subscription,
    )

    session.commit()
    session.refresh(subscription)
    if status_value == "paused":
        _dismiss_billing_notices(
            session=session,
            user_id=user_id,
            notice_type="trial_will_end",
            stripe_subscription_id=subscription.stripe_subscription_id,
        )
        _upsert_subscription_paused_notice(
            session=session,
            subscription=subscription,
        )
    else:
        _dismiss_billing_notices(
            session=session,
            user_id=user_id,
            notice_type="subscription_paused",
            stripe_subscription_id=subscription.stripe_subscription_id,
        )
        if status_value == "active" and subscription.access_revoked_at is None:
            _dismiss_billing_notices(
                session=session,
                user_id=user_id,
                notice_type="trial_will_end",
                stripe_subscription_id=subscription.stripe_subscription_id,
            )
    account_changed = account_was_created or (
        account_state_before is not None
        and _billing_account_state(account) != account_state_before
    )
    subscription_changed = subscription_state_before is None or (
        subscription_state_before != _billing_subscription_state(subscription)
    )
    return SubscriptionSyncResult(
        subscription=subscription,
        changed=account_changed or subscription_changed or override_changed,
    )


def ensure_open_usage_cycle_for_subscription(
    *,
    session: Session,
    subscription: BillingSubscription,
) -> UsageCycle:
    if subscription.status not in STRIPE_ALLOWED_ACTIVE_STATUSES:
        raise BillingAccessError()
    if subscription.access_revoked_at is not None:
        raise BillingAccessError(
            "Access for the current billing period has been revoked."
        )
    if subscription.current_period_start is None:
        raise BillingAccessError("Subscription period is unavailable.")

    desired_plan_code = (
        TRIAL_PLAN_CODE if subscription.status == "trialing" else BASE_PLAN_CODE
    )
    current_cycle = _get_subscription_usage_cycle(
        session=session,
        subscription=subscription,
    )
    if current_cycle is not None:
        if current_cycle.status != "open":
            current_cycle.status = "open"
            current_cycle.updated_at = utcnow()
            session.add(current_cycle)
        _ensure_cycle_feature_rows(
            session=session, usage_cycle=current_cycle, plan_code=desired_plan_code
        )
        session.commit()
        return current_cycle

    _close_open_usage_cycles(session=session, user_id=subscription.user_id)
    cycle = UsageCycle(
        user_id=subscription.user_id,
        source_type="subscription",
        source_id=subscription.id,
        plan_code=desired_plan_code,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        status="open",
    )
    session.add(cycle)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        current_cycle = _get_subscription_usage_cycle(
            session=session,
            subscription=subscription,
        )
        if current_cycle is None:
            raise
        _ensure_cycle_feature_rows(
            session=session,
            usage_cycle=current_cycle,
            plan_code=desired_plan_code,
        )
        session.commit()
        session.refresh(current_cycle)
        return current_cycle
    _ensure_cycle_feature_rows(
        session=session, usage_cycle=cycle, plan_code=desired_plan_code
    )
    session.commit()
    session.refresh(cycle)
    return cycle


def ensure_open_managed_usage_cycle(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> UsageCycle:
    period_start, period_end = _managed_cycle_period_bounds()
    current_cycle = _get_managed_usage_cycle(
        session=session,
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
    )
    if current_cycle is not None:
        if current_cycle.status != "open":
            current_cycle.status = "open"
            current_cycle.updated_at = utcnow()
            session.add(current_cycle)
        _ensure_managed_cycle_feature_rows(session=session, usage_cycle=current_cycle)
        _close_stale_managed_usage_cycles(
            session=session,
            user_id=user_id,
            current_cycle_id=current_cycle.id,
        )
        session.commit()
        return current_cycle

    cycle = UsageCycle(
        user_id=user_id,
        source_type=MANAGED_USAGE_SOURCE_TYPE,
        source_id=_managed_usage_cycle_source_id(
            user_id=user_id,
            period_start=period_start,
        ),
        plan_code=MANAGED_PLAN_CODE,
        period_start=period_start,
        period_end=period_end,
        status="open",
    )
    session.add(cycle)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        current_cycle = _get_managed_usage_cycle(
            session=session,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
        if current_cycle is None:
            raise
        _ensure_managed_cycle_feature_rows(session=session, usage_cycle=current_cycle)
        _close_stale_managed_usage_cycles(
            session=session,
            user_id=user_id,
            current_cycle_id=current_cycle.id,
        )
        session.commit()
        session.refresh(current_cycle)
        return current_cycle

    _ensure_managed_cycle_feature_rows(session=session, usage_cycle=cycle)
    _close_stale_managed_usage_cycles(
        session=session,
        user_id=user_id,
        current_cycle_id=cycle.id,
    )
    session.commit()
    session.refresh(cycle)
    return cycle


def _resolve_access_profile(
    *,
    active_override: UserAccessOverride | None,
    pending_override: UserAccessOverride | None,
) -> str:
    if active_override is not None or pending_override is not None:
        return "ambassador"
    return "standard"


def _get_managed_access_source(
    *,
    user: User | None,
    active_override: UserAccessOverride | None,
) -> str | None:
    if user is not None and user.is_superuser:
        return "admin"
    if active_override is not None:
        return "ambassador"
    return None


def _managed_cycle_period_bounds() -> tuple[datetime, datetime]:
    now = utcnow().astimezone(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    return period_start, period_end


def _managed_usage_cycle_source_id(
    *,
    user_id: uuid.UUID,
    period_start: datetime,
) -> uuid.UUID:
    return uuid.uuid5(
        MANAGED_USAGE_NAMESPACE,
        f"{user_id}:{period_start.isoformat()}",
    )


def _get_managed_usage_cycle(
    *,
    session: Session,
    user_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
) -> UsageCycle | None:
    created_at_column = cast(Any, UsageCycle.created_at)
    return session.exec(
        select(UsageCycle)
        .where(
            UsageCycle.user_id == user_id,
            UsageCycle.source_type == MANAGED_USAGE_SOURCE_TYPE,
            UsageCycle.period_start == period_start,
            UsageCycle.period_end == period_end,
        )
        .order_by(created_at_column.desc())
    ).first()


def _ensure_managed_cycle_feature_rows(
    *,
    session: Session,
    usage_cycle: UsageCycle,
) -> None:
    existing = {
        item.feature_code: item
        for item in session.exec(
            select(UsageCycleFeature).where(
                UsageCycleFeature.usage_cycle_id == usage_cycle.id
            )
        ).all()
    }
    now = utcnow()
    for feature_code in _get_feature_name_map(session=session):
        item = existing.get(feature_code)
        if item is None:
            item = UsageCycleFeature(
                usage_cycle_id=usage_cycle.id,
                feature_code=feature_code,
                limit_count=0,
                used_count=0,
                reserved_count=0,
                is_unlimited=True,
            )
        else:
            item.limit_count = 0
            item.is_unlimited = True
            item.updated_at = now
        session.add(item)


def _close_stale_managed_usage_cycles(
    *,
    session: Session,
    user_id: uuid.UUID,
    current_cycle_id: uuid.UUID,
) -> None:
    now = utcnow()
    cycles = session.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user_id,
            UsageCycle.source_type == MANAGED_USAGE_SOURCE_TYPE,
            UsageCycle.status == "open",
        )
    ).all()
    for cycle in cycles:
        if cycle.id == current_cycle_id:
            continue
        cycle.status = "closed"
        cycle.updated_at = now
        session.add(cycle)


def get_active_access_override(
    *, session: Session, user_id: uuid.UUID
) -> UserAccessOverride | None:
    now = utcnow()
    revoked_at_column = cast(Any, UserAccessOverride.revoked_at)
    created_at_column = cast(Any, UserAccessOverride.created_at)
    statement = (
        select(UserAccessOverride)
        .where(
            UserAccessOverride.user_id == user_id,
            UserAccessOverride.code == AMBASSADOR_OVERRIDE_CODE,
            revoked_at_column.is_(None),
            UserAccessOverride.starts_at <= now,
        )
        .order_by(created_at_column.desc())
    )
    candidates = session.exec(statement).all()
    for candidate in candidates:
        if candidate.ends_at is None or candidate.ends_at > now:
            return candidate
    return None


def get_pending_access_override(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> UserAccessOverride | None:
    now = utcnow()
    revoked_at_column = cast(Any, UserAccessOverride.revoked_at)
    starts_at_column = cast(Any, UserAccessOverride.starts_at)
    created_at_column = cast(Any, UserAccessOverride.created_at)
    return session.exec(
        select(UserAccessOverride)
        .where(
            UserAccessOverride.user_id == user_id,
            UserAccessOverride.code == AMBASSADOR_OVERRIDE_CODE,
            revoked_at_column.is_(None),
            UserAccessOverride.starts_at > now,
        )
        .order_by(starts_at_column.asc(), created_at_column.desc())
    ).first()


async def delete_user_billing_data(*, session: Session, user_id: uuid.UUID) -> None:
    app_models = importlib.import_module("app.models")
    UserLegalAcceptance = app_models.UserLegalAcceptance
    ig_scraper_sqlmodels = importlib.import_module(
        "kiizama_scrape_core.ig_scraper.sqlmodels"
    )
    IgScrapeJob = ig_scraper_sqlmodels.IgScrapeJob

    account = _get_billing_account(session=session, user_id=user_id)
    subscriptions = session.exec(
        select(BillingSubscription).where(BillingSubscription.user_id == user_id)
    ).all()
    if account is not None and account.stripe_customer_id:
        for subscription in subscriptions:
            if subscription.status not in {"canceled", "incomplete_expired"}:
                try:
                    await _cancel_stripe_subscription_immediately(
                        stripe_subscription_id=subscription.stripe_subscription_id
                    )
                except HTTPException:
                    logger.warning(
                        "Best-effort Stripe subscription cleanup failed during billing reset",
                        extra={
                            "user_id": str(user_id),
                            "stripe_subscription_id": subscription.stripe_subscription_id,
                        },
                        exc_info=True,
                    )
        try:
            await _delete_stripe_customer(account.stripe_customer_id)
        except HTTPException:
            logger.warning(
                "Best-effort Stripe customer cleanup failed during billing reset",
                extra={
                    "user_id": str(user_id),
                    "stripe_customer_id": account.stripe_customer_id,
                },
                exc_info=True,
            )

    reservations = session.exec(
        select(UsageReservation).where(UsageReservation.user_id == user_id)
    ).all()
    for reservation in reservations:
        session.delete(reservation)

    usage_events = session.exec(
        select(UsageEvent).where(UsageEvent.user_id == user_id)
    ).all()
    for usage_event in usage_events:
        session.delete(usage_event)

    cycles = session.exec(select(UsageCycle).where(UsageCycle.user_id == user_id)).all()
    cycle_ids = [item.id for item in cycles]
    if cycle_ids:
        usage_cycle_id_column = cast(Any, UsageCycleFeature.usage_cycle_id)
        features = session.exec(
            select(UsageCycleFeature).where(usage_cycle_id_column.in_(cycle_ids))
        ).all()
        for cycle_feature in features:
            session.delete(cycle_feature)
        # `UsageCycleFeature` has a direct FK to `UsageCycle`, but the ORM doesn't
        # know the dependency ordering here because there is no mapped relationship.
        # Flush explicitly before scheduling cycle deletes to avoid FK violations.
        session.flush()
    for cycle in cycles:
        session.delete(cycle)
    if cycles:
        session.flush()

    created_by_admin_id_column = cast(Any, UserAccessOverride.created_by_admin_id)
    overrides = session.exec(
        select(UserAccessOverride).where(UserAccessOverride.user_id == user_id)
    ).all()
    for override in overrides:
        session.delete(override)

    created_overrides = session.exec(
        select(UserAccessOverride).where(created_by_admin_id_column == user_id)
    ).all()
    for created_override in created_overrides:
        created_override.created_by_admin_id = None
        created_override.updated_at = utcnow()
        session.add(created_override)

    for subscription in subscriptions:
        session.delete(subscription)

    notices = session.exec(
        select(BillingNotice).where(BillingNotice.user_id == user_id)
    ).all()
    for notice in notices:
        session.delete(notice)

    customer_sync_tasks = session.exec(
        select(BillingCustomerSyncTask).where(
            BillingCustomerSyncTask.user_id == user_id
        )
    ).all()
    for customer_sync_task in customer_sync_tasks:
        session.delete(customer_sync_task)

    legal_acceptances = session.exec(
        select(UserLegalAcceptance).where(UserLegalAcceptance.user_id == user_id)
    ).all()
    for legal_acceptance in legal_acceptances:
        session.delete(legal_acceptance)

    ig_scrape_jobs = session.exec(
        select(IgScrapeJob).where(IgScrapeJob.owner_user_id == user_id)
    ).all()
    for ig_scrape_job in ig_scrape_jobs:
        session.delete(ig_scrape_job)

    subscription_ids = [item.stripe_subscription_id for item in subscriptions]
    webhook_events: list[BillingWebhookEvent] = []
    stripe_subscription_id_column = cast(
        Any, BillingWebhookEvent.stripe_subscription_id
    )
    if account is not None and account.stripe_customer_id:
        webhook_events = list(
            session.exec(
                select(BillingWebhookEvent).where(
                    (
                        BillingWebhookEvent.stripe_customer_id
                        == account.stripe_customer_id
                    )
                    | (stripe_subscription_id_column.in_(subscription_ids))
                )
            ).all()
        )
    elif subscription_ids:
        webhook_events = list(
            session.exec(
                select(BillingWebhookEvent).where(
                    stripe_subscription_id_column.in_(subscription_ids)
                )
            ).all()
        )
    for webhook_event in webhook_events:
        session.delete(webhook_event)

    if account is not None:
        session.delete(account)
    session.commit()


def _get_user(*, session: Session, user_id: uuid.UUID) -> User | None:
    from app.models import User

    return session.get(User, user_id)


def _get_billing_account(
    *, session: Session, user_id: uuid.UUID
) -> UserBillingAccount | None:
    return session.exec(
        select(UserBillingAccount).where(UserBillingAccount.user_id == user_id)
    ).first()


def _get_or_create_billing_account(
    *, session: Session, user_id: uuid.UUID
) -> UserBillingAccount:
    account = _get_billing_account(session=session, user_id=user_id)
    if account is None:
        account = UserBillingAccount(user_id=user_id)
        session.add(account)
        session.flush()
    return account


def _close_open_usage_cycles(*, session: Session, user_id: uuid.UUID) -> None:
    now = utcnow()
    cycles = session.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user_id, UsageCycle.status == "open"
        )
    ).all()
    for cycle in cycles:
        cycle.status = "closed"
        cycle.updated_at = now
        session.add(cycle)


def _get_subscription_usage_cycle(
    *,
    session: Session,
    subscription: BillingSubscription,
) -> UsageCycle | None:
    if subscription.id is None or subscription.current_period_start is None:
        return None
    created_at_column = cast(Any, UsageCycle.created_at)
    return session.exec(
        select(UsageCycle)
        .where(
            UsageCycle.user_id == subscription.user_id,
            UsageCycle.source_type == "subscription",
            UsageCycle.source_id == subscription.id,
            UsageCycle.period_start == subscription.current_period_start,
            UsageCycle.period_end == subscription.current_period_end,
        )
        .order_by(created_at_column.desc())
    ).first()


def _get_latest_usage_cycle_for_subscription(
    *,
    session: Session,
    subscription: BillingSubscription,
) -> UsageCycle | None:
    exact_cycle = _get_subscription_usage_cycle(
        session=session, subscription=subscription
    )
    if exact_cycle is not None:
        return exact_cycle
    if subscription.id is None:
        return None
    created_at_column = cast(Any, UsageCycle.created_at)
    return session.exec(
        select(UsageCycle)
        .where(
            UsageCycle.user_id == subscription.user_id,
            UsageCycle.source_type == "subscription",
            UsageCycle.source_id == subscription.id,
        )
        .order_by(created_at_column.desc())
    ).first()


def _get_latest_billing_subscription(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> BillingSubscription | None:
    updated_at_column = cast(Any, BillingSubscription.updated_at)
    return session.exec(
        select(BillingSubscription)
        .where(BillingSubscription.user_id == user_id)
        .order_by(updated_at_column.desc())
    ).first()


def _subscription_plan_status(subscription: BillingSubscription) -> str:
    if subscription.status == "trialing":
        return TRIAL_PLAN_CODE
    return BASE_PLAN_CODE


def _build_cycle_feature_usage(
    *,
    session: Session,
    cycle: UsageCycle,
) -> list[BillingFeatureUsagePublic]:
    feature_names = _get_feature_name_map(session=session)
    rows = session.exec(
        select(UsageCycleFeature).where(UsageCycleFeature.usage_cycle_id == cycle.id)
    ).all()
    usage_by_code = {row.feature_code: row for row in rows}
    result: list[BillingFeatureUsagePublic] = []
    for code, name in feature_names.items():
        row = usage_by_code.get(code)
        if row is None:
            result.append(
                BillingFeatureUsagePublic(
                    code=_public_feature_code(code),
                    name=name,
                    limit=0,
                    used=0,
                    reserved=0,
                    remaining=0,
                    is_unlimited=False,
                )
            )
            continue
        remaining = (
            None
            if row.is_unlimited
            else max(0, row.limit_count - row.used_count - row.reserved_count)
        )
        result.append(
            BillingFeatureUsagePublic(
                code=_public_feature_code(code),
                name=name,
                limit=None if row.is_unlimited else row.limit_count,
                used=row.used_count,
                reserved=row.reserved_count,
                remaining=remaining,
                is_unlimited=row.is_unlimited,
            )
        )
    return result


def _build_unlimited_feature_usage(
    *, session: Session
) -> list[BillingFeatureUsagePublic]:
    return [
        BillingFeatureUsagePublic(
            code=_public_feature_code(code),
            name=name,
            limit=None,
            used=0,
            reserved=0,
            remaining=None,
            is_unlimited=True,
        )
        for code, name in _get_feature_name_map(session=session).items()
    ]


def _build_zero_feature_usage(*, session: Session) -> list[BillingFeatureUsagePublic]:
    return [
        BillingFeatureUsagePublic(
            code=_public_feature_code(code),
            name=name,
            limit=0,
            used=0,
            reserved=0,
            remaining=0,
            is_unlimited=False,
        )
        for code, name in _get_feature_name_map(session=session).items()
    ]


def _build_blocked_feature_usage(
    *,
    session: Session,
    plan_code: str | None,
) -> list[BillingFeatureUsagePublic]:
    if plan_code not in {TRIAL_PLAN_CODE, BASE_PLAN_CODE}:
        return _build_zero_feature_usage(session=session)
    limits = _get_plan_limits(session=session, plan_code=plan_code)
    feature_names = _get_feature_name_map(session=session)
    return [
        BillingFeatureUsagePublic(
            code=_public_feature_code(code),
            name=feature_names[code],
            limit=limit,
            used=0,
            reserved=0,
            remaining=0,
            is_unlimited=False,
        )
        for code, limit in limits.items()
    ]


def _get_feature_name_map(*, session: Session) -> dict[str, str]:
    return {
        item.code: item.name for item in session.exec(select(LuBillingFeature)).all()
    }


def _public_feature_code(feature_code: str) -> str:
    return PUBLIC_FEATURE_CODE_ALIASES.get(feature_code, feature_code)


def _get_plan_limits(*, session: Session, plan_code: str) -> dict[str, int]:
    plan = session.exec(
        select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code)
    ).first()
    if plan is None or plan.id is None:
        return {}
    feature_id_column = cast(Any, SubscriptionPlanFeatureLimit.feature_id)
    rows = session.exec(
        select(SubscriptionPlanFeatureLimit, LuBillingFeature)
        .join(LuBillingFeature, cast(Any, LuBillingFeature.id) == feature_id_column)
        .where(SubscriptionPlanFeatureLimit.plan_id == plan.id)
    ).all()
    return {feature.code: limit.monthly_limit for limit, feature in rows}


def _ensure_cycle_feature_rows(
    *,
    session: Session,
    usage_cycle: UsageCycle,
    plan_code: str,
) -> None:
    plan = session.exec(
        select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code)
    ).first()
    if plan is None or plan.id is None:
        raise RuntimeError(f"Billing plan {plan_code!r} is not seeded.")

    existing = {
        item.feature_code: item
        for item in session.exec(
            select(UsageCycleFeature).where(
                UsageCycleFeature.usage_cycle_id == usage_cycle.id
            )
        ).all()
    }
    feature_id_column = cast(Any, SubscriptionPlanFeatureLimit.feature_id)
    rows = session.exec(
        select(SubscriptionPlanFeatureLimit, LuBillingFeature)
        .join(LuBillingFeature, cast(Any, LuBillingFeature.id) == feature_id_column)
        .where(SubscriptionPlanFeatureLimit.plan_id == plan.id)
    ).all()
    now = utcnow()
    for limit, feature in rows:
        item = existing.get(feature.code)
        if item is None:
            item = UsageCycleFeature(
                usage_cycle_id=usage_cycle.id,
                feature_code=feature.code,
                limit_count=limit.monthly_limit,
                used_count=0,
                reserved_count=0,
                is_unlimited=limit.is_unlimited,
            )
        else:
            item.limit_count = limit.monthly_limit
            item.is_unlimited = limit.is_unlimited
            item.updated_at = now
        session.add(item)


def _get_reservation_for_update(
    *,
    session: Session,
    request_key: str | None,
    job_id: str | None,
) -> UsageReservation | None:
    if request_key:
        statement = (
            select(UsageReservation)
            .where(UsageReservation.request_key == request_key)
            .with_for_update()
        )
        reservation = session.exec(statement).first()
        if reservation is not None:
            return reservation
    if job_id:
        statement = (
            select(UsageReservation)
            .where(UsageReservation.job_id == job_id)
            .with_for_update()
        )
        return session.exec(statement).first()
    return None


def _upsert_billing_notice(
    *,
    session: Session,
    user_id: uuid.UUID,
    notice_type: str,
    notice_key: str,
    stripe_event_id: str | None,
    stripe_subscription_id: str | None,
    stripe_invoice_id: str | None,
    title: str,
    message: str,
    effective_at: datetime | None,
    expires_at: datetime | None,
) -> BillingNotice:
    notice = session.exec(
        select(BillingNotice).where(BillingNotice.notice_key == notice_key)
    ).first()
    now = utcnow()
    if notice is None:
        notice = BillingNotice(
            user_id=user_id,
            notice_type=notice_type,
            status="unread",
            notice_key=notice_key,
            stripe_event_id=stripe_event_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_invoice_id=stripe_invoice_id,
            title=title,
            message=message,
            effective_at=effective_at,
            expires_at=expires_at,
        )
    elif notice.status != "dismissed":
        notice.notice_type = notice_type
        notice.stripe_event_id = stripe_event_id
        notice.stripe_subscription_id = stripe_subscription_id
        notice.stripe_invoice_id = stripe_invoice_id
        notice.title = title
        notice.message = message
        notice.effective_at = effective_at
        notice.expires_at = expires_at
        notice.updated_at = now
    session.add(notice)
    session.commit()
    session.refresh(notice)
    return notice


def _dismiss_billing_notices(
    *,
    session: Session,
    user_id: uuid.UUID,
    notice_type: str,
    stripe_subscription_id: str | None = None,
) -> None:
    now = utcnow()
    statement = select(BillingNotice).where(
        BillingNotice.user_id == user_id,
        BillingNotice.notice_type == notice_type,
        BillingNotice.status != "dismissed",
    )
    if stripe_subscription_id is not None:
        statement = statement.where(
            BillingNotice.stripe_subscription_id == stripe_subscription_id
        )
    notices = session.exec(statement).all()
    for notice in notices:
        notice.status = "dismissed"
        notice.dismissed_at = now
        notice.updated_at = now
        session.add(notice)
    if notices:
        session.commit()


def _upsert_subscription_paused_notice(
    *,
    session: Session,
    subscription: BillingSubscription,
) -> None:
    effective_at = subscription.current_period_end or subscription.updated_at
    notice_key = (
        f"subscription_paused:{subscription.user_id}:{subscription.stripe_subscription_id}:"
        f"{effective_at.isoformat() if effective_at else 'none'}"
    )
    _upsert_billing_notice(
        session=session,
        user_id=subscription.user_id,
        notice_type="subscription_paused",
        notice_key=notice_key,
        stripe_event_id=None,
        stripe_subscription_id=subscription.stripe_subscription_id,
        stripe_invoice_id=subscription.latest_invoice_id,
        title="Subscription paused",
        message=(
            "Your subscription is paused because the trial ended without a payment "
            "method. Add a payment method in billing to resume access."
        ),
        effective_at=effective_at,
        expires_at=None,
    )


def _process_invoice_upcoming_notice(
    *,
    session: Session,
    obj: dict[str, Any],
    stripe_event_id: str,
) -> uuid.UUID | None:
    subscription_id = _extract_subscription_id(obj)
    customer_id = _extract_stripe_customer_id(obj)
    subscription = None
    if subscription_id:
        subscription = _get_subscription_by_stripe_id(
            session=session, stripe_subscription_id=subscription_id
        )
    if subscription is None and customer_id:
        account = session.exec(
            select(UserBillingAccount).where(
                UserBillingAccount.stripe_customer_id == customer_id
            )
        ).first()
        if account is None:
            return None
        user_id = account.user_id
    elif subscription is not None:
        user_id = subscription.user_id
    else:
        return None

    period_end = _timestamp_to_datetime(obj.get("period_end")) or (
        subscription.current_period_end if subscription else None
    )
    notice_key = f"invoice_upcoming:{user_id}:{subscription_id or customer_id}:{period_end.isoformat() if period_end else 'none'}"
    _upsert_billing_notice(
        session=session,
        user_id=user_id,
        notice_type="invoice_upcoming",
        notice_key=notice_key,
        stripe_event_id=stripe_event_id,
        stripe_subscription_id=subscription_id,
        stripe_invoice_id=_extract_invoice_id(obj),
        title="Upcoming renewal",
        message="Your subscription is scheduled for automatic renewal soon.",
        effective_at=period_end,
        expires_at=period_end,
    )
    return user_id


def _process_trial_will_end_notice(
    *,
    session: Session,
    obj: dict[str, Any],
    stripe_event_id: str,
) -> uuid.UUID | None:
    subscription_id = _extract_subscription_id(obj)
    if not subscription_id:
        return None
    subscription = _get_subscription_by_stripe_id(
        session=session,
        stripe_subscription_id=subscription_id,
    )
    if subscription is None:
        return None
    trial_end = _timestamp_to_datetime(obj.get("trial_end")) or subscription.trial_end
    notice_key = f"trial_will_end:{subscription.user_id}:{subscription_id}:{trial_end.isoformat() if trial_end else 'none'}"
    _upsert_billing_notice(
        session=session,
        user_id=subscription.user_id,
        notice_type="trial_will_end",
        notice_key=notice_key,
        stripe_event_id=stripe_event_id,
        stripe_subscription_id=subscription_id,
        stripe_invoice_id=None,
        title="Trial ending soon",
        message="Your free trial will end soon. Add a payment method to keep access uninterrupted.",
        effective_at=trial_end,
        expires_at=trial_end,
    )
    return subscription.user_id


def _extract_subscription_id(obj: dict[str, Any]) -> str | None:
    raw = obj.get("subscription")
    if isinstance(raw, str) and raw:
        return raw
    if isinstance(raw, dict):
        subscription_id = raw.get("id")
        if isinstance(subscription_id, str) and subscription_id:
            return subscription_id
    parent = cast(dict[str, Any] | None, obj.get("parent"))
    if isinstance(parent, dict):
        subscription_details = cast(
            dict[str, Any] | None, parent.get("subscription_details")
        )
        if isinstance(subscription_details, dict):
            subscription_id = subscription_details.get("subscription")
            if isinstance(subscription_id, str) and subscription_id:
                return subscription_id
    lines = cast(dict[str, Any] | None, obj.get("lines"))
    line_items = cast(list[dict[str, Any]], (lines or {}).get("data") or [])
    for line_item in line_items:
        line_parent = cast(dict[str, Any] | None, line_item.get("parent"))
        if not isinstance(line_parent, dict):
            continue
        subscription_item_details = cast(
            dict[str, Any] | None, line_parent.get("subscription_item_details")
        )
        if not isinstance(subscription_item_details, dict):
            continue
        subscription_id = subscription_item_details.get("subscription")
        if isinstance(subscription_id, str) and subscription_id:
            return subscription_id
    if isinstance(obj.get("id"), str) and str(obj.get("object")) == "subscription":
        return cast(str, obj["id"])
    return None


def _extract_charge_id(obj: dict[str, Any]) -> str | None:
    raw = obj.get("charge")
    if isinstance(raw, str) and raw:
        return raw
    if isinstance(raw, dict):
        charge_id = raw.get("id")
        if isinstance(charge_id, str) and charge_id:
            return charge_id
    if isinstance(obj.get("id"), str) and str(obj.get("object")) == "charge":
        return cast(str, obj["id"])
    return None


def _extract_invoice_id(obj: dict[str, Any]) -> str | None:
    raw = obj.get("invoice")
    if isinstance(raw, str) and raw:
        return raw
    if isinstance(raw, dict):
        invoice_id = raw.get("id")
        if isinstance(invoice_id, str) and invoice_id:
            return invoice_id
    if isinstance(obj.get("id"), str) and str(obj.get("object")) == "invoice":
        return cast(str, obj["id"])
    charge = cast(dict[str, Any] | None, obj.get("charge"))
    if isinstance(charge, dict):
        invoice_id = charge.get("invoice")
        if isinstance(invoice_id, str) and invoice_id:
            return invoice_id
    return None


def _extract_stripe_customer_id(obj: dict[str, Any]) -> str | None:
    raw = obj.get("customer")
    if isinstance(raw, str) and raw:
        return raw
    return None


def _event_created_at(payload: dict[str, Any]) -> datetime | None:
    return _timestamp_to_datetime(payload.get("created"))


def _extract_price_id(subscription_data: dict[str, Any]) -> str | None:
    items = cast(dict[str, Any] | None, subscription_data.get("items"))
    data = cast(list[dict[str, Any]], (items or {}).get("data") or [])
    if not data:
        return None
    price = cast(dict[str, Any] | None, data[0].get("price"))
    if price is None:
        return None
    price_id = price.get("id")
    return str(price_id) if price_id else None


def _extract_subscription_period_bounds(
    subscription_data: dict[str, Any],
) -> tuple[datetime | None, datetime | None]:
    current_period_start = _timestamp_to_datetime(
        subscription_data.get("current_period_start")
    )
    current_period_end = _timestamp_to_datetime(
        subscription_data.get("current_period_end")
    )
    if current_period_start is not None or current_period_end is not None:
        return current_period_start, current_period_end

    items = cast(dict[str, Any] | None, subscription_data.get("items"))
    item_data = cast(list[dict[str, Any]], (items or {}).get("data") or [])
    item_period_starts = [
        timestamp
        for item in item_data
        if (timestamp := _timestamp_to_datetime(item.get("current_period_start")))
        is not None
    ]
    item_period_ends = [
        timestamp
        for item in item_data
        if (timestamp := _timestamp_to_datetime(item.get("current_period_end")))
        is not None
    ]
    return (
        min(item_period_starts, default=None),
        max(item_period_ends, default=None),
    )


def _extract_latest_invoice_id(subscription_data: dict[str, Any]) -> str | None:
    latest_invoice = subscription_data.get("latest_invoice")
    if isinstance(latest_invoice, str) and latest_invoice:
        return latest_invoice
    if isinstance(latest_invoice, dict):
        invoice_id = latest_invoice.get("id")
        return str(invoice_id) if invoice_id else None
    return None


def _extract_latest_invoice_status(subscription_data: dict[str, Any]) -> str | None:
    latest_invoice = subscription_data.get("latest_invoice")
    if isinstance(latest_invoice, dict):
        status_value = latest_invoice.get("status")
        return str(status_value) if status_value else None
    return None


def _extract_cancel_at(subscription_data: dict[str, Any]) -> datetime | None:
    return _timestamp_to_datetime(subscription_data.get("cancel_at"))


def _extract_cancellation_reason(subscription_data: dict[str, Any]) -> str | None:
    cancellation_details = cast(
        dict[str, Any] | None, subscription_data.get("cancellation_details")
    )
    if not cancellation_details:
        return None
    reason = cancellation_details.get("reason")
    if not isinstance(reason, str):
        return None
    reason = reason.strip()
    return reason or None


def _scheduled_cancel_at(subscription: BillingSubscription) -> datetime | None:
    if subscription.cancel_at is not None:
        return subscription.cancel_at
    if subscription.cancel_at_period_end:
        return subscription.current_period_end
    return None


def _billing_account_state(account: UserBillingAccount) -> tuple[Any, ...]:
    return (
        account.stripe_customer_id,
        account.has_used_trial,
        account.trial_started_at,
        account.trial_ended_at,
    )


def _billing_subscription_state(subscription: BillingSubscription) -> tuple[Any, ...]:
    return (
        subscription.stripe_customer_id,
        subscription.stripe_price_id,
        subscription.plan_code,
        subscription.status,
        subscription.collection_method,
        subscription.cancel_at_period_end,
        subscription.cancel_at,
        subscription.cancellation_reason,
        subscription.current_period_start,
        subscription.current_period_end,
        subscription.trial_start,
        subscription.trial_end,
        subscription.paused_at,
        subscription.canceled_at,
        subscription.ended_at,
        subscription.latest_invoice_id,
        subscription.latest_invoice_status,
        subscription.access_revoked_at,
        subscription.access_revoked_reason,
    )


def _timestamp_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value.isdigit():
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    return None


def _resolve_user_id_from_subscription_payload(
    *,
    session: Session,
    subscription_data: dict[str, Any],
    stripe_customer_id: str,
) -> uuid.UUID:
    account = session.exec(
        select(UserBillingAccount).where(
            UserBillingAccount.stripe_customer_id == stripe_customer_id
        )
    ).first()
    if account is not None:
        return account.user_id

    metadata = cast(dict[str, Any], subscription_data.get("metadata") or {})
    raw_user_id = metadata.get("user_id")
    if isinstance(raw_user_id, str):
        return uuid.UUID(raw_user_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to match Stripe subscription to a user.",
    )


def _get_subscription_by_stripe_id(
    *,
    session: Session,
    stripe_subscription_id: str,
) -> BillingSubscription | None:
    return session.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == stripe_subscription_id
        )
    ).first()


def _is_charge_fully_refunded(charge_data: dict[str, Any]) -> bool:
    is_full_refund = bool(charge_data.get("refunded"))
    if isinstance(charge_data.get("amount"), int) and isinstance(
        charge_data.get("amount_refunded"), int
    ):
        is_full_refund = charge_data["amount"] == charge_data["amount_refunded"]
    return is_full_refund


async def _resolve_refund_context(*, obj: dict[str, Any]) -> RefundContext:
    object_type = str(obj.get("object") or "")
    charge_id = _extract_charge_id(obj)
    charge_data: dict[str, Any] | None = obj if object_type == "charge" else None
    if charge_data is None and charge_id:
        charge_data = await fetch_stripe_charge(charge_id)

    invoice_id = _extract_invoice_id(obj)
    if invoice_id is None and charge_data is not None:
        invoice_id = _extract_invoice_id(charge_data)

    refund_status = None
    is_full_refund = False
    if object_type == "refund":
        status_value = str(obj.get("status") or "").strip()
        refund_status = status_value or None
        if charge_data is not None:
            is_full_refund = _is_charge_fully_refunded(charge_data)
    elif object_type == "charge":
        is_full_refund = _is_charge_fully_refunded(obj)
        refund_status = "succeeded" if is_full_refund else None

    return RefundContext(
        invoice_id=invoice_id,
        charge_id=charge_id,
        refund_status=refund_status,
        is_full_refund=is_full_refund,
    )


def _should_apply_refund_event(*, event_type: str, context: RefundContext) -> bool:
    if not context.invoice_id or not context.is_full_refund:
        return False
    if event_type == "charge.refunded":
        return True
    if event_type == "refund.failed":
        return False
    return context.refund_status == "succeeded"


def _is_refund_already_applied(
    *,
    subscription: BillingSubscription,
    invoice_id: str,
) -> bool:
    return (
        subscription.latest_invoice_id == invoice_id
        and subscription.latest_invoice_status == "refunded"
        and subscription.access_revoked_reason == "refunded"
        and subscription.access_revoked_at is not None
    )


def _process_invoice_payment_failed(
    *, session: Session, obj: dict[str, Any]
) -> uuid.UUID | None:
    subscription_id = _extract_subscription_id(obj)
    if not subscription_id:
        return None

    failed_subscription = _get_subscription_by_stripe_id(
        session=session, stripe_subscription_id=subscription_id
    )
    if failed_subscription is None:
        return None

    invoice_id = _extract_invoice_id(obj)
    invoice_status = str(obj.get("status") or "open")
    if (
        failed_subscription.latest_invoice_id == invoice_id
        and failed_subscription.latest_invoice_status == invoice_status
    ):
        return None

    failed_subscription.latest_invoice_id = invoice_id
    failed_subscription.latest_invoice_status = invoice_status
    failed_subscription.updated_at = utcnow()
    session.add(failed_subscription)
    session.commit()
    return failed_subscription.user_id


async def _process_refund_event(
    *,
    session: Session,
    obj: dict[str, Any],
    event_type: str,
    stripe_event_id: str,
) -> uuid.UUID | None:
    context = await _resolve_refund_context(obj=obj)
    if not _should_apply_refund_event(event_type=event_type, context=context):
        return None

    invoice_id = context.invoice_id
    if not invoice_id:
        return None

    subscription = session.exec(
        select(BillingSubscription).where(
            BillingSubscription.latest_invoice_id == invoice_id
        )
    ).first()
    if subscription is None:
        return None
    if _is_refund_already_applied(subscription=subscription, invoice_id=invoice_id):
        return None

    subscription.access_revoked_at = utcnow()
    subscription.access_revoked_reason = "refunded"
    subscription.latest_invoice_id = invoice_id
    subscription.latest_invoice_status = "refunded"
    subscription.updated_at = utcnow()
    session.add(subscription)

    cycles = session.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == subscription.user_id,
            UsageCycle.status == "open",
        )
    ).all()
    for cycle in cycles:
        cycle.status = "revoked"
        cycle.updated_at = utcnow()
        session.add(cycle)
    session.commit()
    _upsert_billing_notice(
        session=session,
        user_id=subscription.user_id,
        notice_type="access_revoked",
        notice_key=f"access_revoked:{subscription.user_id}:{invoice_id}",
        stripe_event_id=stripe_event_id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        stripe_invoice_id=invoice_id,
        title="Access revoked",
        message="Access for the current billing period was revoked after a refund was processed.",
        effective_at=subscription.current_period_end,
        expires_at=subscription.current_period_end,
    )
    return subscription.user_id


__all__ = [
    "AMBASSADOR_OVERRIDE_CODE",
    "BillingAccessError",
    "BillingLimitExceededError",
    "FEATURE_ENDPOINT_KEYS",
    "IDEMPOTENCY_HEADER_NAME",
    "attach_job_id_to_reservation",
    "build_usage_request_key",
    "build_billing_summary",
    "create_checkout_session",
    "create_portal_session",
    "delete_user_billing_data",
    "finalize_usage_reservation",
    "get_access_snapshot",
    "get_active_access_override",
    "get_pending_access_override",
    "list_billing_notice_public",
    "mark_billing_notice_status",
    "process_pending_customer_sync_tasks_async",
    "process_stripe_webhook",
    "publish_billing_event",
    "queue_customer_email_sync",
    "queue_customer_email_sync_async",
    "release_usage_reservation",
    "reserve_feature_usage",
    "seed_billing_catalog",
    "set_access_profile",
    "set_access_profile_async",
    "sync_superuser_billing_access_async",
    "verify_stripe_signature",
]
