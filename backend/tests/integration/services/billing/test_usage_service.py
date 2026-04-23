from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.models import (
    BillingSubscription,
    UsageReservation,
    UserAccessOverride,
)
from app.features.billing.service import FEATURE_ENDPOINT_KEYS
from app.features.billing.services import usage as usage_service
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def _create_active_subscription(*, db: Session, user_id):
    now = datetime.now(UTC)
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


def test_reserve_feature_usage_is_idempotent_for_same_request_key(
    db: Session,
) -> None:
    subscription = _create_active_subscription(db=db, user_id=_create_user(db=db).id)
    request_key = f"usage:{subscription.user_id}"

    first = usage_service.reserve_feature_usage(
        session=db,
        user_id=subscription.user_id,
        feature_code="ig_scraper_apify",
        endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_apify"],
        max_units_requested=2,
        request_key=request_key,
    )
    second = usage_service.reserve_feature_usage(
        session=db,
        user_id=subscription.user_id,
        feature_code="ig_scraper_apify",
        endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_apify"],
        max_units_requested=2,
        request_key=request_key,
    )

    reservations = db.exec(
        select(UsageReservation).where(UsageReservation.request_key == request_key)
    ).all()

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert len(reservations) == 1


def test_reserve_feature_usage_uses_managed_cycle_for_ambassador_access(
    db: Session,
) -> None:
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    db.add(
        UserAccessOverride(
            user_id=user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=now - timedelta(minutes=1),
            notes="Ambassador access",
        )
    )
    db.commit()

    reservation = usage_service.reserve_feature_usage(
        session=db,
        user_id=user.id,
        feature_code="reputation_strategy",
        endpoint_key=FEATURE_ENDPOINT_KEYS["reputation_strategy.creator"],
        max_units_requested=1,
        request_key=f"managed:{user.id}",
        utcnow_fn=lambda: now,
    )

    assert reservation is not None
    assert reservation.usage_cycle_id is not None
