import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.models import (
    BillingNotice,
    BillingWebhookEvent,
    UserBillingAccount,
)
from app.features.billing.services import webhooks as webhooks_service
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def _stripe_event(
    *,
    event_type: str,
    obj: dict[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "created": int(datetime.now(UTC).timestamp()),
        "data": {"object": obj},
    }


def test_process_stripe_webhook_invoice_upcoming_creates_notice_without_fetches(
    db: Session,
) -> None:
    user = _create_user(db=db)
    customer_id = f"cus_{user.id}"
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id=customer_id))
    db.commit()
    payload = _stripe_event(
        event_type="invoice.upcoming",
        obj={
            "object": "invoice",
            "id": f"in_{user.id}",
            "customer": customer_id,
            "period_end": int(datetime(2026, 5, 1, tzinfo=UTC).timestamp()),
        },
    )

    notified_user_id = asyncio.run(
        webhooks_service.process_stripe_webhook(
            session=db,
            payload=payload,
        )
    )

    notice = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).one()
    record = db.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == payload["id"]
        )
    ).one()

    assert notified_user_id == user.id
    assert notice.notice_type == "invoice_upcoming"
    assert record.processing_status == "processed"


def test_process_stripe_webhook_invalid_payload_raises_400(db: Session) -> None:
    # Arrange
    payload = {"data": {"object": {"id": "obj_invalid"}}}
    before_count = len(db.exec(select(BillingWebhookEvent)).all())

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            webhooks_service.process_stripe_webhook(
                session=db,
                payload=payload,
            )
        )
    records = db.exec(select(BillingWebhookEvent)).all()
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid Stripe event payload."
    assert len(records) == before_count


def test_process_stripe_webhook_checkout_without_subscription_is_processed_noop(
    db: Session,
) -> None:
    # Arrange
    payload = _stripe_event(
        event_type="checkout.session.completed",
        event_id="evt_checkout_no_subscription",
        obj={
            "id": "cs_no_subscription",
            "object": "checkout.session",
            "customer": "cus_no_subscription",
        },
    )

    # Act
    result = asyncio.run(
        webhooks_service.process_stripe_webhook(
            session=db,
            payload=payload,
        )
    )

    # Assert
    record = db.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == payload["id"]
        )
    ).one()
    assert result is None
    assert record.processing_status == "processed"
    assert record.stripe_subscription_id is None


def test_process_stripe_webhook_trial_will_end_missing_subscription_is_noop(
    db: Session,
) -> None:
    # Arrange
    before_notice_count = len(db.exec(select(BillingNotice)).all())
    payload = _stripe_event(
        event_type="customer.subscription.trial_will_end",
        event_id="evt_trial_missing_subscription",
        obj={
            "id": "sub_missing",
            "object": "subscription",
            "subscription": "sub_missing",
        },
    )

    # Act
    result = asyncio.run(
        webhooks_service.process_stripe_webhook(
            session=db,
            payload=payload,
        )
    )

    # Assert
    notices = db.exec(select(BillingNotice)).all()
    record = db.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == payload["id"]
        )
    ).one()
    assert result is None
    assert len(notices) == before_notice_count
    assert record.processing_status == "processed"


def test_process_stripe_webhook_returns_none_for_duplicate_event(
    db: Session,
) -> None:
    user = _create_user(db=db)
    customer_id = f"cus_{user.id}"
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id=customer_id))
    db.commit()
    payload = _stripe_event(
        event_type="invoice.upcoming",
        event_id="evt_duplicate",
        obj={"object": "invoice", "id": f"in_{user.id}", "customer": customer_id},
    )

    first = asyncio.run(
        webhooks_service.process_stripe_webhook(
            session=db,
            payload=payload,
        )
    )
    second = asyncio.run(
        webhooks_service.process_stripe_webhook(
            session=db,
            payload=payload,
        )
    )

    records = db.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == payload["id"]
        )
    ).all()

    assert first == user.id
    assert second is None
    assert len(records) == 1


def test_process_stripe_webhook_reprocesses_failed_event(
    db: Session,
    monkeypatch,
) -> None:
    user = _create_user(db=db)
    customer_id = f"cus_{user.id}"
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id=customer_id))
    db.commit()
    payload = _stripe_event(
        event_type="invoice.upcoming",
        event_id="evt_retry_failed",
        obj={"object": "invoice", "id": f"in_{user.id}", "customer": customer_id},
    )

    original_processor = webhooks_service._process_invoice_upcoming_notice

    def fail_once(**_kwargs: Any) -> uuid.UUID | None:
        raise RuntimeError("temporary failure")

    monkeypatch.setattr(
        webhooks_service,
        "_process_invoice_upcoming_notice",
        fail_once,
    )

    with pytest.raises(RuntimeError, match="temporary failure"):
        asyncio.run(
            webhooks_service.process_stripe_webhook(
                session=db,
                payload=payload,
            )
        )

    failed_record = db.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == payload["id"]
        )
    ).one()
    assert failed_record.processing_status == "failed"
    assert failed_record.processing_error == "temporary failure"
    assert failed_record.processed_at is not None

    monkeypatch.setattr(
        webhooks_service,
        "_process_invoice_upcoming_notice",
        original_processor,
    )

    retried_user_id = asyncio.run(
        webhooks_service.process_stripe_webhook(
            session=db,
            payload=payload,
        )
    )

    records = db.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == payload["id"]
        )
    ).all()
    retried_record = records[0]

    assert retried_user_id == user.id
    assert len(records) == 1
    assert retried_record.processing_status == "processed"
    assert retried_record.processing_error is None
    assert retried_record.processed_at is not None


def test_process_stripe_webhook_returns_none_for_pending_event(
    db: Session,
) -> None:
    payload = _stripe_event(
        event_type="invoice.upcoming",
        event_id="evt_pending_duplicate",
        obj={"object": "invoice", "id": "in_pending", "customer": "cus_pending"},
    )
    db.add(
        BillingWebhookEvent(
            stripe_event_id=payload["id"],
            event_type=payload["type"],
            stripe_customer_id="cus_pending",
            stripe_invoice_id="in_pending",
            payload_json=payload,
            processing_status="pending",
        )
    )
    db.commit()

    result = asyncio.run(
        webhooks_service.process_stripe_webhook(
            session=db,
            payload=payload,
        )
    )

    records = db.exec(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.stripe_event_id == payload["id"]
        )
    ).all()

    assert result is None
    assert len(records) == 1
    assert records[0].processing_status == "pending"
