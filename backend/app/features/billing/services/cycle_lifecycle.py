from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..constants import (
    BASE_PLAN_CODE,
    MANAGED_PLAN_CODE,
    MANAGED_USAGE_NAMESPACE,
    MANAGED_USAGE_SOURCE_TYPE,
    STRIPE_ALLOWED_ACTIVE_STATUSES,
    TRIAL_PLAN_CODE,
)
from ..errors import BillingAccessError
from ..models import BillingSubscription, UsageCycle, utcnow
from ..repository import _get_user
from . import access_state, cycle_features

UtcNowCallable = Callable[[], datetime]


def ensure_user_is_billable(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> BillingSubscription:
    user = _get_user(session=session, user_id=user_id)
    override = access_state.get_active_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    if (
        access_state.get_managed_access_source(
            user=user,
            active_override=override,
        )
        is not None
    ):
        raise BillingAccessError(
            "This user is managed internally and cannot purchase plans."
        )

    subscription = get_latest_billing_subscription(session=session, user_id=user_id)
    if (
        subscription is None
        or subscription.status not in STRIPE_ALLOWED_ACTIVE_STATUSES
        or subscription.access_revoked_at is not None
    ):
        raise BillingAccessError()
    return subscription


def ensure_open_usage_cycle_for_subscription(
    *,
    session: Session,
    subscription: BillingSubscription,
    utcnow_fn: UtcNowCallable = utcnow,
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
    current_cycle = get_subscription_usage_cycle(
        session=session,
        subscription=subscription,
    )
    if current_cycle is not None:
        if current_cycle.status != "open":
            current_cycle.status = "open"
            current_cycle.updated_at = utcnow_fn()
            session.add(current_cycle)
        cycle_features.ensure_cycle_feature_rows(
            session=session,
            usage_cycle=current_cycle,
            plan_code=desired_plan_code,
            utcnow_fn=utcnow_fn,
        )
        session.commit()
        return current_cycle

    close_open_usage_cycles(
        session=session,
        user_id=subscription.user_id,
        utcnow_fn=utcnow_fn,
    )
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
        current_cycle = get_subscription_usage_cycle(
            session=session,
            subscription=subscription,
        )
        if current_cycle is None:
            raise
        cycle_features.ensure_cycle_feature_rows(
            session=session,
            usage_cycle=current_cycle,
            plan_code=desired_plan_code,
            utcnow_fn=utcnow_fn,
        )
        session.commit()
        session.refresh(current_cycle)
        return current_cycle

    cycle_features.ensure_cycle_feature_rows(
        session=session,
        usage_cycle=cycle,
        plan_code=desired_plan_code,
        utcnow_fn=utcnow_fn,
    )
    session.commit()
    session.refresh(cycle)
    return cycle


def ensure_open_managed_usage_cycle(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> UsageCycle:
    period_start, period_end = managed_cycle_period_bounds(utcnow_fn=utcnow_fn)
    current_cycle = get_managed_usage_cycle(
        session=session,
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
    )
    if current_cycle is not None:
        if current_cycle.status != "open":
            current_cycle.status = "open"
            current_cycle.updated_at = utcnow_fn()
            session.add(current_cycle)
        cycle_features.ensure_managed_cycle_feature_rows(
            session=session,
            usage_cycle=current_cycle,
            utcnow_fn=utcnow_fn,
        )
        close_stale_managed_usage_cycles(
            session=session,
            user_id=user_id,
            current_cycle_id=current_cycle.id,
            utcnow_fn=utcnow_fn,
        )
        session.commit()
        return current_cycle

    cycle = UsageCycle(
        user_id=user_id,
        source_type=MANAGED_USAGE_SOURCE_TYPE,
        source_id=managed_usage_cycle_source_id(
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
        current_cycle = get_managed_usage_cycle(
            session=session,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
        if current_cycle is None:
            raise
        cycle_features.ensure_managed_cycle_feature_rows(
            session=session,
            usage_cycle=current_cycle,
            utcnow_fn=utcnow_fn,
        )
        close_stale_managed_usage_cycles(
            session=session,
            user_id=user_id,
            current_cycle_id=current_cycle.id,
            utcnow_fn=utcnow_fn,
        )
        session.commit()
        session.refresh(current_cycle)
        return current_cycle

    cycle_features.ensure_managed_cycle_feature_rows(
        session=session,
        usage_cycle=cycle,
        utcnow_fn=utcnow_fn,
    )
    close_stale_managed_usage_cycles(
        session=session,
        user_id=user_id,
        current_cycle_id=cycle.id,
        utcnow_fn=utcnow_fn,
    )
    session.commit()
    session.refresh(cycle)
    return cycle


def close_open_usage_cycles(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> None:
    now = utcnow_fn()
    cycles = session.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user_id,
            UsageCycle.status == "open",
        )
    ).all()
    for cycle in cycles:
        cycle.status = "closed"
        cycle.updated_at = now
        session.add(cycle)


def get_latest_billing_subscription(
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


def get_latest_usage_cycle_for_subscription(
    *,
    session: Session,
    subscription: BillingSubscription,
) -> UsageCycle | None:
    exact_cycle = get_subscription_usage_cycle(
        session=session,
        subscription=subscription,
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


def get_subscription_usage_cycle(
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


def managed_cycle_period_bounds(
    *,
    utcnow_fn: UtcNowCallable = utcnow,
) -> tuple[datetime, datetime]:
    now = utcnow_fn().astimezone(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    return period_start, period_end


def managed_usage_cycle_source_id(
    *,
    user_id: uuid.UUID,
    period_start: datetime,
) -> uuid.UUID:
    return uuid.uuid5(
        MANAGED_USAGE_NAMESPACE,
        f"{user_id}:{period_start.isoformat()}",
    )


def get_managed_usage_cycle(
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


def close_stale_managed_usage_cycles(
    *,
    session: Session,
    user_id: uuid.UUID,
    current_cycle_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> None:
    now = utcnow_fn()
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


__all__ = [
    "close_open_usage_cycles",
    "ensure_open_managed_usage_cycle",
    "ensure_open_usage_cycle_for_subscription",
    "ensure_user_is_billable",
    "get_latest_billing_subscription",
    "get_latest_usage_cycle_for_subscription",
    "get_managed_usage_cycle",
    "get_subscription_usage_cycle",
    "managed_cycle_period_bounds",
    "managed_usage_cycle_source_id",
]
