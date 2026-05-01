from datetime import UTC, datetime, timedelta
from typing import cast

from sqlmodel import Session, select

from app import crud_users as crud
from app.features.billing.models import (
    BillingCustomerSyncTask,
    BillingNotice,
    BillingSubscription,
    BillingWebhookEvent,
    LuBillingFeature,
    SubscriptionPlan,
    SubscriptionPlanFeatureLimit,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
    UserAccessOverride,
    UserBillingAccount,
)
from app.features.billing.repository import (
    build_user_billing_cleanup_context,
    delete_user_billing_cleanup_context,
)
from app.features.billing.services.catalog import seed_billing_catalog
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def _create_user(*, db: Session):
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )


def test_seed_billing_catalog_twice_keeps_plan_limits_idempotent(
    db: Session,
) -> None:
    # Arrange / Act
    seed_billing_catalog(session=db)
    first_feature_count = len(db.exec(select(LuBillingFeature)).all())
    first_plan_count = len(db.exec(select(SubscriptionPlan)).all())
    first_limit_count = len(db.exec(select(SubscriptionPlanFeatureLimit)).all())

    seed_billing_catalog(session=db)

    # Assert
    assert len(db.exec(select(LuBillingFeature)).all()) == first_feature_count
    assert len(db.exec(select(SubscriptionPlan)).all()) == first_plan_count
    assert len(db.exec(select(SubscriptionPlanFeatureLimit)).all()) == first_limit_count
    assert first_feature_count > 0
    assert first_plan_count > 0
    assert first_limit_count > 0


def test_billing_cleanup_context_collects_and_deletes_user_billing_graph(
    db: Session,
) -> None:
    # Arrange
    user = _create_user(db=db)
    other_user = _create_user(db=db)
    now = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)

    feature = LuBillingFeature(
        code=f"feature-{user.id}",
        name="Feature",
        description="Feature description",
    )
    plan = SubscriptionPlan(
        code=f"p{str(user.id)[:12]}",
        name="Plan",
        billing_source="stripe",
    )
    db.add(feature)
    db.add(plan)
    db.flush()

    limit = SubscriptionPlanFeatureLimit(
        plan_id=cast(int, plan.id),
        feature_id=cast(int, feature.id),
        monthly_limit=10,
    )
    account = UserBillingAccount(
        user_id=user.id,
        stripe_customer_id=f"cus_{user.id}",
    )
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    cycle = UsageCycle(
        user_id=user.id,
        source_type="subscription",
        source_id=subscription.id,
        plan_code="base",
        period_start=now,
        period_end=now + timedelta(days=30),
    )
    db.add_all([limit, account, subscription, cycle])
    db.flush()

    cycle_feature = UsageCycleFeature(
        usage_cycle_id=cycle.id,
        feature_code="ig_scraper_apify",
        limit_count=10,
        used_count=1,
        reserved_count=2,
    )
    reservation = UsageReservation(
        request_key=f"reservation:{user.id}",
        user_id=user.id,
        usage_cycle_id=cycle.id,
        feature_code="ig_scraper_apify",
        endpoint_key="ig_scraper_apify",
        reserved_count=2,
    )
    event = UsageEvent(
        user_id=user.id,
        usage_cycle_id=cycle.id,
        feature_code="ig_scraper_apify",
        endpoint_key="ig_scraper_apify",
        request_key=f"event:{user.id}",
        quantity_requested=2,
        quantity_consumed=1,
    )
    override = UserAccessOverride(
        user_id=user.id,
        code="ambassador",
        is_unlimited=True,
    )
    created_override = UserAccessOverride(
        user_id=other_user.id,
        code="manual",
        is_unlimited=True,
        created_by_admin_id=user.id,
    )
    notice = BillingNotice(
        user_id=user.id,
        notice_type="invoice_upcoming",
        notice_key=f"notice:{user.id}",
        title="Invoice upcoming",
        message="Your invoice is upcoming.",
    )
    sync_task = BillingCustomerSyncTask(
        user_id=user.id,
        stripe_customer_id=f"cus_{user.id}",
        desired_email=user.email,
    )
    webhook_event = BillingWebhookEvent(
        stripe_event_id=f"evt_{user.id}",
        event_type="invoice.upcoming",
        stripe_customer_id=f"cus_{user.id}",
        stripe_subscription_id=f"sub_{user.id}",
        payload_json={"id": f"evt_{user.id}"},
    )
    db.add_all(
        [
            cycle_feature,
            reservation,
            event,
            override,
            created_override,
            notice,
            sync_task,
            webhook_event,
        ]
    )
    db.commit()

    # Act
    context = build_user_billing_cleanup_context(session=db, user_id=user.id)
    delete_user_billing_cleanup_context(session=db, context=context)
    db.commit()

    # Assert
    assert context.account is not None
    assert len(context.subscriptions) == 1
    assert len(context.reservations) == 1
    assert len(context.usage_events) == 1
    assert len(context.cycles) == 1
    assert len(context.cycle_features) == 1
    assert len(context.overrides) == 1
    assert len(context.created_overrides) == 1
    assert len(context.notices) == 1
    assert len(context.customer_sync_tasks) == 1
    assert len(context.webhook_events) == 1
    assert db.get(UserBillingAccount, account.id) is None
    assert db.get(BillingSubscription, subscription.id) is None
    assert db.get(UsageCycle, cycle.id) is None
    assert db.get(UsageCycleFeature, cycle_feature.id) is None
    assert db.get(UsageReservation, reservation.id) is None
    assert db.get(UsageEvent, event.id) is None
    assert db.get(UserAccessOverride, override.id) is None
    assert db.get(BillingNotice, notice.id) is None
    assert db.get(BillingCustomerSyncTask, sync_task.id) is None
    assert db.get(BillingWebhookEvent, webhook_event.id) is None

    db.refresh(created_override)
    assert created_override.created_by_admin_id is None
