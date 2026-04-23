from sqlmodel import Session, select

from app.core.db import init_db, ping_postgres
from app.features.billing.models import LuBillingFeature, SubscriptionPlan
from app.models import LuAdminRole, User


def test_ping_postgres_real_test_database_succeeds() -> None:
    ping_postgres()


def test_init_db_real_test_database_is_idempotent_and_seeds_core_records(
    db: Session,
) -> None:
    init_db(db)
    init_db(db)

    superuser = db.exec(select(User).where(User.is_superuser)).first()
    admin_roles = db.exec(select(LuAdminRole)).all()
    billing_features = db.exec(select(LuBillingFeature)).all()
    subscription_plans = db.exec(select(SubscriptionPlan)).all()

    assert superuser is not None
    assert {role.code for role in admin_roles} >= {
        "platform_owner",
        "ops",
        "viewer",
        "system",
    }
    assert {feature.code for feature in billing_features} >= {
        "social_media_report",
        "reputation_strategy",
        "ig_scraper_apify",
    }
    assert subscription_plans
