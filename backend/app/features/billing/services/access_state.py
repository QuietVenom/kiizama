from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from sqlmodel import Session, select

from ..constants import AMBASSADOR_OVERRIDE_CODE
from ..models import BillingSubscription, UserAccessOverride, utcnow

if TYPE_CHECKING:
    from app.models import User

UtcNowCallable = Callable[[], datetime]


def has_sticky_refund_revocation(subscription: BillingSubscription | None) -> bool:
    return bool(
        subscription is not None
        and subscription.access_revoked_at is not None
        and subscription.access_revoked_reason == "refunded"
        and subscription.latest_invoice_status == "refunded"
    )


def get_active_access_override(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> UserAccessOverride | None:
    now = utcnow_fn()
    revoked_at_column = cast(Any, UserAccessOverride.revoked_at)
    created_at_column = cast(Any, UserAccessOverride.created_at)
    statement = (
        select(UserAccessOverride)
        .where(
            UserAccessOverride.user_id == user_id,
            UserAccessOverride.code == AMBASSADOR_OVERRIDE_CODE,
            revoked_at_column.is_(None),
            UserAccessOverride.starts_at <= now,
        )
        .order_by(created_at_column.desc())
    )
    candidates = session.exec(statement).all()
    for candidate in candidates:
        if candidate.ends_at is None or candidate.ends_at > now:
            return candidate
    return None


def get_pending_access_override(
    *,
    session: Session,
    user_id: uuid.UUID,
    utcnow_fn: UtcNowCallable = utcnow,
) -> UserAccessOverride | None:
    now = utcnow_fn()
    revoked_at_column = cast(Any, UserAccessOverride.revoked_at)
    starts_at_column = cast(Any, UserAccessOverride.starts_at)
    created_at_column = cast(Any, UserAccessOverride.created_at)
    return session.exec(
        select(UserAccessOverride)
        .where(
            UserAccessOverride.user_id == user_id,
            UserAccessOverride.code == AMBASSADOR_OVERRIDE_CODE,
            revoked_at_column.is_(None),
            UserAccessOverride.starts_at > now,
        )
        .order_by(starts_at_column.asc(), created_at_column.desc())
    ).first()


def get_managed_access_source(
    *,
    user: User | None,
    active_override: UserAccessOverride | None,
) -> str | None:
    if user is not None and user.is_superuser:
        return "admin"
    if active_override is not None:
        return "ambassador"
    return None


def resolve_access_profile(
    *,
    active_override: UserAccessOverride | None,
    pending_override: UserAccessOverride | None,
) -> str:
    if active_override is not None or pending_override is not None:
        return "ambassador"
    return "standard"


__all__ = [
    "get_active_access_override",
    "get_managed_access_source",
    "get_pending_access_override",
    "has_sticky_refund_revocation",
    "resolve_access_profile",
]
