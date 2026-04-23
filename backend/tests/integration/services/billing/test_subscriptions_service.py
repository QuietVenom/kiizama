from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.models import (
    BillingNotice,
    BillingSubscription,
    UsageCycle,
    UserBillingAccount,
)
from app.features.billing.services import notices as notices_service
from app.features.billing.services import subscriptions as subscriptions_service
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
    user_id,
    status: str,
    latest_invoice_id: str,
    latest_invoice_status: str = "paid",
    pause_collection: dict[str, Any] | None = None,
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
        "cancel_at": None,
        "current_period_start": int(now.timestamp()),
        "current_period_end": int((now + timedelta(days=30)).timestamp()),
        "trial_start": None,
        "trial_end": None,
        "canceled_at": None,
        "ended_at": None,
        "pause_collection": pause_collection,
        "cancellation_details": {"reason": None, "comment": None, "feedback": None},
        "items": {"data": [{"price": {"id": "price_base"}}]},
        "latest_invoice": {
            "id": latest_invoice_id,
            "status": latest_invoice_status,
        },
    }


def test_sync_subscription_from_stripe_data_creates_account_and_open_cycle(
    db: Session,
) -> None:
    user = _create_user(db=db)
    payload = _subscription_payload(
        subscription_id=f"sub_{user.id}",
        customer_id=f"cus_{user.id}",
        user_id=user.id,
        status="active",
        latest_invoice_id=f"in_{user.id}",
    )

    result = subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=payload,
    )

    account = db.exec(
        select(UserBillingAccount).where(UserBillingAccount.user_id == user.id)
    ).one()
    cycle = db.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user.id,
            UsageCycle.status == "open",
        )
    ).one()

    assert result.changed is True
    assert account.stripe_customer_id == f"cus_{user.id}"
    assert cycle.source_type == "subscription"


def test_sync_subscription_from_stripe_data_paused_upserts_notice_and_dismisses_trial_notice(
    db: Session,
) -> None:
    user = _create_user(db=db)
    subscription_id = f"sub_{user.id}"
    customer_id = f"cus_{user.id}"
    subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="active",
            latest_invoice_id=f"in_active_{user.id}",
        ),
    )
    notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="trial_will_end",
        notice_key=f"trial:{user.id}",
        stripe_event_id="evt_trial",
        stripe_subscription_id=subscription_id,
        stripe_invoice_id=None,
        title="Trial ending soon",
        message="Trial notice",
        effective_at=None,
        expires_at=None,
    )

    subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="paused",
            latest_invoice_id=f"in_paused_{user.id}",
            latest_invoice_status="open",
            pause_collection={"behavior": "keep_as_draft"},
        ),
    )

    notices = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).all()
    paused_notice = next(
        notice for notice in notices if notice.notice_type == "subscription_paused"
    )
    trial_notice = next(
        notice for notice in notices if notice.notice_type == "trial_will_end"
    )

    assert paused_notice.status == "unread"
    assert trial_notice.status == "dismissed"


def test_sync_subscription_from_stripe_data_missing_id_or_customer_raises_400(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    valid_payload = _subscription_payload(
        subscription_id=f"sub_{user.id}",
        customer_id=f"cus_{user.id}",
        user_id=user.id,
        status="active",
        latest_invoice_id=f"in_{user.id}",
    )

    # Act / Assert
    for field, expected_detail in (
        ("id", "Stripe subscription payload is missing an id."),
        ("customer", "Stripe subscription payload is missing a customer id."),
    ):
        payload = valid_payload | {field: ""}
        with pytest.raises(HTTPException) as exc_info:
            subscriptions_service.sync_subscription_from_stripe_data(
                session=db,
                subscription_data=payload,
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == expected_detail


def test_sync_subscription_from_stripe_data_resolves_user_from_existing_account(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    customer_id = f"cus_{user.id}"
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id=customer_id))
    db.commit()
    payload = _subscription_payload(
        subscription_id=f"sub_{user.id}",
        customer_id=customer_id,
        user_id="not-a-uuid",
        status="active",
        latest_invoice_id=f"in_{user.id}",
    )

    # Act
    result = subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=payload,
    )

    # Assert
    assert result.subscription.user_id == user.id
    assert result.changed is True


def test_sync_subscription_from_stripe_data_invalid_metadata_user_id_raises_value_error(
    db: Session,
) -> None:
    # Arrange
    payload = _subscription_payload(
        subscription_id="sub_invalid_metadata",
        customer_id="cus_invalid_metadata",
        user_id="not-a-uuid",
        status="active",
        latest_invoice_id="in_invalid_metadata",
    )

    # Act / Assert
    with pytest.raises(ValueError):
        subscriptions_service.sync_subscription_from_stripe_data(
            session=db,
            subscription_data=payload,
        )


def test_sync_subscription_from_stripe_data_latest_invoice_string_sets_invoice_id(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    payload = _subscription_payload(
        subscription_id=f"sub_invoice_string_{user.id}",
        customer_id=f"cus_invoice_string_{user.id}",
        user_id=user.id,
        status="active",
        latest_invoice_id="unused",
    )
    payload["latest_invoice"] = "in_string"

    # Act
    result = subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=payload,
    )

    # Assert
    assert result.subscription.latest_invoice_id == "in_string"
    assert result.subscription.latest_invoice_status is None


def test_sync_subscription_from_stripe_data_inactive_status_closes_open_cycles(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    subscription_id = f"sub_inactive_{user.id}"
    customer_id = f"cus_inactive_{user.id}"
    subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="active",
            latest_invoice_id=f"in_active_{user.id}",
        ),
    )
    open_cycle = db.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user.id,
            UsageCycle.status == "open",
        )
    ).one()

    # Act
    result = subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=_subscription_payload(
            subscription_id=subscription_id,
            customer_id=customer_id,
            user_id=user.id,
            status="canceled",
            latest_invoice_id=f"in_canceled_{user.id}",
        ),
    )

    # Assert
    db.refresh(open_cycle)
    assert result.subscription.status == "canceled"
    assert open_cycle.status == "closed"


def test_sync_subscription_from_stripe_data_sticky_refund_does_not_restore_access(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_refunded_{user.id}",
        stripe_customer_id=f"cus_refunded_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        latest_invoice_id=f"in_refunded_{user.id}",
        latest_invoice_status="refunded",
        access_revoked_at=now,
        access_revoked_reason="refunded",
    )
    db.add(subscription)
    db.add(
        UsageCycle(
            user_id=user.id,
            source_type="subscription",
            source_id=subscription.id,
            plan_code="base",
            period_start=now,
            period_end=now + timedelta(days=30),
            status="open",
        )
    )
    db.commit()

    # Act
    result = subscriptions_service.sync_subscription_from_stripe_data(
        session=db,
        subscription_data=_subscription_payload(
            subscription_id=subscription.stripe_subscription_id,
            customer_id=subscription.stripe_customer_id,
            user_id=user.id,
            status="active",
            latest_invoice_id=f"in_paid_{user.id}",
            latest_invoice_status="paid",
        ),
    )

    # Assert
    cycle = db.exec(select(UsageCycle).where(UsageCycle.user_id == user.id)).one()
    assert result.subscription.access_revoked_reason == "refunded"
    assert result.subscription.latest_invoice_status == "refunded"
    assert cycle.status == "closed"


def test_subscription_stripe_payload_extractors_support_nested_shapes() -> None:
    # Arrange
    parent_invoice = {
        "object": "invoice",
        "parent": {
            "subscription_details": {
                "subscription": "sub_parent",
            }
        },
    }
    line_invoice = {
        "object": "invoice",
        "lines": {
            "data": [
                {"parent": {"other": {}}},
                {
                    "parent": {
                        "subscription_item_details": {
                            "subscription": "sub_line",
                        }
                    }
                },
            ]
        },
    }

    # Act / Assert
    assert (
        subscriptions_service._extract_subscription_id(
            {"subscription": {"id": "sub_dict"}}
        )
        == "sub_dict"
    )
    assert (
        subscriptions_service._extract_subscription_id(parent_invoice) == "sub_parent"
    )
    assert subscriptions_service._extract_subscription_id(line_invoice) == "sub_line"
    assert (
        subscriptions_service._extract_subscription_id(
            {"id": "sub_object", "object": "subscription"}
        )
        == "sub_object"
    )
    assert subscriptions_service._extract_charge_id({"charge": {"id": "ch_dict"}}) == (
        "ch_dict"
    )
    assert (
        subscriptions_service._extract_charge_id(
            {"id": "ch_object", "object": "charge"}
        )
        == "ch_object"
    )
    assert subscriptions_service._extract_invoice_id(
        {"invoice": {"id": "in_dict"}}
    ) == ("in_dict")
    assert (
        subscriptions_service._extract_invoice_id({"charge": {"invoice": "in_charge"}})
        == "in_charge"
    )
    assert subscriptions_service._extract_price_id({"items": {"data": []}}) is None
    assert (
        subscriptions_service._extract_price_id({"items": {"data": [{"price": None}]}})
        is None
    )
    assert (
        subscriptions_service._extract_latest_invoice_id({"latest_invoice": {"id": ""}})
        is None
    )
    assert (
        subscriptions_service._extract_cancellation_reason(
            {"cancellation_details": {"reason": "  customer_service  "}}
        )
        == "customer_service"
    )
    assert (
        subscriptions_service._extract_cancellation_reason(
            {"cancellation_details": {"reason": "  "}}
        )
        is None
    )
    assert (
        subscriptions_service._extract_cancellation_reason(
            {"cancellation_details": {"reason": 123}}
        )
        is None
    )
    assert subscriptions_service._timestamp_to_datetime("not-a-timestamp") is None
