from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.errors import BillingAccessError
from app.features.billing.models import (
    BillingSubscription,
    UsageCycle,
    UsageCycleFeature,
    UserAccessOverride,
)
from app.features.billing.services import cycle_lifecycle as cycle_lifecycle_service
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def test_ensure_open_usage_cycle_for_subscription_creates_trial_cycle_feature_rows(
    db: Session,
) -> None:
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="trialing",
        current_period_start=now,
        current_period_end=now + timedelta(days=7),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    cycle = cycle_lifecycle_service.ensure_open_usage_cycle_for_subscription(
        session=db,
        subscription=subscription,
        utcnow_fn=lambda: now,
    )
    cycle_features = db.exec(
        select(UsageCycleFeature).where(UsageCycleFeature.usage_cycle_id == cycle.id)
    ).all()

    assert cycle.plan_code == "trial"
    assert cycle.status == "open"
    assert cycle_features


def test_ensure_open_managed_usage_cycle_rolls_month_and_closes_stale_cycle(
    db: Session,
) -> None:
    user = _create_user(db=db)
    april_now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    may_now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)

    april_cycle = cycle_lifecycle_service.ensure_open_managed_usage_cycle(
        session=db,
        user_id=user.id,
        utcnow_fn=lambda: april_now,
    )
    may_cycle = cycle_lifecycle_service.ensure_open_managed_usage_cycle(
        session=db,
        user_id=user.id,
        utcnow_fn=lambda: may_now,
    )
    all_cycles = db.exec(
        select(UsageCycle)
        .where(UsageCycle.user_id == user.id)
        .order_by(UsageCycle.period_start)
    ).all()

    assert april_cycle.id != may_cycle.id
    assert all_cycles[0].status == "closed"
    assert all_cycles[1].status == "open"
    assert all_cycles[1].period_start == datetime(2026, 5, 1, 0, 0, tzinfo=UTC)


def test_ensure_user_is_billable_managed_user_raises_access_error(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    db.add(
        UserAccessOverride(
            user_id=user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=now - timedelta(days=1),
            notes="Ambassador access",
        )
    )
    db.commit()

    # Act / Assert
    with pytest.raises(BillingAccessError, match="managed internally"):
        cycle_lifecycle_service.ensure_user_is_billable(
            session=db,
            user_id=user.id,
            utcnow_fn=lambda: now,
        )


def test_ensure_user_is_billable_without_active_subscription_raises_access_error(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)

    # Act / Assert
    with pytest.raises(BillingAccessError):
        cycle_lifecycle_service.ensure_user_is_billable(
            session=db,
            user_id=user.id,
            utcnow_fn=lambda: datetime(2026, 4, 17, 12, 0, tzinfo=UTC),
        )


def test_ensure_open_usage_cycle_for_subscription_inactive_or_revoked_or_missing_period_raises(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    subscriptions = [
        BillingSubscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_inactive_{user.id}",
            stripe_customer_id=f"cus_{user.id}",
            status="canceled",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        ),
        BillingSubscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_revoked_{user.id}",
            stripe_customer_id=f"cus_{user.id}",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            access_revoked_at=now,
        ),
        BillingSubscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_missing_period_{user.id}",
            stripe_customer_id=f"cus_{user.id}",
            status="active",
            current_period_start=None,
            current_period_end=now + timedelta(days=30),
        ),
    ]
    db.add_all(subscriptions)
    db.commit()

    # Act / Assert
    for subscription in subscriptions:
        with pytest.raises(BillingAccessError):
            cycle_lifecycle_service.ensure_open_usage_cycle_for_subscription(
                session=db,
                subscription=subscription,
                utcnow_fn=lambda: now,
            )


def test_ensure_open_usage_cycle_for_subscription_reopens_existing_closed_cycle(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_closed_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    cycle = UsageCycle(
        user_id=user.id,
        source_type="subscription",
        source_id=subscription.id,
        plan_code="base",
        period_start=now,
        period_end=now + timedelta(days=30),
        status="closed",
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    # Act
    reopened = cycle_lifecycle_service.ensure_open_usage_cycle_for_subscription(
        session=db,
        subscription=subscription,
        utcnow_fn=lambda: now + timedelta(minutes=5),
    )

    # Assert
    assert reopened.id == cycle.id
    assert reopened.status == "open"
    assert db.exec(select(UsageCycle).where(UsageCycle.user_id == user.id)).all() == [
        reopened
    ]


def test_managed_cycle_period_bounds_december_calculates_january_period() -> None:
    # Arrange
    now = datetime(2026, 12, 15, 18, 30, tzinfo=UTC)

    # Act
    period_start, period_end = cycle_lifecycle_service.managed_cycle_period_bounds(
        utcnow_fn=lambda: now,
    )

    # Assert
    assert period_start == datetime(2026, 12, 1, 0, 0, tzinfo=UTC)
    assert period_end == datetime(2027, 1, 1, 0, 0, tzinfo=UTC)


def test_ensure_open_managed_usage_cycle_existing_closed_cycle_reopens_and_closes_stale(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 6, 17, 12, 0, tzinfo=UTC)
    period_start, period_end = cycle_lifecycle_service.managed_cycle_period_bounds(
        utcnow_fn=lambda: now,
    )
    stale_cycle = UsageCycle(
        user_id=user.id,
        source_type="managed",
        source_id=cycle_lifecycle_service.managed_usage_cycle_source_id(
            user_id=user.id,
            period_start=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        ),
        plan_code="managed",
        period_start=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        period_end=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
        status="open",
    )
    closed_current_cycle = UsageCycle(
        user_id=user.id,
        source_type="managed",
        source_id=cycle_lifecycle_service.managed_usage_cycle_source_id(
            user_id=user.id,
            period_start=period_start,
        ),
        plan_code="managed",
        period_start=period_start,
        period_end=period_end,
        status="closed",
    )
    db.add(stale_cycle)
    db.add(closed_current_cycle)
    db.commit()

    # Act
    cycle = cycle_lifecycle_service.ensure_open_managed_usage_cycle(
        session=db,
        user_id=user.id,
        utcnow_fn=lambda: now,
    )

    # Assert
    db.refresh(stale_cycle)
    assert cycle.id == closed_current_cycle.id
    assert cycle.status == "open"
    assert stale_cycle.status == "closed"


def test_get_latest_usage_cycle_for_subscription_falls_back_to_latest_source_cycle(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_fallback_{user.id}",
        stripe_customer_id=f"cus_fallback_{user.id}",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    fallback_cycle = UsageCycle(
        user_id=user.id,
        source_type="subscription",
        source_id=subscription.id,
        plan_code="base",
        period_start=now - timedelta(days=30),
        period_end=now,
        status="closed",
    )
    db.add(fallback_cycle)
    db.commit()
    db.refresh(fallback_cycle)

    # Act
    result = cycle_lifecycle_service.get_latest_usage_cycle_for_subscription(
        session=db,
        subscription=subscription,
    )

    # Assert
    assert result is not None
    assert result.id == fallback_cycle.id


def test_get_subscription_usage_cycle_unsaved_or_missing_period_returns_none(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    unsaved_subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_unsaved_{user.id}",
        stripe_customer_id=f"cus_unsaved_{user.id}",
        status="active",
        current_period_start=None,
        current_period_end=None,
    )

    # Act / Assert
    assert (
        cycle_lifecycle_service.get_subscription_usage_cycle(
            session=db,
            subscription=unsaved_subscription,
        )
        is None
    )
