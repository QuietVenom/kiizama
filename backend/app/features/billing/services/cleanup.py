from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

import httpx
from fastapi import HTTPException
from sqlmodel import Session

from ..clients.stripe import (
    cancel_stripe_subscription_immediately,
    delete_stripe_customer,
)
from ..models import BillingSubscription
from ..repository import (
    build_user_billing_cleanup_context,
    delete_user_billing_cleanup_context,
)

logger = logging.getLogger(__name__)


async def cleanup_remote_billing_state(
    *,
    user_id: uuid.UUID,
    account_stripe_customer_id: str | None,
    subscriptions: Sequence[BillingSubscription],
) -> None:
    if not account_stripe_customer_id:
        return

    for subscription in subscriptions:
        status_value = str(getattr(subscription, "status", ""))
        if status_value in {"canceled", "incomplete_expired"}:
            continue
        try:
            await cancel_stripe_subscription_immediately(
                stripe_subscription_id=subscription.stripe_subscription_id
            )
        except (HTTPException, httpx.TimeoutException, httpx.HTTPError):
            logger.warning(
                "Best-effort Stripe subscription cleanup failed during billing reset",
                extra={
                    "user_id": str(user_id),
                    "stripe_subscription_id": subscription.stripe_subscription_id,
                },
                exc_info=True,
            )

    try:
        await delete_stripe_customer(account_stripe_customer_id)
    except (HTTPException, httpx.TimeoutException, httpx.HTTPError):
        logger.warning(
            "Best-effort Stripe customer cleanup failed during billing reset",
            extra={
                "user_id": str(user_id),
                "stripe_customer_id": account_stripe_customer_id,
            },
            exc_info=True,
        )


async def delete_user_billing_state(*, session: Session, user_id: uuid.UUID) -> None:
    context = build_user_billing_cleanup_context(
        session=session,
        user_id=user_id,
    )
    await cleanup_remote_billing_state(
        user_id=user_id,
        account_stripe_customer_id=(
            context.account.stripe_customer_id if context.account is not None else None
        ),
        subscriptions=context.subscriptions,
    )
    delete_user_billing_cleanup_context(session=session, context=context)


__all__ = ["delete_user_billing_state"]
