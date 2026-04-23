from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from ..errors import BillingLimitExceededError
from ..models import UsageCycleFeature, UsageEvent, UsageReservation, utcnow
from ..repository import _get_user
from . import access_state as access_state_service
from . import cycle_lifecycle as cycle_lifecycle_service

UtcNowCallable = Callable[[], datetime]


def build_usage_request_key(
    *,
    user_id: uuid.UUID,
    request_scope: str,
    idempotency_key: str | None,
) -> str:
    if idempotency_key and idempotency_key.strip():
        return f"{request_scope}:{user_id}:{idempotency_key.strip()}"
    return f"{request_scope}:{uuid.uuid4()}"


def reserve_feature_usage(
    *,
    session: Session,
    user_id: uuid.UUID,
    feature_code: str,
    endpoint_key: str,
    max_units_requested: int,
    request_key: str,
    job_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    utcnow_fn: UtcNowCallable = utcnow,
) -> UsageReservation | None:
    if max_units_requested <= 0:
        return None

    user = _get_user(session=session, user_id=user_id)
    active_override = access_state_service.get_active_access_override(
        session=session,
        user_id=user_id,
        utcnow_fn=utcnow_fn,
    )
    managed_access_source = access_state_service.get_managed_access_source(
        user=user,
        active_override=active_override,
    )

    existing = session.exec(
        select(UsageReservation).where(UsageReservation.request_key == request_key)
    ).first()
    if existing is not None:
        return existing

    if managed_access_source is not None:
        cycle = cycle_lifecycle_service.ensure_open_managed_usage_cycle(
            session=session,
            user_id=user_id,
            utcnow_fn=utcnow_fn,
        )
    else:
        subscription = cycle_lifecycle_service.ensure_user_is_billable(
            session=session,
            user_id=user_id,
            utcnow_fn=utcnow_fn,
        )
        cycle = cycle_lifecycle_service.ensure_open_usage_cycle_for_subscription(
            session=session,
            subscription=subscription,
            utcnow_fn=utcnow_fn,
        )

    feature_statement = select(UsageCycleFeature).where(
        UsageCycleFeature.usage_cycle_id == cycle.id,
        UsageCycleFeature.feature_code == feature_code,
    )
    feature_statement = feature_statement.with_for_update()
    cycle_feature = session.exec(feature_statement).one()
    if not cycle_feature.is_unlimited:
        remaining = (
            cycle_feature.limit_count
            - cycle_feature.used_count
            - cycle_feature.reserved_count
        )
        if remaining < max_units_requested:
            session.rollback()
            raise BillingLimitExceededError(feature_code)

    cycle_feature.reserved_count += max_units_requested
    cycle_feature.updated_at = utcnow_fn()
    reservation = UsageReservation(
        request_key=request_key,
        user_id=user_id,
        usage_cycle_id=cycle.id,
        feature_code=feature_code,
        endpoint_key=endpoint_key,
        reserved_count=max_units_requested,
        consumed_count=0,
        status="reserved",
        job_id=job_id,
        metadata_json=metadata or {},
    )
    session.add(cycle_feature)
    session.add(reservation)
    session.commit()
    session.refresh(reservation)
    return reservation


def attach_job_id_to_reservation(
    *,
    session: Session,
    request_key: str,
    job_id: str,
) -> None:
    reservation = session.exec(
        select(UsageReservation).where(UsageReservation.request_key == request_key)
    ).first()
    if reservation is None:
        return
    reservation.job_id = job_id
    session.add(reservation)
    session.commit()


def finalize_usage_reservation(
    *,
    session: Session,
    request_key: str | None = None,
    job_id: str | None = None,
    quantity_consumed: int,
    metadata: dict[str, Any] | None = None,
    utcnow_fn: UtcNowCallable = utcnow,
) -> UsageEvent | None:
    reservation = _get_reservation_for_update(
        session=session,
        request_key=request_key,
        job_id=job_id,
    )
    if reservation is None:
        return None
    if reservation.status in {"finalized", "released"}:
        return None

    feature = session.exec(
        select(UsageCycleFeature)
        .where(
            UsageCycleFeature.usage_cycle_id == reservation.usage_cycle_id,
            UsageCycleFeature.feature_code == reservation.feature_code,
        )
        .with_for_update()
    ).one()

    consumed = max(0, min(quantity_consumed, reservation.reserved_count))
    feature.used_count += consumed
    feature.reserved_count = max(0, feature.reserved_count - reservation.reserved_count)
    feature.updated_at = utcnow_fn()

    reservation.consumed_count = consumed
    reservation.status = "finalized" if consumed > 0 else "released"
    reservation.finalized_at = utcnow_fn()
    if metadata:
        reservation.metadata_json = reservation.metadata_json | metadata

    result_status = "success"
    if consumed == 0:
        result_status = "no_charge"
    elif consumed < reservation.reserved_count:
        result_status = "partial_success"

    event = UsageEvent(
        user_id=reservation.user_id,
        usage_cycle_id=reservation.usage_cycle_id,
        feature_code=reservation.feature_code,
        endpoint_key=reservation.endpoint_key,
        request_key=reservation.request_key,
        job_id=reservation.job_id,
        quantity_requested=reservation.reserved_count,
        quantity_consumed=consumed,
        result_status=result_status,
        metadata_json=metadata or reservation.metadata_json,
    )
    session.add(feature)
    session.add(reservation)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def release_usage_reservation(
    *,
    session: Session,
    request_key: str | None = None,
    job_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    utcnow_fn: UtcNowCallable = utcnow,
) -> UsageEvent | None:
    return finalize_usage_reservation(
        session=session,
        request_key=request_key,
        job_id=job_id,
        quantity_consumed=0,
        metadata=metadata,
        utcnow_fn=utcnow_fn,
    )


def _get_reservation_for_update(
    *,
    session: Session,
    request_key: str | None,
    job_id: str | None,
) -> UsageReservation | None:
    if request_key:
        statement = (
            select(UsageReservation)
            .where(UsageReservation.request_key == request_key)
            .with_for_update()
        )
        reservation = session.exec(statement).first()
        if reservation is not None:
            return reservation
    if job_id:
        statement = (
            select(UsageReservation)
            .where(UsageReservation.job_id == job_id)
            .with_for_update()
        )
        return session.exec(statement).first()
    return None


__all__ = [
    "attach_job_id_to_reservation",
    "build_usage_request_key",
    "finalize_usage_reservation",
    "release_usage_reservation",
    "reserve_feature_usage",
]
