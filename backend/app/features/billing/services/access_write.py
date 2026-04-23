from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

from sqlmodel import Session

from ..clients import stripe as stripe_client
from ..constants import AMBASSADOR_OVERRIDE_CODE, STRIPE_ALLOWED_ACTIVE_STATUSES
from ..models import BillingSubscription, UserAccessOverride, utcnow
from . import access_state
from . import cycle_lifecycle as cycle_lifecycle_service

UtcNowCallable = Callable[[], datetime]


async def set_access_profile_async(
    *,
    session: Session,
    user_id: uuid.UUID,
    access_profile: str,
    created_by_admin_id: uuid.UUID | None = None,
    utcnow_fn: UtcNowCallable = utcnow,
) -> bool:
    now = utcnow_fn()
    active_override = access_state.get_active_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    pending_override = access_state.get_pending_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    subscription = cycle_lifecycle_service.get_latest_billing_subscription(
        session=session,
        user_id=user_id,
    )
    billing_changed = False

    if access_profile == "ambassador":
        if (
            subscription is not None
            and subscription.status in STRIPE_ALLOWED_ACTIVE_STATUSES
            and subscription.access_revoked_at is None
            and subscription.current_period_end is not None
        ):
            await stripe_client.set_subscription_cancel_at_period_end(
                stripe_subscription_id=subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            subscription.cancel_at_period_end = True
            subscription.updated_at = now
            session.add(subscription)
            upsert_pending_ambassador_override(
                session=session,
                user_id=user_id,
                starts_at=subscription.current_period_end,
                created_by_admin_id=created_by_admin_id,
                utcnow_fn=utcnow_fn,
            )
            session.commit()
            return True

        if active_override is None:
            create_access_override(
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
        cycle_lifecycle_service.close_open_usage_cycles(
            session=session,
            user_id=user_id,
            utcnow_fn=utcnow_fn,
        )
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
            await stripe_client.set_subscription_cancel_at_period_end(
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
    set_access_profile_async_fn: Callable[..., Coroutine[Any, Any, bool]],
) -> bool:
    return asyncio.run(
        set_access_profile_async_fn(
            session=session,
            user_id=user_id,
            access_profile=access_profile,
            created_by_admin_id=created_by_admin_id,
        )
    )


async def sync_superuser_billing_access_async(
    *,
    session: Session,
    user_id: uuid.UUID,
    is_superuser: bool,
    utcnow_fn: UtcNowCallable = utcnow,
) -> bool:
    if not is_superuser:
        return False

    subscription = cycle_lifecycle_service.get_latest_billing_subscription(
        session=session,
        user_id=user_id,
    )
    if (
        subscription is None
        or subscription.status not in STRIPE_ALLOWED_ACTIVE_STATUSES
        or subscription.access_revoked_at is not None
        or subscription.current_period_end is None
        or subscription.cancel_at_period_end
    ):
        return False

    await stripe_client.set_subscription_cancel_at_period_end(
        stripe_subscription_id=subscription.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    subscription.cancel_at_period_end = True
    subscription.updated_at = utcnow_fn()
    session.add(subscription)
    session.commit()
    return True


def sync_pending_ambassador_override_for_subscription(
    *,
    session: Session,
    user_id: uuid.UUID,
    subscription: BillingSubscription,
    utcnow_fn: UtcNowCallable = utcnow,
) -> bool:
    pending_override = access_state.get_pending_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    if pending_override is None:
        return False

    starts_at = pending_ambassador_starts_at_for_subscription(subscription=subscription)
    if starts_at is None or pending_override.starts_at == starts_at:
        return False

    pending_override.starts_at = starts_at
    pending_override.updated_at = utcnow_fn()
    session.add(pending_override)
    return True


def create_access_override(
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


def upsert_pending_ambassador_override(
    *,
    session: Session,
    user_id: uuid.UUID,
    starts_at: datetime,
    created_by_admin_id: uuid.UUID | None,
    utcnow_fn: UtcNowCallable = utcnow,
) -> UserAccessOverride:
    pending = access_state.get_pending_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    if pending is None:
        return create_access_override(
            session=session,
            user_id=user_id,
            starts_at=starts_at,
            created_by_admin_id=created_by_admin_id,
        )
    pending.starts_at = starts_at
    pending.revoked_at = None
    pending.updated_at = utcnow_fn()
    pending.created_by_admin_id = created_by_admin_id
    pending.is_unlimited = True
    session.add(pending)
    return pending


def pending_ambassador_starts_at_for_subscription(
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


__all__ = [
    "set_access_profile",
    "set_access_profile_async",
    "sync_pending_ambassador_override_for_subscription",
    "sync_superuser_billing_access_async",
]
