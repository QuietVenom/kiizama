from typing import Any, cast

from sqlmodel import Session, delete, select

from app.features.billing.constants import STRIPE_ALLOWED_ACTIVE_STATUSES
from app.features.billing.models import (
    BillingSubscription,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
)


def cleanup_invalid_billing_subscriptions(session: Session) -> int:
    subscription_status_column = cast(Any, BillingSubscription.status)
    subscription_id_column = cast(Any, BillingSubscription.id)
    subscription_current_period_start_column = cast(
        Any, BillingSubscription.current_period_start
    )
    subscription_access_revoked_at_column = cast(
        Any, BillingSubscription.access_revoked_at
    )
    cycle_id_column = cast(Any, UsageCycle.id)
    cycle_source_id_column = cast(Any, UsageCycle.source_id)
    cycle_feature_cycle_id_column = cast(Any, UsageCycleFeature.usage_cycle_id)
    reservation_cycle_id_column = cast(Any, UsageReservation.usage_cycle_id)
    event_cycle_id_column = cast(Any, UsageEvent.usage_cycle_id)
    bad_subscription_ids = list(
        session.exec(
            select(BillingSubscription.id).where(
                subscription_status_column.in_(STRIPE_ALLOWED_ACTIVE_STATUSES),
                subscription_current_period_start_column.is_(None),
                subscription_access_revoked_at_column.is_(None),
            )
        ).all()
    )
    if not bad_subscription_ids:
        return 0

    bad_cycle_ids = list(
        session.exec(
            select(UsageCycle.id).where(
                UsageCycle.source_type == "subscription",
                cycle_source_id_column.in_(bad_subscription_ids),
            )
        ).all()
    )
    if bad_cycle_ids:
        session.execute(
            delete(UsageEvent).where(event_cycle_id_column.in_(bad_cycle_ids))
        )
        session.execute(
            delete(UsageReservation).where(
                reservation_cycle_id_column.in_(bad_cycle_ids)
            )
        )
        session.execute(
            delete(UsageCycleFeature).where(
                cycle_feature_cycle_id_column.in_(bad_cycle_ids)
            )
        )
        session.execute(delete(UsageCycle).where(cycle_id_column.in_(bad_cycle_ids)))

    session.execute(
        delete(BillingSubscription).where(
            subscription_id_column.in_(bad_subscription_ids)
        )
    )
    session.commit()
    return len(bad_subscription_ids)
