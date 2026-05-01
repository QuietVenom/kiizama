import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.clients import stripe as stripe_client
from app.features.billing.models import BillingSubscription, UserAccessOverride
from app.features.billing.services import access_write as access_write_service
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def _create_active_subscription(*, db: Session, user_id):
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    subscription = BillingSubscription(
        user_id=user_id,
        stripe_subscription_id=f"sub_{user_id}",
        stripe_customer_id=f"cus_{user_id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=now - timedelta(days=1),
        current_period_end=now + timedelta(days=29),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def test_set_access_profile_async_schedules_pending_override_for_active_subscription(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    subscription = _create_active_subscription(db=db, user_id=user.id)
    cancel_calls: list[bool] = []

    async def fake_set_subscription_cancel_at_period_end(
        *,
        stripe_subscription_id: str,
        cancel_at_period_end: bool,
    ) -> None:
        assert stripe_subscription_id == subscription.stripe_subscription_id
        cancel_calls.append(cancel_at_period_end)

    monkeypatch.setattr(
        stripe_client,
        "set_subscription_cancel_at_period_end",
        fake_set_subscription_cancel_at_period_end,
    )

    changed = asyncio.run(
        access_write_service.set_access_profile_async(
            session=db,
            user_id=user.id,
            access_profile="ambassador",
            utcnow_fn=lambda: datetime(2026, 4, 20, 18, 0, tzinfo=UTC),
        )
    )

    db.refresh(subscription)
    pending_override = db.exec(
        select(UserAccessOverride).where(UserAccessOverride.user_id == user.id)
    ).one()

    assert changed is True
    assert cancel_calls == [True]
    assert subscription.cancel_at_period_end is True
    assert pending_override.starts_at == subscription.current_period_end


def test_set_access_profile_async_base_clears_pending_override_and_reverts_cancellation(
    db: Session,
    monkeypatch,
) -> None:
    # Arrange
    user = _create_user(db=db)
    subscription = _create_active_subscription(db=db, user_id=user.id)
    subscription.cancel_at_period_end = True
    pending_override = UserAccessOverride(
        user_id=user.id,
        code="ambassador",
        is_unlimited=True,
        starts_at=subscription.current_period_end,
        notes="Ambassador access",
    )
    db.add(subscription)
    db.add(pending_override)
    db.commit()
    cancel_calls: list[bool] = []

    async def fake_set_subscription_cancel_at_period_end(
        *,
        stripe_subscription_id: str,
        cancel_at_period_end: bool,
    ) -> None:
        assert stripe_subscription_id == subscription.stripe_subscription_id
        cancel_calls.append(cancel_at_period_end)

    monkeypatch.setattr(
        stripe_client,
        "set_subscription_cancel_at_period_end",
        fake_set_subscription_cancel_at_period_end,
    )

    # Act
    changed = asyncio.run(
        access_write_service.set_access_profile_async(
            session=db,
            user_id=user.id,
            access_profile="base",
            utcnow_fn=lambda: datetime(2026, 4, 20, 18, 0, tzinfo=UTC),
        )
    )

    # Assert
    db.refresh(subscription)
    db.refresh(pending_override)
    assert changed is True
    assert cancel_calls == [False]
    assert subscription.cancel_at_period_end is False
    assert pending_override.revoked_at == datetime(2026, 4, 20, 18, 0, tzinfo=UTC)


def test_set_access_profile_async_stripe_failure_leaves_subscription_and_override_unchanged(
    db: Session,
    monkeypatch,
) -> None:
    # Arrange
    user = _create_user(db=db)
    subscription = _create_active_subscription(db=db, user_id=user.id)

    async def failing_set_subscription_cancel_at_period_end(
        *,
        stripe_subscription_id: str,
        cancel_at_period_end: bool,
    ) -> None:
        del stripe_subscription_id, cancel_at_period_end
        raise RuntimeError("stripe unavailable")

    monkeypatch.setattr(
        stripe_client,
        "set_subscription_cancel_at_period_end",
        failing_set_subscription_cancel_at_period_end,
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="stripe unavailable"):
        asyncio.run(
            access_write_service.set_access_profile_async(
                session=db,
                user_id=user.id,
                access_profile="ambassador",
                utcnow_fn=lambda: datetime(2026, 4, 20, 18, 0, tzinfo=UTC),
            )
        )
    db.refresh(subscription)
    overrides = db.exec(
        select(UserAccessOverride).where(UserAccessOverride.user_id == user.id)
    ).all()
    assert subscription.cancel_at_period_end is False
    assert overrides == []


def test_set_access_profile_async_ambassador_without_subscription_creates_active_override(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)

    # Act
    changed = asyncio.run(
        access_write_service.set_access_profile_async(
            session=db,
            user_id=user.id,
            access_profile="ambassador",
            utcnow_fn=lambda: now,
        )
    )

    # Assert
    override = db.exec(
        select(UserAccessOverride).where(UserAccessOverride.user_id == user.id)
    ).one()
    assert changed is True
    assert override.starts_at == now
    assert override.revoked_at is None
    assert override.is_unlimited is True


def test_set_access_profile_async_ambassador_existing_override_updates_override(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    override = UserAccessOverride(
        user_id=user.id,
        code="ambassador",
        is_unlimited=False,
        starts_at=now - timedelta(days=10),
        ends_at=now + timedelta(days=1),
        revoked_at=None,
        notes="Ambassador access",
    )
    db.add(override)
    db.commit()

    # Act
    changed = asyncio.run(
        access_write_service.set_access_profile_async(
            session=db,
            user_id=user.id,
            access_profile="ambassador",
            utcnow_fn=lambda: now,
        )
    )

    # Assert
    db.refresh(override)
    assert changed is True
    assert override.revoked_at is None
    assert override.ends_at is None
    assert override.is_unlimited is True
    assert override.updated_at == now


def test_sync_superuser_billing_access_async_false_is_noop(db: Session) -> None:
    # Arrange
    user = _create_user(db=db)
    subscription = _create_active_subscription(db=db, user_id=user.id)

    # Act
    changed = asyncio.run(
        access_write_service.sync_superuser_billing_access_async(
            session=db,
            user_id=user.id,
            is_superuser=False,
            utcnow_fn=lambda: datetime(2026, 4, 20, 18, 0, tzinfo=UTC),
        )
    )

    # Assert
    db.refresh(subscription)
    assert changed is False
    assert subscription.cancel_at_period_end is False


def test_pending_ambassador_starts_at_for_subscription_uses_cancel_or_end_fallbacks(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_fallback_{user.id}",
        stripe_customer_id=f"cus_fallback_{user.id}",
        status="canceled",
        current_period_start=None,
        current_period_end=None,
        cancel_at=now + timedelta(days=1),
        ended_at=now + timedelta(days=2),
        canceled_at=now + timedelta(days=3),
    )

    # Act / Assert
    assert access_write_service.pending_ambassador_starts_at_for_subscription(
        subscription=subscription,
    ) == now + timedelta(days=1)
    subscription.cancel_at = None
    assert access_write_service.pending_ambassador_starts_at_for_subscription(
        subscription=subscription,
    ) == now + timedelta(days=2)
    subscription.ended_at = None
    assert access_write_service.pending_ambassador_starts_at_for_subscription(
        subscription=subscription,
    ) == now + timedelta(days=3)


def test_sync_superuser_billing_access_async_marks_subscription_for_cancelation(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    subscription = _create_active_subscription(db=db, user_id=user.id)
    cancel_calls: list[bool] = []

    async def fake_set_subscription_cancel_at_period_end(
        *,
        stripe_subscription_id: str,
        cancel_at_period_end: bool,
    ) -> None:
        assert stripe_subscription_id == subscription.stripe_subscription_id
        cancel_calls.append(cancel_at_period_end)

    monkeypatch.setattr(
        stripe_client,
        "set_subscription_cancel_at_period_end",
        fake_set_subscription_cancel_at_period_end,
    )

    changed = asyncio.run(
        access_write_service.sync_superuser_billing_access_async(
            session=db,
            user_id=user.id,
            is_superuser=True,
            utcnow_fn=lambda: datetime(2026, 4, 20, 18, 0, tzinfo=UTC),
        )
    )

    db.refresh(subscription)
    assert changed is True
    assert cancel_calls == [True]
    assert subscription.cancel_at_period_end is True
