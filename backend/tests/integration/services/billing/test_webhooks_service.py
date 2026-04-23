import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.clients import stripe as stripe_client
from app.features.billing.models import (
    BillingNotice,
    BillingSubscription,
    UsageCycle,
    UserAccessOverride,
    UserBillingAccount,
)
from app.features.billing.services import access_read as access_read_service
from app.features.billing.services.webhooks import process_stripe_webhook
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def _subscription_payload(
    *,
    subscription_id: str,
    customer_id: str,
    user_id: uuid.UUID,
    status: str,
    price_id: str = "price_base",
    latest_invoice_id: str = "in_default",
    latest_invoice_status: str = "paid",
    cancel_at: int | None = None,
    cancellation_reason: str | None = None,
    canceled_at: int | None = None,
    ended_at: int | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "id": subscription_id,
        "object": "subscription",
        "customer": customer_id,
        "status": status,
        "metadata": {"user_id": str(user_id)},
        "collection_method": "charge_automatically",
        "cancel_at_period_end": False,
        "cancel_at": cancel_at,
        "current_period_start": int(now.timestamp()),
        "current_period_end": int((now + timedelta(days=30)).timestamp()),
        "trial_start": None,
        "trial_end": None,
        "canceled_at": canceled_at,
        "ended_at": ended_at,
        "cancellation_details": {
            "reason": cancellation_reason,
            "comment": None,
            "feedback": None,
        },
        "items": {
            "data": [
                {
                    "price": {"id": price_id},
                }
            ]
        },
        "latest_invoice": {
            "id": latest_invoice_id,
            "status": latest_invoice_status,
        },
    }


def _stripe_event(
    *, event_type: str, obj: dict[str, Any], event_id: str | None = None
) -> dict[str, Any]:
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "created": int(datetime.now(UTC).timestamp()),
        "data": {"object": obj},
    }


def _create_subscription(
    *,
    db: Session,
    user_id: uuid.UUID,
    stripe_subscription_id: str,
    stripe_customer_id: str,
    latest_invoice_id: str,
    status: str = "active",
    latest_invoice_status: str = "paid",
) -> BillingSubscription:
    now = datetime.now(UTC)
    subscription = BillingSubscription(
        user_id=user_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_customer_id=stripe_customer_id,
        stripe_price_id="price_base",
        plan_code="base",
        status=status,
        collection_method="charge_automatically",
        current_period_start=now - timedelta(days=1),
        current_period_end=now + timedelta(days=29),
        latest_invoice_id=latest_invoice_id,
        latest_invoice_status=latest_invoice_status,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def _open_usage_cycle(*, db: Session, subscription: BillingSubscription) -> UsageCycle:
    access_read_service.get_access_snapshot(session=db, user_id=subscription.user_id)
    return db.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == subscription.user_id,
            UsageCycle.status == "open",
        )
    ).one()


def test_process_stripe_webhook_customer_subscription_created_creates_subscription_before_checkout(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    payload = _stripe_event(
        event_type="customer.subscription.created",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="active",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
        ),
    )

    notified_user_id = asyncio.run(process_stripe_webhook(session=db, payload=payload))

    subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()
    account = db.exec(
        select(UserBillingAccount).where(UserBillingAccount.user_id == user.id)
    ).one()

    assert notified_user_id == user.id
    assert subscription.user_id == user.id
    assert subscription.status == "active"
    assert subscription.stripe_customer_id == customer_id
    assert account.stripe_customer_id == customer_id


def test_process_stripe_webhook_customer_subscription_created_updates_existing_without_duplicate(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
        latest_invoice_id=f"in_{uuid.uuid4().hex}",
        status="incomplete",
        latest_invoice_status="open",
    )

    updated_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="active",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
        ),
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=updated_payload)
    )

    repeated_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj=updated_payload["data"]["object"],
    )

    repeated_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=repeated_payload)
    )
    subscriptions = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).all()

    assert notified_user_id == user.id
    assert repeated_user_id is None
    assert len(subscriptions) == 1
    assert subscriptions[0].status == "active"


def test_process_stripe_webhook_customer_subscription_created_uses_item_level_periods(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    now = datetime.now(UTC)
    payload = _stripe_event(
        event_type="customer.subscription.created",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id=f"in_{uuid.uuid4().hex}",
            ),
            "current_period_start": None,
            "current_period_end": None,
            "trial_start": int(now.timestamp()),
            "trial_end": int((now + timedelta(days=7)).timestamp()),
            "items": {
                "data": [
                    {
                        "price": {"id": "price_base"},
                        "current_period_start": int(now.timestamp()),
                        "current_period_end": int(
                            (now + timedelta(days=30)).timestamp()
                        ),
                    }
                ]
            },
        },
    )

    notified_user_id = asyncio.run(process_stripe_webhook(session=db, payload=payload))

    subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()
    account = db.exec(
        select(UserBillingAccount).where(UserBillingAccount.user_id == user.id)
    ).one()
    cycle = db.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user.id,
            UsageCycle.source_id == subscription.id,
            UsageCycle.status == "open",
        )
    ).one()

    assert notified_user_id == user.id
    assert subscription.status == "trialing"
    assert subscription.current_period_start is not None
    assert subscription.current_period_end is not None
    assert account.has_used_trial is True
    assert account.trial_started_at is not None
    assert account.trial_ended_at is not None
    assert cycle.plan_code == "trial"


def test_process_stripe_webhook_customer_subscription_updated_persists_scheduled_cancellation(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    cancel_at = int((datetime.now(UTC) + timedelta(days=7)).timestamp())

    payload = _stripe_event(
        event_type="customer.subscription.updated",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="trialing",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
            cancel_at=cancel_at,
            cancellation_reason="cancellation_requested",
        ),
    )

    notified_user_id = asyncio.run(process_stripe_webhook(session=db, payload=payload))

    subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()

    assert notified_user_id == user.id
    assert subscription.cancel_at is not None
    assert subscription.cancel_at == datetime.fromtimestamp(cancel_at, tz=UTC)
    assert subscription.cancellation_reason == "cancellation_requested"


def test_process_stripe_webhook_customer_subscription_updated_clears_removed_scheduled_cancellation(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    initial_cancel_at = int((datetime.now(UTC) + timedelta(days=7)).timestamp())

    initial_payload = _stripe_event(
        event_type="customer.subscription.updated",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="trialing",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
            cancel_at=initial_cancel_at,
            cancellation_reason="cancellation_requested",
        ),
    )
    cleared_payload = _stripe_event(
        event_type="customer.subscription.updated",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="trialing",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
        ),
    )

    asyncio.run(process_stripe_webhook(session=db, payload=initial_payload))
    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=cleared_payload)
    )

    subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()

    assert notified_user_id == user.id
    assert subscription.cancel_at is None
    assert subscription.cancellation_reason is None


def test_process_stripe_webhook_customer_subscription_deleted_closes_access_cycle(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="active",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
        ),
    )
    asyncio.run(process_stripe_webhook(session=db, payload=created_payload))

    subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()
    cycle = _open_usage_cycle(db=db, subscription=subscription)
    ended_at = int(datetime.now(UTC).timestamp())
    deleted_payload = _stripe_event(
        event_type="customer.subscription.deleted",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="canceled",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
            canceled_at=ended_at,
            ended_at=ended_at,
        ),
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=deleted_payload)
    )

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)

    assert notified_user_id == user.id
    assert refreshed_subscription is not None
    assert refreshed_subscription.status == "canceled"
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "closed"


def test_process_stripe_webhook_customer_subscription_paused_replaces_trial_notice(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    now = datetime.now(UTC)
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id=f"in_{uuid.uuid4().hex}",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=created_payload))

    trial_notice_payload = _stripe_event(
        event_type="customer.subscription.trial_will_end",
        obj={
            "id": subscription_id,
            "object": "subscription",
            "subscription": subscription_id,
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=trial_notice_payload))

    paused_payload = _stripe_event(
        event_type="customer.subscription.paused",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="paused",
                latest_invoice_id=f"in_{uuid.uuid4().hex}",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int((now + timedelta(days=7)).timestamp()),
            "current_period_end": int(now.timestamp()),
        },
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=paused_payload)
    )

    refreshed_subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()
    notices = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).all()
    trial_notice = next(
        notice for notice in notices if notice.notice_type == "trial_will_end"
    )
    paused_notice = next(
        notice for notice in notices if notice.notice_type == "subscription_paused"
    )

    assert notified_user_id == user.id
    assert refreshed_subscription.status == "paused"
    assert trial_notice.status == "dismissed"
    assert paused_notice.status == "unread"
    assert "paused because the trial ended" in paused_notice.message


def test_process_stripe_webhook_customer_subscription_updated_reschedules_pending_ambassador_override(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    original_period_end = now + timedelta(days=7)
    shortened_period_end = now + timedelta(days=2)
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id=f"in_{uuid.uuid4().hex}",
            ),
            "current_period_start": int(now.timestamp()),
            "current_period_end": int(original_period_end.timestamp()),
            "trial_start": int(now.timestamp()),
            "trial_end": int(original_period_end.timestamp()),
        },
    )
    asyncio.run(
        process_stripe_webhook(
            session=db,
            payload=created_payload,
            utcnow_fn=lambda: now,
        )
    )

    db.add(
        UserAccessOverride(
            user_id=user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=original_period_end,
            notes="Ambassador access",
        )
    )
    db.commit()

    updated_payload = _stripe_event(
        event_type="customer.subscription.updated",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id=f"in_{uuid.uuid4().hex}",
                cancel_at=int(shortened_period_end.timestamp()),
                cancellation_reason="cancellation_requested",
            ),
            "cancel_at_period_end": True,
            "current_period_start": int(now.timestamp()),
            "current_period_end": int(shortened_period_end.timestamp()),
            "trial_start": int(now.timestamp()),
            "trial_end": int(shortened_period_end.timestamp()),
        },
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(
            session=db,
            payload=updated_payload,
            utcnow_fn=lambda: now,
        )
    )

    pending_override = db.exec(
        select(UserAccessOverride)
        .where(
            UserAccessOverride.user_id == user.id,
            cast(Any, UserAccessOverride.revoked_at).is_(None),
        )
        .order_by(cast(Any, UserAccessOverride.created_at).desc())
    ).first()
    summary = access_read_service.build_billing_summary(
        session=db,
        user_id=user.id,
        utcnow_fn=lambda: now,
    )

    assert notified_user_id == user.id
    assert pending_override is not None
    assert pending_override.starts_at == shortened_period_end
    assert summary.managed_access_source is None
    assert summary.pending_ambassador_activation is True
    assert summary.plan_status == "trial"
    assert summary.subscription_status == "trialing"


def test_process_stripe_webhook_customer_subscription_paused_activates_pending_ambassador_override(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    original_period_end = now + timedelta(days=7)
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id=f"in_{uuid.uuid4().hex}",
            ),
            "current_period_start": int(now.timestamp()),
            "current_period_end": int(original_period_end.timestamp()),
            "trial_start": int(now.timestamp()),
            "trial_end": int(original_period_end.timestamp()),
        },
    )
    asyncio.run(
        process_stripe_webhook(
            session=db,
            payload=created_payload,
            utcnow_fn=lambda: now,
        )
    )

    db.add(
        UserAccessOverride(
            user_id=user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=original_period_end,
            notes="Ambassador access",
        )
    )
    db.commit()

    paused_payload = _stripe_event(
        event_type="customer.subscription.paused",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="paused",
                latest_invoice_id=f"in_{uuid.uuid4().hex}",
                cancel_at=int(now.timestamp()),
                cancellation_reason="cancellation_requested",
                canceled_at=int(now.timestamp()),
            ),
            "cancel_at_period_end": True,
            "current_period_start": int(now.timestamp()),
            "current_period_end": int(now.timestamp()),
            "trial_start": int(now.timestamp()),
            "trial_end": int((now - timedelta(seconds=1)).timestamp()),
        },
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(
            session=db,
            payload=paused_payload,
            utcnow_fn=lambda: now,
        )
    )

    active_override = db.exec(
        select(UserAccessOverride)
        .where(
            UserAccessOverride.user_id == user.id,
            cast(Any, UserAccessOverride.revoked_at).is_(None),
        )
        .order_by(cast(Any, UserAccessOverride.created_at).desc())
    ).first()
    summary = access_read_service.build_billing_summary(
        session=db,
        user_id=user.id,
        utcnow_fn=lambda: now,
    )

    assert notified_user_id == user.id
    assert active_override is not None
    assert active_override.starts_at == now
    assert summary.access_profile == "ambassador"
    assert summary.managed_access_source == "ambassador"
    assert summary.pending_ambassador_activation is False
    assert summary.plan_status == "ambassador"
    assert summary.subscription_status is None
    assert all(feature.is_unlimited is True for feature in summary.features)


def test_process_stripe_webhook_invoice_paid_dismisses_trial_notice_after_trial_completion(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    now = datetime.now(UTC)
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id="in_trial",
                latest_invoice_status="paid",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=created_payload))

    trial_notice_payload = _stripe_event(
        event_type="customer.subscription.trial_will_end",
        obj={
            "id": subscription_id,
            "object": "subscription",
            "subscription": subscription_id,
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=trial_notice_payload))

    async def fake_fetch_stripe_subscription(_subscription_id: str) -> dict[str, Any]:
        assert _subscription_id == subscription_id
        return {
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="active",
                latest_invoice_id="in_paid",
                latest_invoice_status="paid",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int(now.timestamp()),
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_subscription",
        fake_fetch_stripe_subscription,
    )

    invoice_paid_payload = _stripe_event(
        event_type="invoice.paid",
        obj={
            "id": "in_paid",
            "object": "invoice",
            "subscription": subscription_id,
            "status": "paid",
        },
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=invoice_paid_payload)
    )

    refreshed_subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()
    trial_notice = db.exec(
        select(BillingNotice).where(
            BillingNotice.user_id == user.id,
            BillingNotice.notice_type == "trial_will_end",
        )
    ).one()

    assert notified_user_id == user.id
    assert refreshed_subscription.status == "active"
    assert refreshed_subscription.latest_invoice_status == "paid"
    assert trial_notice.status == "dismissed"
    assert trial_notice.dismissed_at is not None


def test_process_stripe_webhook_invoice_paid_new_period_rolls_usage_cycle(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
        latest_invoice_id="in_previous",
    )
    previous_cycle = _open_usage_cycle(db=db, subscription=subscription)
    new_period_start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    new_period_end = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

    async def fake_fetch_stripe_subscription(_subscription_id: str) -> dict[str, Any]:
        assert _subscription_id == subscription_id
        return {
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="active",
                latest_invoice_id="in_paid_rollover",
                latest_invoice_status="paid",
            ),
            "current_period_start": int(new_period_start.timestamp()),
            "current_period_end": int(new_period_end.timestamp()),
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_subscription",
        fake_fetch_stripe_subscription,
    )

    invoice_paid_payload = _stripe_event(
        event_type="invoice.paid",
        obj={
            "id": "in_paid_rollover",
            "object": "invoice",
            "subscription": subscription_id,
            "status": "paid",
        },
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=invoice_paid_payload)
    )

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_previous_cycle = db.get(UsageCycle, previous_cycle.id)
    new_cycle = db.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user.id,
            UsageCycle.source_id == subscription.id,
            UsageCycle.period_start == new_period_start,
            UsageCycle.period_end == new_period_end,
        )
    ).one()

    assert notified_user_id == user.id
    assert refreshed_subscription is not None
    assert refreshed_subscription.current_period_start == new_period_start
    assert refreshed_subscription.current_period_end == new_period_end
    assert refreshed_subscription.latest_invoice_id == "in_paid_rollover"
    assert refreshed_subscription.latest_invoice_status == "paid"
    assert refreshed_previous_cycle is not None
    assert refreshed_previous_cycle.status == "closed"
    assert new_cycle.id != previous_cycle.id
    assert new_cycle.status == "open"
    assert new_cycle.plan_code == "base"


def test_process_stripe_webhook_invoice_payment_failed_syncs_past_due_and_clears_paused_notice(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="trialing",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
            latest_invoice_status="paid",
        ),
    )
    asyncio.run(process_stripe_webhook(session=db, payload=created_payload))

    trial_notice_payload = _stripe_event(
        event_type="customer.subscription.trial_will_end",
        obj={
            "id": subscription_id,
            "object": "subscription",
            "subscription": subscription_id,
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=trial_notice_payload))

    paused_payload = _stripe_event(
        event_type="customer.subscription.paused",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="paused",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
        ),
    )
    asyncio.run(process_stripe_webhook(session=db, payload=paused_payload))

    async def fake_fetch_stripe_invoice(_invoice_id: str) -> dict[str, Any]:
        assert _invoice_id == "in_failed"
        return {
            "id": "in_failed",
            "object": "invoice",
            "status": "open",
            "parent": {
                "type": "subscription_details",
                "subscription_details": {
                    "subscription": subscription_id,
                },
            },
        }

    async def fake_fetch_stripe_subscription(_subscription_id: str) -> dict[str, Any]:
        assert _subscription_id == subscription_id
        return {
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="past_due",
                latest_invoice_id="in_failed",
            ),
            "latest_invoice": "in_failed",
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_invoice",
        fake_fetch_stripe_invoice,
    )
    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_subscription",
        fake_fetch_stripe_subscription,
    )

    invoice_failed_payload = _stripe_event(
        event_type="invoice.payment_failed",
        obj={
            "id": "in_failed",
            "object": "invoice",
            "status": "open",
        },
    )
    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=invoice_failed_payload)
    )

    refreshed_subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()
    notices = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).all()
    paused_notice = next(
        notice for notice in notices if notice.notice_type == "subscription_paused"
    )
    trial_notice = next(
        notice for notice in notices if notice.notice_type == "trial_will_end"
    )

    assert notified_user_id == user.id
    assert refreshed_subscription.status == "past_due"
    assert refreshed_subscription.latest_invoice_status == "open"
    assert paused_notice.status == "dismissed"
    assert trial_notice.status == "dismissed"


def test_process_stripe_webhook_invoice_payment_failed_does_not_auto_dismiss_trial_notice(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    now = datetime.now(UTC)
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id="in_trial",
                latest_invoice_status="paid",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=created_payload))

    trial_notice_payload = _stripe_event(
        event_type="customer.subscription.trial_will_end",
        obj={
            "id": subscription_id,
            "object": "subscription",
            "subscription": subscription_id,
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=trial_notice_payload))

    async def fake_fetch_stripe_invoice(_invoice_id: str) -> dict[str, Any]:
        assert _invoice_id == "in_failed"
        return {
            "id": "in_failed",
            "object": "invoice",
            "status": "open",
            "parent": {
                "type": "subscription_details",
                "subscription_details": {
                    "subscription": subscription_id,
                },
            },
        }

    async def fake_fetch_stripe_subscription(_subscription_id: str) -> dict[str, Any]:
        assert _subscription_id == subscription_id
        return {
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="past_due",
                latest_invoice_id="in_failed",
                latest_invoice_status="open",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int(now.timestamp()),
            "latest_invoice": "in_failed",
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_invoice",
        fake_fetch_stripe_invoice,
    )
    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_subscription",
        fake_fetch_stripe_subscription,
    )

    invoice_failed_payload = _stripe_event(
        event_type="invoice.payment_failed",
        obj={
            "id": "in_failed",
            "object": "invoice",
            "status": "open",
        },
    )
    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=invoice_failed_payload)
    )

    refreshed_subscription = db.exec(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    ).one()
    trial_notice = db.exec(
        select(BillingNotice).where(
            BillingNotice.user_id == user.id,
            BillingNotice.notice_type == "trial_will_end",
        )
    ).one()

    assert notified_user_id == user.id
    assert refreshed_subscription.status == "past_due"
    assert refreshed_subscription.latest_invoice_status == "open"
    assert trial_notice.status == "unread"


def test_process_stripe_webhook_customer_subscription_updated_to_active_dismisses_trial_notice(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    now = datetime.now(UTC)
    created_payload = _stripe_event(
        event_type="customer.subscription.created",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="trialing",
                latest_invoice_id="in_trial",
                latest_invoice_status="paid",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=created_payload))

    trial_notice_payload = _stripe_event(
        event_type="customer.subscription.trial_will_end",
        obj={
            "id": subscription_id,
            "object": "subscription",
            "subscription": subscription_id,
            "trial_end": int((now + timedelta(days=7)).timestamp()),
        },
    )
    asyncio.run(process_stripe_webhook(session=db, payload=trial_notice_payload))

    updated_payload = _stripe_event(
        event_type="customer.subscription.updated",
        obj={
            **_subscription_payload(
                subscription_id=subscription_id,
                customer_id=customer_id,
                user_id=user.id,
                status="active",
                latest_invoice_id="in_paid",
                latest_invoice_status="paid",
            ),
            "trial_start": int(now.timestamp()),
            "trial_end": int(now.timestamp()),
        },
    )

    notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=updated_payload)
    )

    trial_notice = db.exec(
        select(BillingNotice).where(
            BillingNotice.user_id == user.id,
            BillingNotice.notice_type == "trial_will_end",
        )
    ).one()

    assert notified_user_id == user.id
    assert trial_notice.status == "dismissed"
    assert trial_notice.dismissed_at is not None


def test_process_stripe_webhook_refund_created_resolves_invoice_from_charge_and_revokes_access(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    invoice_id = f"in_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=f"sub_{uuid.uuid4().hex}",
        stripe_customer_id=f"cus_{uuid.uuid4().hex}",
        latest_invoice_id=invoice_id,
    )
    cycle = _open_usage_cycle(db=db, subscription=subscription)

    async def fake_fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
        assert charge_id == "ch_refund_full"
        return {
            "id": "ch_refund_full",
            "object": "charge",
            "invoice": invoice_id,
            "amount": 1000,
            "amount_refunded": 1000,
            "refunded": True,
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_charge",
        fake_fetch_stripe_charge,
    )

    payload = _stripe_event(
        event_type="refund.created",
        obj={
            "id": f"re_{uuid.uuid4().hex}",
            "object": "refund",
            "charge": "ch_refund_full",
            "status": "succeeded",
            "amount": 1000,
        },
    )

    notified_user_id = asyncio.run(process_stripe_webhook(session=db, payload=payload))

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)
    notices = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).all()

    assert notified_user_id == user.id
    assert refreshed_subscription is not None
    assert refreshed_subscription.latest_invoice_status == "refunded"
    assert refreshed_subscription.access_revoked_reason == "refunded"
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "revoked"
    assert len(notices) == 1
    assert notices[0].stripe_invoice_id == invoice_id


def test_process_stripe_webhook_refund_revocation_stays_blocked_after_subscription_updated(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    invoice_id = f"in_{uuid.uuid4().hex}"
    subscription_id = f"sub_{uuid.uuid4().hex}"
    customer_id = f"cus_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
        latest_invoice_id=invoice_id,
    )
    cycle = _open_usage_cycle(db=db, subscription=subscription)

    async def fake_fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
        assert charge_id == "ch_refund_sticky"
        return {
            "id": "ch_refund_sticky",
            "object": "charge",
            "invoice": invoice_id,
            "amount": 1000,
            "amount_refunded": 1000,
            "refunded": True,
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_charge",
        fake_fetch_stripe_charge,
    )

    refund_payload = _stripe_event(
        event_type="refund.updated",
        obj={
            "id": f"re_{uuid.uuid4().hex}",
            "object": "refund",
            "charge": "ch_refund_sticky",
            "status": "succeeded",
            "amount": 1000,
        },
    )
    active_update_payload = _stripe_event(
        event_type="customer.subscription.updated",
        obj=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="active",
            latest_invoice_id=f"in_{uuid.uuid4().hex}",
            latest_invoice_status="paid",
        ),
    )

    first_notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=refund_payload)
    )
    second_notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=active_update_payload)
    )

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)
    snapshot = access_read_service.get_access_snapshot(session=db, user_id=user.id)

    assert first_notified_user_id == user.id
    assert second_notified_user_id == user.id
    assert refreshed_subscription is not None
    assert refreshed_subscription.status == "active"
    assert refreshed_subscription.latest_invoice_status == "refunded"
    assert refreshed_subscription.access_revoked_reason == "refunded"
    assert refreshed_subscription.access_revoked_at is not None
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "revoked"
    assert snapshot.subscription_status == "canceled"
    assert snapshot.access_revoked_reason == "refunded"
    assert snapshot.current_period_end is None
    assert all((feature.remaining or 0) == 0 for feature in snapshot.features)


def test_process_stripe_webhook_refund_created_pending_does_not_revoke_access(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    invoice_id = f"in_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=f"sub_{uuid.uuid4().hex}",
        stripe_customer_id=f"cus_{uuid.uuid4().hex}",
        latest_invoice_id=invoice_id,
    )
    cycle = _open_usage_cycle(db=db, subscription=subscription)

    async def fake_fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
        assert charge_id == "ch_refund_pending"
        return {
            "id": "ch_refund_pending",
            "object": "charge",
            "invoice": invoice_id,
            "amount": 1000,
            "amount_refunded": 0,
            "refunded": False,
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_charge",
        fake_fetch_stripe_charge,
    )

    payload = _stripe_event(
        event_type="refund.created",
        obj={
            "id": f"re_{uuid.uuid4().hex}",
            "object": "refund",
            "charge": "ch_refund_pending",
            "status": "pending",
            "amount": 1000,
        },
    )

    notified_user_id = asyncio.run(process_stripe_webhook(session=db, payload=payload))

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)

    assert notified_user_id is None
    assert refreshed_subscription is not None
    assert refreshed_subscription.access_revoked_reason is None
    assert refreshed_subscription.latest_invoice_status == "paid"
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "open"


def test_process_stripe_webhook_refund_updated_succeeded_revokes_after_pending(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    invoice_id = f"in_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=f"sub_{uuid.uuid4().hex}",
        stripe_customer_id=f"cus_{uuid.uuid4().hex}",
        latest_invoice_id=invoice_id,
    )
    cycle = _open_usage_cycle(db=db, subscription=subscription)
    charge_responses = iter(
        [
            {
                "id": "ch_refund_transition",
                "object": "charge",
                "invoice": invoice_id,
                "amount": 1000,
                "amount_refunded": 0,
                "refunded": False,
            },
            {
                "id": "ch_refund_transition",
                "object": "charge",
                "invoice": invoice_id,
                "amount": 1000,
                "amount_refunded": 1000,
                "refunded": True,
            },
        ]
    )

    async def fake_fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
        assert charge_id == "ch_refund_transition"
        return next(charge_responses)

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_charge",
        fake_fetch_stripe_charge,
    )

    pending_payload = _stripe_event(
        event_type="refund.created",
        obj={
            "id": f"re_{uuid.uuid4().hex}",
            "object": "refund",
            "charge": "ch_refund_transition",
            "status": "pending",
            "amount": 1000,
        },
    )
    succeeded_payload = _stripe_event(
        event_type="refund.updated",
        obj={
            "id": f"re_{uuid.uuid4().hex}",
            "object": "refund",
            "charge": "ch_refund_transition",
            "status": "succeeded",
            "amount": 1000,
        },
    )

    first_notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=pending_payload)
    )
    second_notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=succeeded_payload)
    )

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)

    assert first_notified_user_id is None
    assert second_notified_user_id == user.id
    assert refreshed_subscription is not None
    assert refreshed_subscription.latest_invoice_status == "refunded"
    assert refreshed_subscription.access_revoked_reason == "refunded"
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "revoked"


def test_process_stripe_webhook_refund_failed_is_noop(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    invoice_id = f"in_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=f"sub_{uuid.uuid4().hex}",
        stripe_customer_id=f"cus_{uuid.uuid4().hex}",
        latest_invoice_id=invoice_id,
    )
    cycle = _open_usage_cycle(db=db, subscription=subscription)

    async def fake_fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
        assert charge_id == "ch_refund_failed"
        return {
            "id": "ch_refund_failed",
            "object": "charge",
            "invoice": invoice_id,
            "amount": 1000,
            "amount_refunded": 0,
            "refunded": False,
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_charge",
        fake_fetch_stripe_charge,
    )

    payload = _stripe_event(
        event_type="refund.failed",
        obj={
            "id": f"re_{uuid.uuid4().hex}",
            "object": "refund",
            "charge": "ch_refund_failed",
            "status": "failed",
            "amount": 1000,
        },
    )

    notified_user_id = asyncio.run(process_stripe_webhook(session=db, payload=payload))

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)

    assert notified_user_id is None
    assert refreshed_subscription is not None
    assert refreshed_subscription.access_revoked_reason is None
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "open"


def test_process_stripe_webhook_charge_refunded_remains_compatible_and_idempotent_after_refund_updated(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db=db)
    invoice_id = f"in_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=f"sub_{uuid.uuid4().hex}",
        stripe_customer_id=f"cus_{uuid.uuid4().hex}",
        latest_invoice_id=invoice_id,
    )
    cycle = _open_usage_cycle(db=db, subscription=subscription)

    async def fake_fetch_stripe_charge(charge_id: str) -> dict[str, Any]:
        assert charge_id == "ch_refund_legacy"
        return {
            "id": "ch_refund_legacy",
            "object": "charge",
            "invoice": invoice_id,
            "amount": 1000,
            "amount_refunded": 1000,
            "refunded": True,
        }

    monkeypatch.setattr(
        stripe_client,
        "fetch_stripe_charge",
        fake_fetch_stripe_charge,
    )

    refund_updated_payload = _stripe_event(
        event_type="refund.updated",
        obj={
            "id": f"re_{uuid.uuid4().hex}",
            "object": "refund",
            "charge": "ch_refund_legacy",
            "status": "succeeded",
            "amount": 1000,
        },
    )
    charge_refunded_payload = _stripe_event(
        event_type="charge.refunded",
        obj={
            "id": "ch_refund_legacy",
            "object": "charge",
            "invoice": invoice_id,
            "amount": 1000,
            "amount_refunded": 1000,
            "refunded": True,
        },
    )

    first_notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=refund_updated_payload)
    )
    second_notified_user_id = asyncio.run(
        process_stripe_webhook(session=db, payload=charge_refunded_payload)
    )

    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)
    notices = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).all()

    assert first_notified_user_id == user.id
    assert second_notified_user_id is None
    assert refreshed_subscription is not None
    assert refreshed_subscription.latest_invoice_status == "refunded"
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "revoked"
    assert len(notices) == 1


def test_process_stripe_webhook_charge_refunded_full_refund_revokes_access(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    invoice_id = f"in_{uuid.uuid4().hex}"
    subscription = _create_subscription(
        db=db,
        user_id=user.id,
        stripe_subscription_id=f"sub_{uuid.uuid4().hex}",
        stripe_customer_id=f"cus_{uuid.uuid4().hex}",
        latest_invoice_id=invoice_id,
    )
    cycle = _open_usage_cycle(db=db, subscription=subscription)
    payload = _stripe_event(
        event_type="charge.refunded",
        obj={
            "id": "ch_full_refund_direct",
            "object": "charge",
            "invoice": invoice_id,
            "amount": 2500,
            "amount_refunded": 2500,
            "refunded": True,
        },
    )

    # Act
    notified_user_id = asyncio.run(process_stripe_webhook(session=db, payload=payload))

    # Assert
    refreshed_subscription = db.get(BillingSubscription, subscription.id)
    refreshed_cycle = db.get(UsageCycle, cycle.id)
    notice = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).one()
    assert notified_user_id == user.id
    assert refreshed_subscription is not None
    assert refreshed_subscription.latest_invoice_status == "refunded"
    assert refreshed_subscription.access_revoked_reason == "refunded"
    assert refreshed_cycle is not None
    assert refreshed_cycle.status == "revoked"
    assert notice.notice_type == "access_revoked"
