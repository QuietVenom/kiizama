import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import httpx
import pytest
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app import crud_users as crud
from app.core.config import settings
from app.features.billing import (
    FEATURE_ENDPOINT_KEYS,
    build_billing_summary,
    create_checkout_session,
    delete_user_billing_data,
    finalize_usage_reservation,
    process_pending_customer_sync_tasks_async,
    queue_customer_email_sync_async,
    release_usage_reservation,
    reserve_feature_usage,
    set_access_profile,
)
from app.features.billing import service as billing_service
from app.features.billing.models import (
    BillingCustomerSyncTask,
    BillingSubscription,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
    UserBillingAccount,
)
from app.models import User, UserCreate
from tests.utils.utils import random_email, random_password


def _create_active_subscription(*, db: Session) -> BillingSubscription:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    now = datetime.now(timezone.utc)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
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


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def _configure_stripe_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STRIPE_BASE_PRICE_ID", "price_base")


def test_create_checkout_session_for_trial_allows_missing_payment_method(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    captured: dict[str, str] = {}
    _configure_stripe_checkout(monkeypatch)

    async def fake_stripe_request(_method, path, *, data=None, params=None):
        if path == "/v1/customers":
            return {"id": f"cus_{user.id}"}
        if path == "/v1/checkout/sessions":
            captured.update(data or {})
            assert params is None
            return {"url": "https://checkout.stripe.test/session"}
        raise AssertionError(f"Unexpected Stripe call: {path}")

    monkeypatch.setattr(billing_service, "_stripe_request", fake_stripe_request)

    checkout_url = asyncio.run(create_checkout_session(session=db, user=user))

    assert checkout_url == "https://checkout.stripe.test/session"
    assert captured["payment_method_collection"] == "if_required"
    assert captured["subscription_data[trial_period_days]"] == "7"
    assert (
        captured[
            "subscription_data[trial_settings][end_behavior][missing_payment_method]"
        ]
        == "pause"
    )


def test_create_checkout_session_after_trial_keeps_payment_method_required(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    _configure_stripe_checkout(monkeypatch)
    db.add(
        UserBillingAccount(
            user_id=user.id,
            stripe_customer_id=f"cus_{user.id}",
            has_used_trial=True,
        )
    )
    db.commit()
    captured: dict[str, str] = {}

    async def fake_stripe_request(_method, path, *, data=None, params=None):
        if path == "/v1/checkout/sessions":
            captured.update(data or {})
            assert params is None
            return {"url": "https://checkout.stripe.test/session"}
        raise AssertionError(f"Unexpected Stripe call: {path}")

    monkeypatch.setattr(billing_service, "_stripe_request", fake_stripe_request)

    checkout_url = asyncio.run(create_checkout_session(session=db, user=user))

    assert checkout_url == "https://checkout.stripe.test/session"
    assert "payment_method_collection" not in captured
    assert "subscription_data[trial_period_days]" not in captured


def test_create_checkout_session_allows_repurchase_after_refund_revocation(
    db: Session,
    monkeypatch,
) -> None:
    _configure_stripe_checkout(monkeypatch)
    subscription = _create_active_subscription(db=db)
    subscription.latest_invoice_status = "refunded"
    subscription.access_revoked_at = datetime.now(timezone.utc)
    subscription.access_revoked_reason = "refunded"
    db.add(subscription)
    db.add(
        UserBillingAccount(
            user_id=subscription.user_id,
            stripe_customer_id=subscription.stripe_customer_id,
            has_used_trial=True,
        )
    )
    db.commit()
    user = db.get(User, subscription.user_id)
    assert user is not None

    captured: dict[str, str] = {}

    async def fake_stripe_request(_method, path, *, data=None, params=None):
        if path == "/v1/checkout/sessions":
            captured.update(data or {})
            assert params is None
            return {"url": "https://checkout.stripe.test/repurchase"}
        raise AssertionError(f"Unexpected Stripe call: {path}")

    monkeypatch.setattr(billing_service, "_stripe_request", fake_stripe_request)

    checkout_url = asyncio.run(create_checkout_session(session=db, user=user))

    assert checkout_url == "https://checkout.stripe.test/repurchase"
    assert captured["customer"] == subscription.stripe_customer_id


def test_queue_customer_email_sync_coalesces_pending_task(db: Session) -> None:
    user = _create_user(db=db)
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id=f"cus_{user.id}"))
    db.commit()

    first_email = "first-sync@example.com"
    user.email = first_email
    db.add(user)
    db.commit()
    asyncio.run(
        queue_customer_email_sync_async(
            session=db,
            user=user,
            previous_email="before@example.com",
        )
    )

    second_email = "second-sync@example.com"
    user.email = second_email
    db.add(user)
    db.commit()
    asyncio.run(
        queue_customer_email_sync_async(
            session=db,
            user=user,
            previous_email=first_email,
        )
    )

    tasks = db.exec(
        select(BillingCustomerSyncTask).where(
            BillingCustomerSyncTask.user_id == user.id
        )
    ).all()

    assert len(tasks) == 1
    assert tasks[0].status == "pending"
    assert tasks[0].desired_email == second_email
    assert tasks[0].attempt_count == 0


def test_process_pending_customer_sync_tasks_async_succeeds(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    task = BillingCustomerSyncTask(
        user_id=user.id,
        stripe_customer_id=f"cus_{user.id}",
        desired_email="sync-worker@example.com",
        status="pending",
        next_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    async def fake_stripe_request_raw(
        method, path, *, data=None, params=None, extra_headers=None
    ):
        assert method == "POST"
        assert path == f"/v1/customers/cus_{user.id}"
        assert data == {"email": "sync-worker@example.com"}
        assert params is None
        assert extra_headers is not None
        return httpx.Response(
            200,
            headers={"Request-Id": "req_worker"},
            json={"id": f"cus_{user.id}", "email": "sync-worker@example.com"},
        )

    monkeypatch.setattr(billing_service, "_stripe_request_raw", fake_stripe_request_raw)

    processed = asyncio.run(
        process_pending_customer_sync_tasks_async(session=db, max_tasks=1)
    )

    db.refresh(task)
    assert processed == 1
    assert task.status == "succeeded"
    assert task.attempt_count == 1
    assert task.last_stripe_request_id == "req_worker"


def test_finalize_usage_reservation_tracks_partial_success(db: Session) -> None:
    subscription = _create_active_subscription(db=db)
    request_key = f"partial:{subscription.user_id}"

    reservation = reserve_feature_usage(
        session=db,
        user_id=subscription.user_id,
        feature_code="ig_scraper_apify",
        endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_apify"],
        max_units_requested=7,
        request_key=request_key,
    )

    assert reservation is not None
    event = finalize_usage_reservation(
        session=db,
        request_key=request_key,
        quantity_consumed=5,
        metadata={"successful": 5, "requested": 7},
    )

    assert event is not None
    reservation_db = db.exec(
        select(UsageReservation).where(UsageReservation.request_key == request_key)
    ).one()
    cycle_feature = db.exec(
        select(UsageCycleFeature).where(
            UsageCycleFeature.usage_cycle_id == reservation_db.usage_cycle_id,
            UsageCycleFeature.feature_code == "ig_scraper_apify",
        )
    ).one()
    usage_event = db.exec(
        select(UsageEvent).where(UsageEvent.request_key == request_key)
    ).one()

    assert reservation_db.status == "finalized"
    assert reservation_db.consumed_count == 5
    assert cycle_feature.used_count == 5
    assert cycle_feature.reserved_count == 0
    assert usage_event.quantity_requested == 7
    assert usage_event.quantity_consumed == 5
    assert usage_event.result_status == "partial_success"


def test_release_usage_reservation_clears_reserved_units(db: Session) -> None:
    subscription = _create_active_subscription(db=db)
    request_key = f"release:{subscription.user_id}"

    reservation = reserve_feature_usage(
        session=db,
        user_id=subscription.user_id,
        feature_code="reputation_strategy",
        endpoint_key=FEATURE_ENDPOINT_KEYS["reputation_strategy.creator"],
        max_units_requested=1,
        request_key=request_key,
    )

    assert reservation is not None
    event = release_usage_reservation(
        session=db,
        request_key=request_key,
        metadata={"error": "upstream-failure"},
    )

    assert event is not None
    reservation_db = db.exec(
        select(UsageReservation).where(UsageReservation.request_key == request_key)
    ).one()
    cycle_feature = db.exec(
        select(UsageCycleFeature).where(
            UsageCycleFeature.usage_cycle_id == reservation_db.usage_cycle_id,
            UsageCycleFeature.feature_code == "reputation_strategy",
        )
    ).one()

    assert reservation_db.status == "released"
    assert reservation_db.consumed_count == 0
    assert cycle_feature.used_count == 0
    assert cycle_feature.reserved_count == 0


def test_ambassador_usage_is_tracked_in_managed_monthly_cycle(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(billing_service, "utcnow", lambda: now)
    set_access_profile(session=db, user_id=user.id, access_profile="ambassador")

    request_key = f"ambassador:{user.id}"
    reservation = reserve_feature_usage(
        session=db,
        user_id=user.id,
        feature_code="ig_scraper_apify",
        endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_apify"],
        max_units_requested=4,
        request_key=request_key,
    )

    assert reservation is not None
    event = finalize_usage_reservation(
        session=db,
        request_key=request_key,
        quantity_consumed=4,
    )

    assert event is not None
    summary = build_billing_summary(session=db, user_id=user.id)
    profiles_usage = next(
        feature for feature in summary.features if feature.code == "ig_scraper"
    )

    assert summary.managed_access_source == "ambassador"
    assert profiles_usage.used == 4
    assert profiles_usage.is_unlimited is True


def test_limit_exceeded_error_uses_public_feature_code(db: Session) -> None:
    subscription = _create_active_subscription(db=db)

    with pytest.raises(HTTPException) as exc_info:
        reserve_feature_usage(
            session=db,
            user_id=subscription.user_id,
            feature_code="ig_scraper_apify",
            endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_apify"],
            max_units_requested=51,
            request_key=f"limit:{subscription.user_id}",
        )

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail == "Credit limit exceeded for feature 'ig_scraper'."


def test_superuser_usage_is_tracked_in_managed_monthly_cycle(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    user.is_superuser = True
    db.add(user)
    db.commit()
    now = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(billing_service, "utcnow", lambda: now)

    request_key = f"admin:{user.id}"
    reservation = reserve_feature_usage(
        session=db,
        user_id=user.id,
        feature_code="reputation_strategy",
        endpoint_key=FEATURE_ENDPOINT_KEYS["reputation_strategy.creator"],
        max_units_requested=2,
        request_key=request_key,
    )

    assert reservation is not None
    event = finalize_usage_reservation(
        session=db,
        request_key=request_key,
        quantity_consumed=2,
    )

    assert event is not None
    summary = build_billing_summary(session=db, user_id=user.id)
    reputation_usage = next(
        feature for feature in summary.features if feature.code == "reputation_strategy"
    )

    assert summary.managed_access_source == "admin"
    assert reputation_usage.used == 2
    assert reputation_usage.is_unlimited is True


def test_set_access_profile_reverting_pending_ambassador_restores_trial_subscription(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=timezone.utc)
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

    cancel_at_period_end_calls: list[bool] = []

    async def fake_set_subscription_cancel_at_period_end(
        *,
        stripe_subscription_id: str,
        cancel_at_period_end: bool,
    ) -> None:
        assert stripe_subscription_id == subscription.stripe_subscription_id
        cancel_at_period_end_calls.append(cancel_at_period_end)

    monkeypatch.setattr(
        billing_service,
        "_set_subscription_cancel_at_period_end",
        fake_set_subscription_cancel_at_period_end,
    )

    ambassador_changed = asyncio.run(
        billing_service.set_access_profile_async(
            session=db,
            user_id=user.id,
            access_profile="ambassador",
        )
    )
    db.refresh(subscription)

    standard_changed = asyncio.run(
        billing_service.set_access_profile_async(
            session=db,
            user_id=user.id,
            access_profile="standard",
        )
    )
    db.refresh(subscription)
    summary = build_billing_summary(session=db, user_id=user.id)

    assert ambassador_changed is True
    assert standard_changed is True
    assert cancel_at_period_end_calls == [True, False]
    assert subscription.cancel_at_period_end is False
    assert summary.access_profile == "standard"
    assert summary.managed_access_source is None
    assert summary.pending_ambassador_activation is False
    assert summary.plan_status == "trial"
    assert summary.subscription_status == "trialing"
    assert summary.cancel_at is None


def test_managed_usage_resets_with_new_utc_month(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    april_now = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(billing_service, "utcnow", lambda: april_now)
    set_access_profile(session=db, user_id=user.id, access_profile="ambassador")

    request_key = f"month-reset:{user.id}"
    reservation = reserve_feature_usage(
        session=db,
        user_id=user.id,
        feature_code="social_media_report",
        endpoint_key=FEATURE_ENDPOINT_KEYS["social_media_report"],
        max_units_requested=3,
        request_key=request_key,
    )
    assert reservation is not None
    finalize_usage_reservation(
        session=db,
        request_key=request_key,
        quantity_consumed=3,
    )

    may_now = datetime(2026, 5, 2, 9, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(billing_service, "utcnow", lambda: may_now)
    summary = build_billing_summary(session=db, user_id=user.id)
    reports_usage = next(
        feature for feature in summary.features if feature.code == "social_media_report"
    )
    managed_cycles = db.exec(
        select(UsageCycle)
        .where(
            UsageCycle.user_id == user.id,
            UsageCycle.source_type == "managed",
        )
        .order_by(cast(Any, UsageCycle.period_start))
    ).all()

    assert summary.managed_access_source == "ambassador"
    assert summary.current_period_start == datetime(
        2026, 5, 1, 0, 0, tzinfo=timezone.utc
    )
    assert summary.current_period_end == datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    assert reports_usage.used == 0
    assert len(managed_cycles) == 2
    assert managed_cycles[0].period_start == datetime(
        2026, 4, 1, 0, 0, tzinfo=timezone.utc
    )
    assert managed_cycles[1].period_start == datetime(
        2026, 5, 1, 0, 0, tzinfo=timezone.utc
    )


def test_delete_user_billing_data_removes_managed_cycles_without_fk_errors(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(billing_service, "utcnow", lambda: now)
    set_access_profile(session=db, user_id=user.id, access_profile="ambassador")

    request_key = f"delete-billing:{user.id}"
    reservation = reserve_feature_usage(
        session=db,
        user_id=user.id,
        feature_code="ig_scraper_apify",
        endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_apify"],
        max_units_requested=1,
        request_key=request_key,
    )
    assert reservation is not None
    finalize_usage_reservation(
        session=db,
        request_key=request_key,
        quantity_consumed=1,
    )

    asyncio.run(delete_user_billing_data(session=db, user_id=user.id))

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


def test_delete_user_billing_data_continues_when_stripe_cleanup_fails(
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
        billing_service,
        "_cancel_stripe_subscription_immediately",
        fail_cancel,
    )
    monkeypatch.setattr(
        billing_service,
        "_delete_stripe_customer",
        fail_delete_customer,
    )

    asyncio.run(delete_user_billing_data(session=db, user_id=subscription.user_id))

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
