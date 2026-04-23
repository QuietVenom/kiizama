from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import HTTPException, status
from sqlmodel import Session, select

from ..constants import BASE_PLAN_CODE, STRIPE_ALLOWED_ACTIVE_STATUSES
from ..models import BillingSubscription, UserBillingAccount, utcnow
from ..repository import _get_billing_account, _get_or_create_billing_account
from ..schemas import SubscriptionSyncResult
from . import access_state as access_state_service
from . import access_write as access_write_service
from . import cycle_lifecycle as cycle_lifecycle_service
from . import notices as notices_service

UtcNowCallable = Callable[[], datetime]


def sync_subscription_from_stripe_data(
    *,
    session: Session,
    subscription_data: dict[str, Any],
    event_created: datetime | None = None,
    latest_invoice_id: str | None = None,
    latest_invoice_status: str | None = None,
    utcnow_fn: UtcNowCallable = utcnow,
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
        account.updated_at = utcnow_fn()
        session.add(account)

    if subscription is None:
        subscription = BillingSubscription(
            user_id=user_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status=str(subscription_data.get("status") or "incomplete"),
        )

    had_sticky_refund = access_state_service.has_sticky_refund_revocation(subscription)
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
        utcnow_fn()
        if status_value == "paused" and paused_at is not None
        else subscription.paused_at
    )
    subscription.canceled_at = _timestamp_to_datetime(
        subscription_data.get("canceled_at")
    )
    subscription.ended_at = _timestamp_to_datetime(subscription_data.get("ended_at"))
    if not had_sticky_refund:
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
    if status_value in STRIPE_ALLOWED_ACTIVE_STATUSES and not had_sticky_refund:
        subscription.access_revoked_at = None
        subscription.access_revoked_reason = None
    subscription.last_stripe_event_created = event_created
    subscription.updated_at = utcnow_fn()
    session.add(subscription)

    if status_value == "trialing":
        account.has_used_trial = True
        account.trial_started_at = subscription.trial_start
        account.trial_ended_at = subscription.trial_end
        account.updated_at = utcnow_fn()
        session.add(account)

    if (
        status_value in STRIPE_ALLOWED_ACTIVE_STATUSES
        and subscription.access_revoked_at is None
    ):
        cycle_lifecycle_service.ensure_open_usage_cycle_for_subscription(
            session=session,
            subscription=subscription,
            utcnow_fn=utcnow_fn,
        )
    else:
        cycle_lifecycle_service.close_open_usage_cycles(
            session=session,
            user_id=user_id,
            utcnow_fn=utcnow_fn,
        )

    override_changed = (
        access_write_service.sync_pending_ambassador_override_for_subscription(
            session=session,
            user_id=user_id,
            subscription=subscription,
            utcnow_fn=utcnow_fn,
        )
    )

    session.commit()
    session.refresh(subscription)
    if status_value == "paused":
        notices_service.dismiss_billing_notices(
            session=session,
            user_id=user_id,
            notice_type="trial_will_end",
            stripe_subscription_id=subscription.stripe_subscription_id,
            utcnow_fn=utcnow_fn,
        )
        notices_service.upsert_subscription_paused_notice(
            session=session,
            subscription=subscription,
            utcnow_fn=utcnow_fn,
        )
    else:
        notices_service.dismiss_billing_notices(
            session=session,
            user_id=user_id,
            notice_type="subscription_paused",
            stripe_subscription_id=subscription.stripe_subscription_id,
            utcnow_fn=utcnow_fn,
        )
        if status_value == "active" and subscription.access_revoked_at is None:
            notices_service.dismiss_billing_notices(
                session=session,
                user_id=user_id,
                notice_type="trial_will_end",
                stripe_subscription_id=subscription.stripe_subscription_id,
                utcnow_fn=utcnow_fn,
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
        return value.astimezone(UTC)
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str) and value.isdigit():
        return datetime.fromtimestamp(int(value), tz=UTC)
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


__all__ = ["sync_subscription_from_stripe_data"]
