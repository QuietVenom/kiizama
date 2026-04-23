from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import timedelta
from typing import Any, cast

import httpx
from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlmodel import Session, select

from app.core.config import settings

from ..clients import stripe as stripe_client
from ..constants import (
    IDEMPOTENCY_HEADER_NAME,
    STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS,
    STRIPE_CUSTOMER_SYNC_TYPE,
)
from ..models import BillingCustomerSyncTask, utcnow
from ..repository import _get_billing_account
from ..schemas import StripeCustomerSyncError

logger = logging.getLogger(__name__)


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def customer_sync_idempotency_key(task: BillingCustomerSyncTask) -> str:
    return f"billing-customer-email-sync:{task.id}:{task.desired_email}"


def customer_sync_backoff_seconds(task: BillingCustomerSyncTask) -> int:
    schedule_index = min(
        max(task.attempt_count - 1, 0),
        len(STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS) - 1,
    )
    base_seconds = STRIPE_CUSTOMER_SYNC_RETRY_SCHEDULE_SECONDS[schedule_index]
    max_jitter_seconds = min(max(base_seconds // 10, 1), 60)
    digest = hashlib.sha256(f"{task.id}:{task.attempt_count}".encode()).digest()
    jitter_seconds = int.from_bytes(digest[:2], "big") % (max_jitter_seconds + 1)
    return base_seconds + jitter_seconds


def upsert_customer_email_sync_task(
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


def mark_customer_sync_task_succeeded(
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


def mark_customer_sync_task_pending_retry(
    *,
    session: Session,
    task: BillingCustomerSyncTask,
    error: StripeCustomerSyncError,
) -> None:
    now = utcnow()
    task.status = "pending"
    task.attempt_count += 1
    task.next_attempt_at = now + timedelta(seconds=customer_sync_backoff_seconds(task))
    task.last_error = error.message
    task.last_http_status = error.http_status
    task.last_stripe_request_id = error.stripe_request_id
    task.updated_at = now
    session.add(task)
    session.commit()


def mark_customer_sync_task_failed(
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


async def update_stripe_customer_email(
    *,
    task: BillingCustomerSyncTask,
) -> str | None:
    try:
        response = await stripe_client._stripe_request_raw(
            "POST",
            f"/v1/customers/{task.stripe_customer_id}",
            data={"email": task.desired_email},
            extra_headers={
                IDEMPOTENCY_HEADER_NAME: customer_sync_idempotency_key(task)
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
            message=stripe_client._extract_stripe_error_message(response),
            retryable=response.status_code == 429 or response.status_code >= 500,
            http_status=response.status_code,
            stripe_request_id=stripe_request_id,
        )
    return stripe_request_id


async def attempt_customer_email_sync_task(
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
        stripe_request_id = await update_stripe_customer_email(
            task=task,
        )
    except StripeCustomerSyncError as exc:
        if exc.retryable:
            mark_customer_sync_task_pending_retry(session=session, task=task, error=exc)
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
        mark_customer_sync_task_failed(session=session, task=task, error=exc)
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

    mark_customer_sync_task_succeeded(
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


def claim_next_customer_sync_task(
    *,
    session: Session,
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
        task = claim_next_customer_sync_task(session=session)
        if task is None:
            break
        await attempt_customer_email_sync_task(
            session=session,
            task=task,
        )
        processed += 1
    return processed


async def queue_customer_email_sync_async(
    *,
    session: Session,
    user: Any,
    previous_email: str | None,
) -> bool:
    previous_normalized = normalize_email(previous_email)
    current_normalized = normalize_email(str(user.email))
    if previous_normalized == current_normalized:
        return False

    account = _get_billing_account(session=session, user_id=user.id)
    if account is None or not account.stripe_customer_id:
        return False

    upsert_customer_email_sync_task(
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


__all__ = [
    "attempt_customer_email_sync_task",
    "claim_next_customer_sync_task",
    "customer_sync_backoff_seconds",
    "customer_sync_idempotency_key",
    "mark_customer_sync_task_failed",
    "mark_customer_sync_task_pending_retry",
    "mark_customer_sync_task_succeeded",
    "normalize_email",
    "process_pending_customer_sync_tasks_async",
    "queue_customer_email_sync",
    "queue_customer_email_sync_async",
    "update_stripe_customer_email",
    "upsert_customer_email_sync_task",
]
