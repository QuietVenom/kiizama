from sqlmodel import Session

from app import crud_users as crud
from app.features.billing.models import BillingSubscription
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


def test_invalid_active_subscription_state_is_cleaned_after_module(
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    db.add(
        BillingSubscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_invalid_period_{user.id}",
            stripe_customer_id=f"cus_invalid_period_{user.id}",
            stripe_price_id="price_base",
            plan_code="base",
            status="active",
            current_period_start=None,
            current_period_end=None,
        )
    )
    db.commit()
