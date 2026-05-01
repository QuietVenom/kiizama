from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.models import BillingNotice
from app.features.billing.services import notices as notices_service
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def test_upsert_billing_notice_existing_unread_updates_notice_fields(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    notice = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="invoice_upcoming",
        notice_key="notice-key",
        stripe_event_id="evt_initial",
        stripe_subscription_id="sub_initial",
        stripe_invoice_id="in_initial",
        title="Initial",
        message="Initial message",
        effective_at=now,
        expires_at=now + timedelta(days=1),
        utcnow_fn=lambda: now,
    )

    # Act
    updated = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="invoice_upcoming",
        notice_key="notice-key",
        stripe_event_id="evt_updated",
        stripe_subscription_id="sub_updated",
        stripe_invoice_id="in_updated",
        title="Updated",
        message="Updated message",
        effective_at=now + timedelta(days=2),
        expires_at=now + timedelta(days=3),
        utcnow_fn=lambda: now + timedelta(minutes=5),
    )

    # Assert
    notices = db.exec(
        select(BillingNotice).where(BillingNotice.user_id == user.id)
    ).all()
    assert len(notices) == 1
    assert updated.id == notice.id
    assert updated.title == "Updated"
    assert updated.stripe_event_id == "evt_updated"
    assert updated.updated_at == now + timedelta(minutes=5)


def test_upsert_billing_notice_existing_dismissed_keeps_dismissed_content(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    notice = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="trial_will_end",
        notice_key="dismissed-key",
        stripe_event_id="evt_initial",
        stripe_subscription_id="sub_1",
        stripe_invoice_id=None,
        title="Initial",
        message="Initial message",
        effective_at=now,
        expires_at=None,
        utcnow_fn=lambda: now,
    )
    notices_service.mark_billing_notice_status(
        session=db,
        user_id=user.id,
        notice_id=notice.id,
        status_value="dismissed",
        utcnow_fn=lambda: now + timedelta(minutes=1),
    )

    # Act
    updated = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="trial_will_end",
        notice_key="dismissed-key",
        stripe_event_id="evt_updated",
        stripe_subscription_id="sub_1",
        stripe_invoice_id=None,
        title="Updated",
        message="Updated message",
        effective_at=now + timedelta(days=1),
        expires_at=None,
        utcnow_fn=lambda: now + timedelta(minutes=5),
    )

    # Assert
    assert updated.status == "dismissed"
    assert updated.title == "Initial"
    assert updated.stripe_event_id == "evt_initial"
    assert updated.dismissed_at == now + timedelta(minutes=1)


def test_dismiss_billing_notices_filters_by_subscription_and_skips_dismissed(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    matching = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="trial_will_end",
        notice_key="trial:sub_match",
        stripe_event_id="evt_match",
        stripe_subscription_id="sub_match",
        stripe_invoice_id=None,
        title="Trial",
        message="Trial",
        effective_at=None,
        expires_at=None,
        utcnow_fn=lambda: now,
    )
    other_subscription = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="trial_will_end",
        notice_key="trial:sub_other",
        stripe_event_id="evt_other",
        stripe_subscription_id="sub_other",
        stripe_invoice_id=None,
        title="Trial",
        message="Trial",
        effective_at=None,
        expires_at=None,
        utcnow_fn=lambda: now,
    )
    dismissed = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="trial_will_end",
        notice_key="trial:dismissed",
        stripe_event_id="evt_dismissed",
        stripe_subscription_id="sub_match",
        stripe_invoice_id=None,
        title="Trial",
        message="Trial",
        effective_at=None,
        expires_at=None,
        utcnow_fn=lambda: now,
    )
    notices_service.mark_billing_notice_status(
        session=db,
        user_id=user.id,
        notice_id=dismissed.id,
        status_value="dismissed",
        utcnow_fn=lambda: now + timedelta(minutes=1),
    )

    # Act
    notices_service.dismiss_billing_notices(
        session=db,
        user_id=user.id,
        notice_type="trial_will_end",
        stripe_subscription_id="sub_match",
        utcnow_fn=lambda: now + timedelta(minutes=5),
    )

    # Assert
    db.refresh(matching)
    db.refresh(other_subscription)
    db.refresh(dismissed)
    assert matching.status == "dismissed"
    assert matching.dismissed_at == now + timedelta(minutes=5)
    assert other_subscription.status == "unread"
    assert dismissed.dismissed_at == now + timedelta(minutes=1)


def test_mark_billing_notice_status_read_and_dismissed_sets_timestamps(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    now = datetime(2026, 4, 20, 18, 0, tzinfo=UTC)
    notice = notices_service.upsert_billing_notice(
        session=db,
        user_id=user.id,
        notice_type="invoice_upcoming",
        notice_key="status-key",
        stripe_event_id="evt_status",
        stripe_subscription_id=None,
        stripe_invoice_id="in_status",
        title="Upcoming",
        message="Upcoming",
        effective_at=None,
        expires_at=None,
        utcnow_fn=lambda: now,
    )

    # Act
    read_notice = notices_service.mark_billing_notice_status(
        session=db,
        user_id=user.id,
        notice_id=notice.id,
        status_value="read",
        utcnow_fn=lambda: now + timedelta(minutes=1),
    )
    dismissed_notice = notices_service.mark_billing_notice_status(
        session=db,
        user_id=user.id,
        notice_id=notice.id,
        status_value="dismissed",
        utcnow_fn=lambda: now + timedelta(minutes=2),
    )

    # Assert
    refreshed = db.get(BillingNotice, notice.id)
    assert read_notice.status == "read"
    assert dismissed_notice.status == "dismissed"
    assert refreshed is not None
    assert refreshed.read_at == now + timedelta(minutes=1)
    assert refreshed.dismissed_at == now + timedelta(minutes=2)
