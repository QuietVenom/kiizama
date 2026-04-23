from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from fastapi import HTTPException, status
from sqlmodel import Session, select

from ..models import BillingNotice, BillingSubscription, utcnow
from ..schemas import BillingNoticePublic

UtcNowCallable = Callable[[], datetime]


def list_billing_notice_public(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> list[BillingNoticePublic]:
    now = utcnow_fn()
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
    utcnow_fn: UtcNowCallable = utcnow,
) -> BillingNoticePublic:
    notice = session.get(BillingNotice, notice_id)
    if notice is None or notice.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing notice not found.",
        )
    notice.status = status_value
    notice.updated_at = utcnow_fn()
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


def upsert_billing_notice(
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
    utcnow_fn: UtcNowCallable = utcnow,
) -> BillingNotice:
    notice = session.exec(
        select(BillingNotice).where(BillingNotice.notice_key == notice_key)
    ).first()
    now = utcnow_fn()
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


def dismiss_billing_notices(
    *,
    session: Session,
    user_id: uuid.UUID,
    notice_type: str,
    stripe_subscription_id: str | None = None,
    utcnow_fn: UtcNowCallable = utcnow,
) -> None:
    now = utcnow_fn()
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


def upsert_subscription_paused_notice(
    *,
    session: Session,
    subscription: BillingSubscription,
    utcnow_fn: UtcNowCallable = utcnow,
) -> None:
    effective_at = subscription.current_period_end or subscription.updated_at
    notice_key = (
        f"subscription_paused:{subscription.user_id}:{subscription.stripe_subscription_id}:"
        f"{effective_at.isoformat() if effective_at else 'none'}"
    )
    upsert_billing_notice(
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
        utcnow_fn=utcnow_fn,
    )


__all__ = [
    "dismiss_billing_notices",
    "list_billing_notice_public",
    "mark_billing_notice_status",
    "upsert_billing_notice",
    "upsert_subscription_paused_notice",
]
