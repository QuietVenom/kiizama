from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from sqlmodel import Session, select

from .models import (
    BillingCustomerSyncTask,
    BillingNotice,
    BillingSubscription,
    BillingWebhookEvent,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
    UserAccessOverride,
    UserBillingAccount,
    utcnow,
)

if TYPE_CHECKING:
    from app.models import User


@dataclass(slots=True)
class BillingCleanupContext:
    account: UserBillingAccount | None
    subscriptions: list[BillingSubscription]
    reservations: list[UsageReservation]
    usage_events: list[UsageEvent]
    cycles: list[UsageCycle]
    cycle_features: list[UsageCycleFeature]
    overrides: list[UserAccessOverride]
    created_overrides: list[UserAccessOverride]
    notices: list[BillingNotice]
    customer_sync_tasks: list[BillingCustomerSyncTask]
    webhook_events: list[BillingWebhookEvent]


def _get_user(*, session: Session, user_id: uuid.UUID) -> User | None:
    from app.models import User

    return session.get(User, user_id)


def _get_billing_account(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> UserBillingAccount | None:
    return session.exec(
        select(UserBillingAccount).where(UserBillingAccount.user_id == user_id)
    ).first()


def _get_or_create_billing_account(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> UserBillingAccount:
    account = _get_billing_account(session=session, user_id=user_id)
    if account is None:
        account = UserBillingAccount(user_id=user_id)
        session.add(account)
        session.flush()
    return account


def build_user_billing_cleanup_context(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> BillingCleanupContext:
    account = _get_billing_account(session=session, user_id=user_id)
    subscriptions = list(
        session.exec(
            select(BillingSubscription).where(BillingSubscription.user_id == user_id)
        ).all()
    )
    reservations = list(
        session.exec(
            select(UsageReservation).where(UsageReservation.user_id == user_id)
        ).all()
    )
    usage_events = list(
        session.exec(select(UsageEvent).where(UsageEvent.user_id == user_id)).all()
    )
    cycles = list(
        session.exec(select(UsageCycle).where(UsageCycle.user_id == user_id)).all()
    )
    cycle_ids = [item.id for item in cycles]
    cycle_features: list[UsageCycleFeature] = []
    if cycle_ids:
        usage_cycle_id_column = cast(Any, UsageCycleFeature.usage_cycle_id)
        cycle_features = list(
            session.exec(
                select(UsageCycleFeature).where(usage_cycle_id_column.in_(cycle_ids))
            ).all()
        )

    created_by_admin_id_column = cast(Any, UserAccessOverride.created_by_admin_id)
    overrides = list(
        session.exec(
            select(UserAccessOverride).where(UserAccessOverride.user_id == user_id)
        ).all()
    )
    created_overrides = list(
        session.exec(
            select(UserAccessOverride).where(created_by_admin_id_column == user_id)
        ).all()
    )
    notices = list(
        session.exec(
            select(BillingNotice).where(BillingNotice.user_id == user_id)
        ).all()
    )
    customer_sync_tasks = list(
        session.exec(
            select(BillingCustomerSyncTask).where(
                BillingCustomerSyncTask.user_id == user_id
            )
        ).all()
    )

    subscription_ids = [item.stripe_subscription_id for item in subscriptions]
    stripe_subscription_id_column = cast(
        Any, BillingWebhookEvent.stripe_subscription_id
    )
    webhook_events: list[BillingWebhookEvent] = []
    if account is not None and account.stripe_customer_id:
        webhook_events = list(
            session.exec(
                select(BillingWebhookEvent).where(
                    (
                        BillingWebhookEvent.stripe_customer_id
                        == account.stripe_customer_id
                    )
                    | (stripe_subscription_id_column.in_(subscription_ids))
                )
            ).all()
        )
    elif subscription_ids:
        webhook_events = list(
            session.exec(
                select(BillingWebhookEvent).where(
                    stripe_subscription_id_column.in_(subscription_ids)
                )
            ).all()
        )

    return BillingCleanupContext(
        account=account,
        subscriptions=subscriptions,
        reservations=reservations,
        usage_events=usage_events,
        cycles=cycles,
        cycle_features=cycle_features,
        overrides=overrides,
        created_overrides=created_overrides,
        notices=notices,
        customer_sync_tasks=customer_sync_tasks,
        webhook_events=webhook_events,
    )


def delete_user_billing_cleanup_context(
    *, session: Session, context: BillingCleanupContext
) -> None:
    for reservation in context.reservations:
        session.delete(reservation)

    for usage_event in context.usage_events:
        session.delete(usage_event)

    if context.cycle_features:
        for cycle_feature in context.cycle_features:
            session.delete(cycle_feature)
        # `UsageCycleFeature` has a direct FK to `UsageCycle`, but the ORM doesn't
        # know the dependency ordering here because there is no mapped relationship.
        # Flush explicitly before scheduling cycle deletes to avoid FK violations.
        session.flush()
    for cycle in context.cycles:
        session.delete(cycle)
    if context.cycles:
        session.flush()

    for override in context.overrides:
        session.delete(override)

    for created_override in context.created_overrides:
        created_override.created_by_admin_id = None
        created_override.updated_at = utcnow()
        session.add(created_override)

    for subscription in context.subscriptions:
        session.delete(subscription)

    for notice in context.notices:
        session.delete(notice)

    for customer_sync_task in context.customer_sync_tasks:
        session.delete(customer_sync_task)

    for webhook_event in context.webhook_events:
        session.delete(webhook_event)

    if context.account is not None:
        session.delete(context.account)


__all__ = [
    "BillingCleanupContext",
    "_get_billing_account",
    "_get_or_create_billing_account",
    "_get_user",
    "build_user_billing_cleanup_context",
    "delete_user_billing_cleanup_context",
]
