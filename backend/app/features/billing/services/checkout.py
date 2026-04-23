from __future__ import annotations

import uuid
from typing import Any, cast

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings

from ..clients import stripe as stripe_client
from ..constants import STRIPE_ALLOWED_ACTIVE_STATUSES
from ..errors import BillingAccessError
from ..models import UserBillingAccount, utcnow
from ..repository import _get_billing_account, _get_or_create_billing_account
from . import access_read as access_read_service
from . import access_state as access_state_service


async def ensure_stripe_customer(
    *,
    session: Session,
    user: Any,
) -> UserBillingAccount:
    account = _get_or_create_billing_account(session=session, user_id=user.id)
    if account.stripe_customer_id:
        return account

    payload: dict[str, str] = {
        "email": user.email,
        "metadata[user_id]": str(user.id),
    }
    if user.full_name:
        payload["name"] = user.full_name

    customer = await stripe_client._stripe_request(
        "POST", "/v1/customers", data=payload
    )
    account.stripe_customer_id = str(customer["id"])
    account.updated_at = utcnow()
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def settings_payments_return_url() -> str:
    return f"{settings.FRONTEND_HOST}/settings?tab=payments&billing_return=1"


def ensure_user_can_use_stripe_billing(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> None:
    from ..repository import _get_user

    user = _get_user(session=session, user_id=user_id)
    override = access_state_service.get_active_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow,
    )
    if (
        access_state_service.get_managed_access_source(
            user=user,
            active_override=override,
        )
        is not None
    ):
        raise BillingAccessError(
            "This user is managed internally and cannot use Stripe billing."
        )


async def create_checkout_session(
    *,
    session: Session,
    user: Any,
) -> str:
    ensure_user_can_use_stripe_billing(session=session, user_id=user.id)
    if not settings.STRIPE_BASE_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe price is not configured.",
        )

    access = access_read_service.get_access_snapshot(
        session=session,
        user_id=user.id,
        utcnow_fn=utcnow,
    )
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

    account = await ensure_stripe_customer(
        session=session,
        user=user,
    )
    data: dict[str, str] = {
        "mode": "subscription",
        "customer": cast(str, account.stripe_customer_id),
        "line_items[0][price]": settings.STRIPE_BASE_PRICE_ID,
        "line_items[0][quantity]": "1",
        "success_url": settings_payments_return_url(),
        "cancel_url": settings_payments_return_url(),
        "metadata[user_id]": str(user.id),
        "subscription_data[metadata][user_id]": str(user.id),
    }
    if not account.has_used_trial:
        data["payment_method_collection"] = "if_required"
        data["subscription_data[trial_period_days]"] = str(settings.BILLING_TRIAL_DAYS)
        data[
            "subscription_data[trial_settings][end_behavior][missing_payment_method]"
        ] = "pause"

    stripe_session = await stripe_client._stripe_request(
        "POST", "/v1/checkout/sessions", data=data
    )
    url = stripe_session.get("url")
    if not isinstance(url, str) or not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe checkout session did not return a redirect URL.",
        )
    return url


async def create_portal_session(
    *,
    session: Session,
    user: Any,
) -> str:
    ensure_user_can_use_stripe_billing(session=session, user_id=user.id)
    account = _get_billing_account(session=session, user_id=user.id)
    if account is None or not account.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer is available for this user.",
        )

    portal_session = await stripe_client._stripe_request(
        "POST",
        "/v1/billing_portal/sessions",
        data={
            "customer": account.stripe_customer_id,
            "return_url": settings_payments_return_url(),
        },
    )
    url = portal_session.get("url")
    if not isinstance(url, str) or not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe customer portal did not return a redirect URL.",
        )
    return url


__all__ = [
    "create_checkout_session",
    "create_portal_session",
    "ensure_stripe_customer",
    "ensure_user_can_use_stripe_billing",
    "settings_payments_return_url",
]
