"""Stable billing facade.

Public consumers should import from `app.features.billing` or this module.
Internal feature logic lives under `app.features.billing.services`.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlmodel import Session

from .clients.stripe import verify_stripe_signature
from .constants import (
    AMBASSADOR_OVERRIDE_CODE,
    FEATURE_ENDPOINT_KEYS,
    IDEMPOTENCY_HEADER_NAME,
)
from .errors import BillingAccessError, BillingLimitExceededError
from .models import UsageEvent, UsageReservation
from .schemas import BillingNoticePublic, BillingSummaryPublic
from .services import access_read as access_read_service
from .services import access_write as access_write_service
from .services import catalog as catalog_service
from .services import checkout as checkout_service
from .services import customer_sync as customer_sync_service
from .services import events as events_service
from .services import notices as notices_service
from .services import usage as usage_service
from .services import webhooks as webhooks_service


def seed_billing_catalog(*, session: Session) -> None:
    catalog_service.seed_billing_catalog(session=session)


async def create_checkout_session(*, session: Session, user: Any) -> str:
    return await checkout_service.create_checkout_session(session=session, user=user)


async def create_portal_session(*, session: Session, user: Any) -> str:
    return await checkout_service.create_portal_session(session=session, user=user)


async def process_pending_customer_sync_tasks_async(
    *,
    session: Session,
    max_tasks: int = 10,
) -> int:
    return await customer_sync_service.process_pending_customer_sync_tasks_async(
        session=session, max_tasks=max_tasks
    )


async def queue_customer_email_sync_async(
    *,
    session: Session,
    user: Any,
    previous_email: str | None,
) -> bool:
    return await customer_sync_service.queue_customer_email_sync_async(
        session=session,
        user=user,
        previous_email=previous_email,
    )


def queue_customer_email_sync(
    *,
    session: Session,
    user: Any,
    previous_email: str | None,
) -> bool:
    return customer_sync_service.queue_customer_email_sync(
        session=session,
        user=user,
        previous_email=previous_email,
    )


def build_billing_summary(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> BillingSummaryPublic:
    return access_read_service.build_billing_summary(session=session, user_id=user_id)


async def set_access_profile_async(
    *,
    session: Session,
    user_id: uuid.UUID,
    access_profile: str,
    created_by_admin_id: uuid.UUID | None = None,
) -> bool:
    return await access_write_service.set_access_profile_async(
        session=session,
        user_id=user_id,
        access_profile=access_profile,
        created_by_admin_id=created_by_admin_id,
    )


def set_access_profile(
    *,
    session: Session,
    user_id: uuid.UUID,
    access_profile: str,
    created_by_admin_id: uuid.UUID | None = None,
) -> bool:
    return access_write_service.set_access_profile(
        session=session,
        user_id=user_id,
        access_profile=access_profile,
        created_by_admin_id=created_by_admin_id,
        set_access_profile_async_fn=set_access_profile_async,
    )


def list_billing_notice_public(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> list[BillingNoticePublic]:
    return notices_service.list_billing_notice_public(session=session, user_id=user_id)


def mark_billing_notice_status(
    *,
    session: Session,
    user_id: uuid.UUID,
    notice_id: uuid.UUID,
    status_value: str,
) -> BillingNoticePublic:
    return notices_service.mark_billing_notice_status(
        session=session,
        user_id=user_id,
        notice_id=notice_id,
        status_value=status_value,
    )


async def sync_superuser_billing_access_async(
    *,
    session: Session,
    user_id: uuid.UUID,
    is_superuser: bool,
) -> bool:
    return await access_write_service.sync_superuser_billing_access_async(
        session=session,
        user_id=user_id,
        is_superuser=is_superuser,
    )


def build_usage_request_key(
    *,
    user_id: uuid.UUID,
    request_scope: str,
    idempotency_key: str | None,
) -> str:
    return usage_service.build_usage_request_key(
        user_id=user_id,
        request_scope=request_scope,
        idempotency_key=idempotency_key,
    )


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
    return usage_service.reserve_feature_usage(
        session=session,
        user_id=user_id,
        feature_code=feature_code,
        endpoint_key=endpoint_key,
        max_units_requested=max_units_requested,
        request_key=request_key,
        job_id=job_id,
        metadata=metadata,
    )


def attach_job_id_to_reservation(
    *,
    session: Session,
    request_key: str,
    job_id: str,
) -> None:
    usage_service.attach_job_id_to_reservation(
        session=session,
        request_key=request_key,
        job_id=job_id,
    )


def finalize_usage_reservation(
    *,
    session: Session,
    request_key: str | None = None,
    job_id: str | None = None,
    quantity_consumed: int,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent | None:
    return usage_service.finalize_usage_reservation(
        session=session,
        request_key=request_key,
        job_id=job_id,
        quantity_consumed=quantity_consumed,
        metadata=metadata,
    )


def release_usage_reservation(
    *,
    session: Session,
    request_key: str | None = None,
    job_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent | None:
    return usage_service.release_usage_reservation(
        session=session,
        request_key=request_key,
        job_id=job_id,
        metadata=metadata,
    )


async def publish_billing_event(
    *,
    session: Session,
    user_id: uuid.UUID,
    event_name: str,
) -> None:
    await events_service.publish_billing_event(
        session=session, user_id=user_id, event_name=event_name
    )


async def process_stripe_webhook(
    *,
    session: Session,
    payload: dict[str, Any],
) -> uuid.UUID | None:
    return await webhooks_service.process_stripe_webhook(
        session=session, payload=payload
    )


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
    "finalize_usage_reservation",
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
