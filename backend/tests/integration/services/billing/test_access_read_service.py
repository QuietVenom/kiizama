from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.models import UsageCycle, UserAccessOverride
from app.features.billing.services import access_read as access_read_service
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def test_get_access_snapshot_pending_ambassador_activation_returns_unlimited_features(
    db: Session,
) -> None:
    user = _create_user(db=db)
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    db.add(
        UserAccessOverride(
            user_id=user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=now + timedelta(days=1),
            notes="Pending ambassador",
        )
    )
    db.commit()

    snapshot = access_read_service.get_access_snapshot(
        session=db,
        user_id=user.id,
        utcnow_fn=lambda: now,
    )

    assert snapshot.access_profile == "ambassador"
    assert snapshot.pending_ambassador_activation is True
    assert snapshot.billing_eligible is False
    assert snapshot.managed_access_source is None
    assert snapshot.features
    assert all(feature.is_unlimited for feature in snapshot.features)


def test_get_access_snapshot_for_superuser_opens_managed_cycle(
    db: Session,
) -> None:
    user = _create_user(db=db)
    user.is_superuser = True
    db.add(user)
    db.commit()

    now = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    snapshot = access_read_service.get_access_snapshot(
        session=db,
        user_id=user.id,
        utcnow_fn=lambda: now,
    )

    managed_cycle = db.exec(
        select(UsageCycle).where(
            UsageCycle.user_id == user.id,
            UsageCycle.source_type == "managed",
            UsageCycle.status == "open",
        )
    ).one()

    assert snapshot.managed_access_source == "admin"
    assert snapshot.current_period_start == datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    assert snapshot.current_period_end == datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    assert managed_cycle.period_start == snapshot.current_period_start
    assert all(feature.is_unlimited for feature in snapshot.features)
