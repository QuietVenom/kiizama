from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from sqlmodel import Session

from ..constants import BASE_PLAN_CODE, STRIPE_ALLOWED_ACTIVE_STATUSES, TRIAL_PLAN_CODE
from ..models import BillingSubscription, utcnow
from ..repository import _get_billing_account, _get_user
from ..schemas import AccessSnapshot, BillingSummaryPublic
from . import access_state
from . import cycle_features as cycle_features_service
from . import cycle_lifecycle as cycle_lifecycle_service
from . import notices as notices_service

UtcNowCallable = Callable[[], datetime]


def build_billing_summary(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> BillingSummaryPublic:
    snapshot = get_access_snapshot(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
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


def get_access_snapshot(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> AccessSnapshot:
    user = _get_user(session=session, user_id=user_id)
    account = _get_billing_account(session=session, user_id=user_id)
    override = access_state.get_active_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    pending_override = access_state.get_pending_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    notices = notices_service.list_billing_notice_public(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    access_profile = access_state.resolve_access_profile(
        active_override=override,
        pending_override=pending_override,
    )
    managed_access_source = access_state.get_managed_access_source(
        user=user,
        active_override=override,
    )
    if managed_access_source is not None:
        managed_cycle = cycle_lifecycle_service.ensure_open_managed_usage_cycle(
            session=session,
            user_id=user_id,
            utcnow_fn=utcnow_fn,
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
            features=cycle_features_service.build_cycle_feature_usage(
                session=session,
                cycle=managed_cycle,
            ),
            notices=notices,
        )

    subscription = cycle_lifecycle_service.get_latest_billing_subscription(
        session=session,
        user_id=user_id,
    )
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
                cycle_features_service.build_zero_feature_usage(session=session)
                if pending_override is None
                else cycle_features_service.build_unlimited_feature_usage(
                    session=session
                )
            ),
            notices=notices,
        )

    plan_status = _subscription_plan_status(subscription.status)
    sticky_refund = access_state.has_sticky_refund_revocation(subscription)
    is_access_allowed = (
        subscription.status in STRIPE_ALLOWED_ACTIVE_STATUSES
        and subscription.access_revoked_at is None
    )
    cycle = None
    if sticky_refund:
        features = cycle_features_service.build_blocked_feature_usage(
            session=session,
            plan_code=plan_status,
        )
    elif is_access_allowed:
        cycle = cycle_lifecycle_service.ensure_open_usage_cycle_for_subscription(
            session=session,
            subscription=subscription,
            utcnow_fn=utcnow_fn,
        )
        features = cycle_features_service.build_cycle_feature_usage(
            session=session, cycle=cycle
        )
    else:
        cycle = cycle_lifecycle_service.get_latest_usage_cycle_for_subscription(
            session=session,
            subscription=subscription,
        )
        if cycle is not None:
            features = cycle_features_service.build_cycle_feature_usage(
                session=session,
                cycle=cycle,
            )
        else:
            features = cycle_features_service.build_blocked_feature_usage(
                session=session,
                plan_code=plan_status,
            )

    return AccessSnapshot(
        access_profile=access_profile,
        managed_access_source=None,
        billing_eligible=pending_override is None,
        trial_eligible=trial_eligible,
        plan_status=plan_status,
        subscription_status="canceled" if sticky_refund else subscription.status,
        latest_invoice_status=subscription.latest_invoice_status,
        access_revoked_reason=subscription.access_revoked_reason,
        pending_ambassador_activation=pending_override is not None,
        cancel_at=None if sticky_refund else _scheduled_cancel_at(subscription),
        current_period_start=None
        if sticky_refund
        else subscription.current_period_start,
        current_period_end=None if sticky_refund else subscription.current_period_end,
        features=features,
        notices=notices,
    )


def _subscription_plan_status(status_value: str) -> str:
    if status_value == "trialing":
        return TRIAL_PLAN_CODE
    return BASE_PLAN_CODE


def _scheduled_cancel_at(subscription: BillingSubscription) -> datetime | None:
    if subscription.cancel_at is not None:
        return subscription.cancel_at
    if subscription.cancel_at_period_end:
        return subscription.current_period_end
    return None


__all__ = [
    "build_billing_summary",
    "get_access_snapshot",
]
