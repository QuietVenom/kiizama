from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from fastapi import HTTPException, status
from sqlmodel import Session, select

from ..clients import stripe as stripe_client
from ..models import (
    BillingSubscription,
    BillingWebhookEvent,
    UsageCycle,
    UserBillingAccount,
    utcnow,
)
from ..schemas import RefundContext
from . import notices as notices_service
from . import subscriptions as subscriptions_service

UtcNowCallable = Callable[[], datetime]


async def process_stripe_webhook(
    *,
    session: Session,
    payload: dict[str, Any],
    utcnow_fn: UtcNowCallable = utcnow,
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
    if existing is not None and existing.processing_status != "failed":
        return None

    if existing is None:
        record = BillingWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            stripe_customer_id=subscriptions_service._extract_stripe_customer_id(obj),
            stripe_subscription_id=subscriptions_service._extract_subscription_id(obj),
            stripe_invoice_id=subscriptions_service._extract_invoice_id(obj),
            payload_json=payload,
            processing_status="pending",
        )
    else:
        record = existing
        record.event_type = event_type
        record.stripe_customer_id = subscriptions_service._extract_stripe_customer_id(
            obj
        )
        record.stripe_subscription_id = subscriptions_service._extract_subscription_id(
            obj
        )
        record.stripe_invoice_id = subscriptions_service._extract_invoice_id(obj)
        record.payload_json = payload
        record.processing_status = "pending"
        record.processing_error = None
        record.processed_at = None

    session.add(record)
    session.commit()
    session.refresh(record)

    user_id_to_notify: uuid.UUID | None = None
    try:
        if event_type == "checkout.session.completed":
            subscription_id = subscriptions_service._extract_subscription_id(obj)
            if subscription_id:
                subscription_data = await stripe_client.fetch_stripe_subscription(
                    subscription_id
                )
                sync_result = subscriptions_service.sync_subscription_from_stripe_data(
                    session=session,
                    subscription_data=subscription_data,
                    event_created=subscriptions_service._event_created_at(payload),
                    utcnow_fn=utcnow_fn,
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
            sync_result = subscriptions_service.sync_subscription_from_stripe_data(
                session=session,
                subscription_data=obj,
                event_created=subscriptions_service._event_created_at(payload),
                utcnow_fn=utcnow_fn,
            )
            if sync_result.changed:
                user_id_to_notify = sync_result.subscription.user_id
        elif event_type == "invoice.paid":
            subscription_id = subscriptions_service._extract_subscription_id(obj)
            if subscription_id:
                subscription_data = await stripe_client.fetch_stripe_subscription(
                    subscription_id
                )
                sync_result = subscriptions_service.sync_subscription_from_stripe_data(
                    session=session,
                    subscription_data=subscription_data,
                    event_created=subscriptions_service._event_created_at(payload),
                    latest_invoice_id=subscriptions_service._extract_invoice_id(obj),
                    latest_invoice_status=str(obj.get("status") or "paid"),
                    utcnow_fn=utcnow_fn,
                )
                if sync_result.changed:
                    user_id_to_notify = sync_result.subscription.user_id
        elif event_type == "invoice.payment_failed":
            subscription_id = subscriptions_service._extract_subscription_id(obj)
            invoice_id = subscriptions_service._extract_invoice_id(obj)
            if not subscription_id and invoice_id:
                invoice_data = await stripe_client.fetch_stripe_invoice(invoice_id)
                subscription_id = subscriptions_service._extract_subscription_id(
                    invoice_data
                )
            if subscription_id:
                subscription_data = await stripe_client.fetch_stripe_subscription(
                    subscription_id
                )
                sync_result = subscriptions_service.sync_subscription_from_stripe_data(
                    session=session,
                    subscription_data=subscription_data,
                    event_created=subscriptions_service._event_created_at(payload),
                    latest_invoice_id=invoice_id,
                    latest_invoice_status=str(obj.get("status") or "open"),
                    utcnow_fn=utcnow_fn,
                )
                if sync_result.changed:
                    user_id_to_notify = sync_result.subscription.user_id
            else:
                user_id_to_notify = _process_invoice_payment_failed(
                    session=session,
                    obj=obj,
                    utcnow_fn=utcnow_fn,
                )
        elif event_type == "invoice.upcoming":
            user_id_to_notify = _process_invoice_upcoming_notice(
                session=session,
                obj=obj,
                stripe_event_id=event_id,
                utcnow_fn=utcnow_fn,
            )
        elif event_type == "customer.subscription.trial_will_end":
            user_id_to_notify = _process_trial_will_end_notice(
                session=session,
                obj=obj,
                stripe_event_id=event_id,
                utcnow_fn=utcnow_fn,
            )
        elif event_type in {
            "refund.created",
            "refund.updated",
            "refund.failed",
            "charge.refunded",
        }:
            user_id_to_notify = await _process_refund_event(
                session=session,
                obj=obj,
                event_type=event_type,
                stripe_event_id=event_id,
                utcnow_fn=utcnow_fn,
            )

        record.processing_status = "processed"
        record.processed_at = utcnow_fn()
        session.add(record)
        session.commit()
    except Exception as exc:
        record.processing_status = "failed"
        record.processing_error = str(exc)
        record.processed_at = utcnow_fn()
        session.add(record)
        session.commit()
        raise

    return user_id_to_notify


def _process_invoice_upcoming_notice(
    *,
    session: Session,
    obj: dict[str, Any],
    stripe_event_id: str,
    utcnow_fn: UtcNowCallable = utcnow,
) -> uuid.UUID | None:
    subscription_id = subscriptions_service._extract_subscription_id(obj)
    customer_id = subscriptions_service._extract_stripe_customer_id(obj)
    subscription = None
    if subscription_id:
        subscription = subscriptions_service._get_subscription_by_stripe_id(
            session=session,
            stripe_subscription_id=subscription_id,
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

    period_end = subscriptions_service._timestamp_to_datetime(
        obj.get("period_end")
    ) or (subscription.current_period_end if subscription else None)
    notice_key = (
        f"invoice_upcoming:{user_id}:{subscription_id or customer_id}:"
        f"{period_end.isoformat() if period_end else 'none'}"
    )
    notices_service.upsert_billing_notice(
        session=session,
        user_id=user_id,
        notice_type="invoice_upcoming",
        notice_key=notice_key,
        stripe_event_id=stripe_event_id,
        stripe_subscription_id=subscription_id,
        stripe_invoice_id=subscriptions_service._extract_invoice_id(obj),
        title="Upcoming renewal",
        message="Your subscription is scheduled for automatic renewal soon.",
        effective_at=period_end,
        expires_at=period_end,
        utcnow_fn=utcnow_fn,
    )
    return user_id


def _process_trial_will_end_notice(
    *,
    session: Session,
    obj: dict[str, Any],
    stripe_event_id: str,
    utcnow_fn: UtcNowCallable = utcnow,
) -> uuid.UUID | None:
    subscription_id = subscriptions_service._extract_subscription_id(obj)
    if not subscription_id:
        return None
    subscription = subscriptions_service._get_subscription_by_stripe_id(
        session=session,
        stripe_subscription_id=subscription_id,
    )
    if subscription is None:
        return None
    trial_end = (
        subscriptions_service._timestamp_to_datetime(obj.get("trial_end"))
        or subscription.trial_end
    )
    notice_key = (
        f"trial_will_end:{subscription.user_id}:{subscription_id}:"
        f"{trial_end.isoformat() if trial_end else 'none'}"
    )
    notices_service.upsert_billing_notice(
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
        utcnow_fn=utcnow_fn,
    )
    return subscription.user_id


def _is_charge_fully_refunded(charge_data: dict[str, Any]) -> bool:
    is_full_refund = bool(charge_data.get("refunded"))
    if isinstance(charge_data.get("amount"), int) and isinstance(
        charge_data.get("amount_refunded"), int
    ):
        is_full_refund = charge_data["amount"] == charge_data["amount_refunded"]
    return is_full_refund


async def _resolve_refund_context(
    *,
    obj: dict[str, Any],
) -> RefundContext:
    object_type = str(obj.get("object") or "")
    charge_id = subscriptions_service._extract_charge_id(obj)
    charge_data: dict[str, Any] | None = obj if object_type == "charge" else None
    if charge_data is None and charge_id:
        charge_data = await stripe_client.fetch_stripe_charge(charge_id)

    invoice_id = subscriptions_service._extract_invoice_id(obj)
    if invoice_id is None and charge_data is not None:
        invoice_id = subscriptions_service._extract_invoice_id(charge_data)

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
    *,
    session: Session,
    obj: dict[str, Any],
    utcnow_fn: UtcNowCallable = utcnow,
) -> uuid.UUID | None:
    subscription_id = subscriptions_service._extract_subscription_id(obj)
    if not subscription_id:
        return None

    failed_subscription = subscriptions_service._get_subscription_by_stripe_id(
        session=session,
        stripe_subscription_id=subscription_id,
    )
    if failed_subscription is None:
        return None

    invoice_id = subscriptions_service._extract_invoice_id(obj)
    invoice_status = str(obj.get("status") or "open")
    if (
        failed_subscription.latest_invoice_id == invoice_id
        and failed_subscription.latest_invoice_status == invoice_status
    ):
        return None

    failed_subscription.latest_invoice_id = invoice_id
    failed_subscription.latest_invoice_status = invoice_status
    failed_subscription.updated_at = utcnow_fn()
    session.add(failed_subscription)
    session.commit()
    return failed_subscription.user_id


async def _process_refund_event(
    *,
    session: Session,
    obj: dict[str, Any],
    event_type: str,
    stripe_event_id: str,
    utcnow_fn: UtcNowCallable = utcnow,
) -> uuid.UUID | None:
    context = await _resolve_refund_context(
        obj=obj,
    )
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

    now = utcnow_fn()
    subscription.access_revoked_at = now
    subscription.access_revoked_reason = "refunded"
    subscription.latest_invoice_id = invoice_id
    subscription.latest_invoice_status = "refunded"
    subscription.updated_at = now
    session.add(subscription)

    cycles = session.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == subscription.user_id,
            UsageCycle.status == "open",
        )
    ).all()
    for cycle in cycles:
        cycle.status = "revoked"
        cycle.updated_at = now
        session.add(cycle)
    session.commit()
    notices_service.upsert_billing_notice(
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
        utcnow_fn=utcnow_fn,
    )
    return subscription.user_id


__all__ = ["process_stripe_webhook"]
