from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from sqlmodel import Session, select

from ..constants import BASE_PLAN_CODE, TRIAL_PLAN_CODE, public_feature_code
from ..models import (
    LuBillingFeature,
    SubscriptionPlan,
    SubscriptionPlanFeatureLimit,
    UsageCycle,
    UsageCycleFeature,
    utcnow,
)
from ..schemas import BillingFeatureUsagePublic

UtcNowCallable = Callable[[], datetime]


def ensure_managed_cycle_feature_rows(
    *,
    session: Session,
    usage_cycle: UsageCycle,
    utcnow_fn: UtcNowCallable = utcnow,
) -> None:
    existing = {
        item.feature_code: item
        for item in session.exec(
            select(UsageCycleFeature).where(
                UsageCycleFeature.usage_cycle_id == usage_cycle.id
            )
        ).all()
    }
    now = utcnow_fn()
    for feature_code in get_feature_name_map(session=session):
        item = existing.get(feature_code)
        if item is None:
            item = UsageCycleFeature(
                usage_cycle_id=usage_cycle.id,
                feature_code=feature_code,
                limit_count=0,
                used_count=0,
                reserved_count=0,
                is_unlimited=True,
            )
        else:
            item.limit_count = 0
            item.is_unlimited = True
            item.updated_at = now
        session.add(item)


def build_cycle_feature_usage(
    *,
    session: Session,
    cycle: UsageCycle,
) -> list[BillingFeatureUsagePublic]:
    feature_names = get_feature_name_map(session=session)
    rows = session.exec(
        select(UsageCycleFeature).where(UsageCycleFeature.usage_cycle_id == cycle.id)
    ).all()
    usage_by_code = {row.feature_code: row for row in rows}
    result: list[BillingFeatureUsagePublic] = []
    for code, name in feature_names.items():
        row = usage_by_code.get(code)
        if row is None:
            result.append(
                BillingFeatureUsagePublic(
                    code=public_feature_code(code),
                    name=name,
                    limit=0,
                    used=0,
                    reserved=0,
                    remaining=0,
                    is_unlimited=False,
                )
            )
            continue
        remaining = (
            None
            if row.is_unlimited
            else max(0, row.limit_count - row.used_count - row.reserved_count)
        )
        result.append(
            BillingFeatureUsagePublic(
                code=public_feature_code(code),
                name=name,
                limit=None if row.is_unlimited else row.limit_count,
                used=row.used_count,
                reserved=row.reserved_count,
                remaining=remaining,
                is_unlimited=row.is_unlimited,
            )
        )
    return result


def build_unlimited_feature_usage(
    *,
    session: Session,
) -> list[BillingFeatureUsagePublic]:
    return [
        BillingFeatureUsagePublic(
            code=public_feature_code(code),
            name=name,
            limit=None,
            used=0,
            reserved=0,
            remaining=None,
            is_unlimited=True,
        )
        for code, name in get_feature_name_map(session=session).items()
    ]


def build_zero_feature_usage(
    *,
    session: Session,
) -> list[BillingFeatureUsagePublic]:
    return [
        BillingFeatureUsagePublic(
            code=public_feature_code(code),
            name=name,
            limit=0,
            used=0,
            reserved=0,
            remaining=0,
            is_unlimited=False,
        )
        for code, name in get_feature_name_map(session=session).items()
    ]


def build_blocked_feature_usage(
    *,
    session: Session,
    plan_code: str | None,
) -> list[BillingFeatureUsagePublic]:
    if plan_code not in {TRIAL_PLAN_CODE, BASE_PLAN_CODE}:
        return build_zero_feature_usage(session=session)
    limits = get_plan_limits(session=session, plan_code=plan_code)
    feature_names = get_feature_name_map(session=session)
    return [
        BillingFeatureUsagePublic(
            code=public_feature_code(code),
            name=feature_names[code],
            limit=limit,
            used=0,
            reserved=0,
            remaining=0,
            is_unlimited=False,
        )
        for code, limit in limits.items()
    ]


def get_feature_name_map(*, session: Session) -> dict[str, str]:
    return {
        item.code: item.name for item in session.exec(select(LuBillingFeature)).all()
    }


def get_plan_limits(*, session: Session, plan_code: str) -> dict[str, int]:
    plan = session.exec(
        select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code)
    ).first()
    if plan is None or plan.id is None:
        return {}
    feature_id_column = cast(Any, SubscriptionPlanFeatureLimit.feature_id)
    rows = session.exec(
        select(SubscriptionPlanFeatureLimit, LuBillingFeature)
        .join(LuBillingFeature, cast(Any, LuBillingFeature.id) == feature_id_column)
        .where(SubscriptionPlanFeatureLimit.plan_id == plan.id)
    ).all()
    return {feature.code: limit.monthly_limit for limit, feature in rows}


def ensure_cycle_feature_rows(
    *,
    session: Session,
    usage_cycle: UsageCycle,
    plan_code: str,
    utcnow_fn: UtcNowCallable = utcnow,
) -> None:
    plan = session.exec(
        select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code)
    ).first()
    if plan is None or plan.id is None:
        raise RuntimeError(f"Billing plan {plan_code!r} is not seeded.")

    existing = {
        item.feature_code: item
        for item in session.exec(
            select(UsageCycleFeature).where(
                UsageCycleFeature.usage_cycle_id == usage_cycle.id
            )
        ).all()
    }
    feature_id_column = cast(Any, SubscriptionPlanFeatureLimit.feature_id)
    rows = session.exec(
        select(SubscriptionPlanFeatureLimit, LuBillingFeature)
        .join(LuBillingFeature, cast(Any, LuBillingFeature.id) == feature_id_column)
        .where(SubscriptionPlanFeatureLimit.plan_id == plan.id)
    ).all()
    now = utcnow_fn()
    for limit, feature in rows:
        item = existing.get(feature.code)
        if item is None:
            item = UsageCycleFeature(
                usage_cycle_id=usage_cycle.id,
                feature_code=feature.code,
                limit_count=limit.monthly_limit,
                used_count=0,
                reserved_count=0,
                is_unlimited=limit.is_unlimited,
            )
        else:
            item.limit_count = limit.monthly_limit
            item.is_unlimited = limit.is_unlimited
            item.updated_at = now
        session.add(item)


__all__ = [
    "build_blocked_feature_usage",
    "build_cycle_feature_usage",
    "build_unlimited_feature_usage",
    "build_zero_feature_usage",
    "ensure_cycle_feature_rows",
    "ensure_managed_cycle_feature_rows",
    "get_feature_name_map",
    "get_plan_limits",
]
