import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import httpx
import pytest
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app import crud_users as crud
from app.features.account_cleanup import (
    cleanup_user_related_data_before_delete,
    delete_user_event_stream_best_effort,
)
from app.features.account_cleanup.services import user_cleanup as user_cleanup_service
from app.features.billing.models import (
    BillingSubscription,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
    UserAccessOverride,
    UserBillingAccount,
)
from app.features.billing.services import access_write as access_write_service
from app.features.billing.services import cleanup as billing_cleanup_service
from app.features.billing.services import usage as usage_service
from app.features.user_events.repository import (
    UserEventsRepository,
    UserEventsUnavailableError,
    build_user_events_stream_key,
)
from app.features.user_events.schemas import UserEventEnvelope
from app.models import IgScrapeJob, User, UserCreate, UserLegalAcceptance
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def _create_active_subscription(*, db: Session) -> BillingSubscription:
    user = _create_user(db=db)
    now = datetime.now(UTC)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=now,
        current_period_end=now,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def _build_user_event_envelope() -> UserEventEnvelope:
    return UserEventEnvelope(
        topic="account",
        source="backend",
        kind="account.subscription.updated",
        notification_id="notification-1",
        payload={"status": "active"},
    )


def test_cleanup_user_related_data_before_delete_removes_billing_and_cross_feature_state(
    db: Session,
) -> None:
    user = _create_user(db=db)
    other_user = _create_user(db=db)

    request_key = f"cleanup:{user.id}"
    asyncio.run(
        access_write_service.set_access_profile_async(
            session=db,
            user_id=user.id,
            access_profile="ambassador",
        )
    )
    reservation = usage_service.reserve_feature_usage(
        session=db,
        user_id=user.id,
        feature_code="ig_scraper_apify",
        endpoint_key="ig_scraper_apify",
        max_units_requested=1,
        request_key=request_key,
    )
    assert reservation is not None
    usage_service.finalize_usage_reservation(
        session=db,
        request_key=request_key,
        quantity_consumed=1,
    )

    db.add(
        UserBillingAccount(
            user_id=user.id,
            stripe_customer_id=f"cus_{user.id}",
        )
    )
    db.add(
        UserLegalAcceptance(
            user_id=user.id,
            document_type="privacy_notice",
            document_version="v1",
            source="public_signup",
        )
    )
    bind = db.get_bind()
    cast(Any, IgScrapeJob).__table__.create(bind=bind, checkfirst=True)
    db.add(
        IgScrapeJob(
            owner_user_id=user.id,
            payload={"usernames": ["alpha"]},
            expires_at=datetime.now(UTC),
        )
    )
    override = UserAccessOverride(
        user_id=other_user.id,
        code="ambassador",
        is_unlimited=True,
        starts_at=datetime.now(UTC),
        created_by_admin_id=user.id,
        notes="Created by deleted user",
    )
    db.add(override)
    db.commit()

    asyncio.run(cleanup_user_related_data_before_delete(session=db, user_id=user.id))

    assert db.get(User, user.id) is not None
    assert db.exec(select(UsageCycle).where(UsageCycle.user_id == user.id)).all() == []
    assert (
        db.exec(
            select(UsageCycleFeature)
            .join(
                UsageCycle,
                cast(Any, UsageCycle.id) == cast(Any, UsageCycleFeature.usage_cycle_id),
            )
            .where(UsageCycle.user_id == user.id)
        ).all()
        == []
    )
    assert (
        db.exec(
            select(UsageReservation).where(UsageReservation.user_id == user.id)
        ).all()
        == []
    )
    assert db.exec(select(UsageEvent).where(UsageEvent.user_id == user.id)).all() == []
    assert (
        db.exec(
            select(UserLegalAcceptance).where(UserLegalAcceptance.user_id == user.id)
        ).all()
        == []
    )
    assert (
        db.exec(select(IgScrapeJob).where(IgScrapeJob.owner_user_id == user.id)).all()
        == []
    )
    assert (
        db.exec(
            select(BillingSubscription).where(BillingSubscription.user_id == user.id)
        ).all()
        == []
    )
    assert (
        db.exec(
            select(UserBillingAccount).where(UserBillingAccount.user_id == user.id)
        ).all()
        == []
    )
    persisted_override = db.get(UserAccessOverride, override.id)
    assert persisted_override is not None
    assert persisted_override.created_by_admin_id is None


def test_cleanup_user_related_data_before_delete_successful_stripe_cleanup_calls_remote_before_local_delete(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _create_active_subscription(db=db)
    db.add(
        UserBillingAccount(
            user_id=subscription.user_id,
            stripe_customer_id=subscription.stripe_customer_id,
        )
    )
    db.commit()
    calls: list[str] = []

    def assert_local_billing_state_exists() -> None:
        assert db.get(BillingSubscription, subscription.id) is not None
        assert (
            db.exec(
                select(UserBillingAccount).where(
                    UserBillingAccount.user_id == subscription.user_id
                )
            ).one()
            is not None
        )

    async def fake_cancel(*, stripe_subscription_id: str) -> None:
        assert stripe_subscription_id == subscription.stripe_subscription_id
        assert_local_billing_state_exists()
        calls.append("cancel_subscription")

    async def fake_delete_customer(stripe_customer_id: str) -> None:
        assert stripe_customer_id == subscription.stripe_customer_id
        assert_local_billing_state_exists()
        calls.append("delete_customer")

    monkeypatch.setattr(
        billing_cleanup_service,
        "cancel_stripe_subscription_immediately",
        fake_cancel,
    )
    monkeypatch.setattr(
        billing_cleanup_service,
        "delete_stripe_customer",
        fake_delete_customer,
    )

    asyncio.run(
        cleanup_user_related_data_before_delete(
            session=db,
            user_id=subscription.user_id,
        )
    )

    assert calls == ["cancel_subscription", "delete_customer"]
    assert db.get(User, subscription.user_id) is not None
    assert db.get(BillingSubscription, subscription.id) is None
    assert (
        db.exec(
            select(UserBillingAccount).where(
                UserBillingAccount.user_id == subscription.user_id
            )
        ).all()
        == []
    )


@pytest.mark.anyio
async def test_delete_user_event_stream_best_effort_removes_only_target_stream(
    redis_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.UUID(int=1)
    other_user_id = uuid.UUID(int=2)
    repository = UserEventsRepository(redis_provider=lambda: redis_client)
    await repository.publish_event(
        user_id=str(user_id),
        event_name="account.subscription.updated",
        envelope=_build_user_event_envelope(),
    )
    await repository.publish_event(
        user_id=str(other_user_id),
        event_name="account.subscription.updated",
        envelope=_build_user_event_envelope(),
    )

    monkeypatch.setattr(
        user_cleanup_service,
        "get_user_events_repository",
        lambda: repository,
    )
    await delete_user_event_stream_best_effort(user_id=user_id)

    assert await redis_client.exists(build_user_events_stream_key(str(user_id))) == 0
    assert (
        await redis_client.exists(build_user_events_stream_key(str(other_user_id))) == 1
    )


def test_delete_user_event_stream_best_effort_continues_when_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.UUID(int=1)

    class FailingUserEventsRepository:
        async def delete_user_stream(self, *, user_id: str) -> None:
            assert user_id == str(uuid.UUID(int=1))
            raise UserEventsUnavailableError("Redis unavailable")

    monkeypatch.setattr(
        user_cleanup_service,
        "get_user_events_repository",
        lambda: FailingUserEventsRepository(),
    )

    asyncio.run(delete_user_event_stream_best_effort(user_id=user_id))


def test_cleanup_user_related_data_before_delete_continues_when_stripe_cleanup_fails(
    db: Session,
    monkeypatch,
) -> None:
    subscription = _create_active_subscription(db=db)
    db.add(
        UserBillingAccount(
            user_id=subscription.user_id,
            stripe_customer_id=subscription.stripe_customer_id,
        )
    )
    db.commit()

    async def fail_cancel(*, stripe_subscription_id: str) -> None:
        assert stripe_subscription_id == subscription.stripe_subscription_id
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe request failed.",
        )

    async def fail_delete_customer(stripe_customer_id: str) -> None:
        assert stripe_customer_id == subscription.stripe_customer_id
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe request failed.",
        )

    monkeypatch.setattr(
        billing_cleanup_service,
        "cancel_stripe_subscription_immediately",
        fail_cancel,
    )
    monkeypatch.setattr(
        billing_cleanup_service,
        "delete_stripe_customer",
        fail_delete_customer,
    )

    asyncio.run(
        cleanup_user_related_data_before_delete(
            session=db,
            user_id=subscription.user_id,
        )
    )

    assert db.get(User, subscription.user_id) is not None
    assert (
        db.exec(
            select(BillingSubscription).where(
                BillingSubscription.user_id == subscription.user_id
            )
        ).all()
        == []
    )
    assert (
        db.exec(
            select(UserBillingAccount).where(
                UserBillingAccount.user_id == subscription.user_id
            )
        ).all()
        == []
    )


def test_cleanup_user_related_data_before_delete_continues_when_stripe_times_out(
    db: Session,
    monkeypatch,
) -> None:
    subscription = _create_active_subscription(db=db)
    db.add(
        UserBillingAccount(
            user_id=subscription.user_id,
            stripe_customer_id=subscription.stripe_customer_id,
        )
    )
    db.commit()

    async def fail_cancel(*, stripe_subscription_id: str) -> None:
        assert stripe_subscription_id == subscription.stripe_subscription_id
        raise httpx.TimeoutException("Stripe timeout during subscription cleanup")

    async def fail_delete_customer(stripe_customer_id: str) -> None:
        assert stripe_customer_id == subscription.stripe_customer_id
        raise httpx.TimeoutException("Stripe timeout during customer cleanup")

    monkeypatch.setattr(
        billing_cleanup_service,
        "cancel_stripe_subscription_immediately",
        fail_cancel,
    )
    monkeypatch.setattr(
        billing_cleanup_service,
        "delete_stripe_customer",
        fail_delete_customer,
    )

    asyncio.run(
        cleanup_user_related_data_before_delete(
            session=db,
            user_id=subscription.user_id,
        )
    )

    assert db.get(User, subscription.user_id) is not None
    assert (
        db.exec(
            select(BillingSubscription).where(
                BillingSubscription.user_id == subscription.user_id
            )
        ).all()
        == []
    )
    assert (
        db.exec(
            select(UserBillingAccount).where(
                UserBillingAccount.user_id == subscription.user_id
            )
        ).all()
        == []
    )
