from __future__ import annotations

from typing import cast

from sqlmodel import Session, select

from ..constants import FEATURE_SEED, PLAN_SEED
from ..models import LuBillingFeature, SubscriptionPlan, SubscriptionPlanFeatureLimit


def seed_billing_catalog(*, session: Session) -> None:
    existing_features = {
        item.code: item for item in session.exec(select(LuBillingFeature)).all()
    }
    for code, name, description in FEATURE_SEED:
        feature = existing_features.get(code)
        if feature is None:
            feature = LuBillingFeature(code=code, name=name, description=description)
            session.add(feature)
            session.flush()
            existing_features[code] = feature
        elif feature.name != name or feature.description != description:
            feature.name = name
            feature.description = description
            session.add(feature)

    existing_plans = {
        item.code: item for item in session.exec(select(SubscriptionPlan)).all()
    }
    for code, payload in PLAN_SEED.items():
        plan = existing_plans.get(code)
        if plan is None:
            plan = SubscriptionPlan(
                code=code,
                name=str(payload["name"]),
                billing_source=str(payload["billing_source"]),
                is_active=True,
            )
            session.add(plan)
            session.flush()
            existing_plans[code] = plan
        else:
            plan.name = str(payload["name"])
            plan.billing_source = str(payload["billing_source"])
            plan.is_active = True
            session.add(plan)

    existing_limits = {
        (item.plan_id, item.feature_id): item
        for item in session.exec(select(SubscriptionPlanFeatureLimit)).all()
    }
    for code, payload in PLAN_SEED.items():
        plan = existing_plans[code]
        limits = cast(dict[str, int], payload["limits"])
        for feature_code, monthly_limit in limits.items():
            feature = existing_features[feature_code]
            limit = existing_limits.get((cast(int, plan.id), cast(int, feature.id)))
            if limit is None:
                limit = SubscriptionPlanFeatureLimit(
                    plan_id=cast(int, plan.id),
                    feature_id=cast(int, feature.id),
                    monthly_limit=monthly_limit,
                    is_unlimited=False,
                )
            else:
                limit.monthly_limit = monthly_limit
                limit.is_unlimited = False
            session.add(limit)
    session.commit()


__all__ = ["seed_billing_catalog"]
