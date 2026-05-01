import uuid
from datetime import UTC, datetime

from app.features.billing.models import UserBillingAccount


def billing_account(
    *, user_id: uuid.UUID, stripe_customer_id: str
) -> UserBillingAccount:
    return UserBillingAccount(
        user_id=user_id,
        stripe_customer_id=stripe_customer_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
