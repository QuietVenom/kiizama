from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud_users as crud
from app.core.config import settings
from app.features.billing import set_access_profile
from app.features.billing.models import BillingSubscription, UserBillingAccount
from app.models import UserCreate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_password


def test_read_billing_me_for_standard_user_without_subscription(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/billing/me",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_profile"] == "standard"
    assert payload["billing_eligible"] is True
    assert payload["plan_status"] == "none"
    assert payload["subscription_status"] is None
    assert payload["trial_eligible"] is True
    assert len(payload["features"]) == 3
    assert any(feature["code"] == "ig_scraper" for feature in payload["features"])
    assert all(feature["code"] != "ig_scraper_apify" for feature in payload["features"])
    assert all(feature["remaining"] == 0 for feature in payload["features"])


def test_read_billing_me_for_ambassador_user(
    client: TestClient,
    db: Session,
) -> None:
    email = random_email()
    password = random_password()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    set_access_profile(session=db, user_id=user.id, access_profile="ambassador")
    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.get(f"{settings.API_V1_STR}/billing/me", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_profile"] == "ambassador"
    assert payload["managed_access_source"] == "ambassador"
    assert payload["billing_eligible"] is False
    assert payload["trial_eligible"] is False
    assert payload["plan_status"] == "ambassador"
    assert payload["subscription_status"] is None
    assert all(feature["is_unlimited"] is True for feature in payload["features"])


def test_read_billing_me_for_superuser_returns_admin_managed_access(
    client: TestClient,
    db: Session,
) -> None:
    email = random_email()
    password = random_password()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    user.is_superuser = True
    db.add(user)
    db.commit()
    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.get(f"{settings.API_V1_STR}/billing/me", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_profile"] == "standard"
    assert payload["managed_access_source"] == "admin"
    assert payload["billing_eligible"] is False
    assert payload["trial_eligible"] is False
    assert payload["plan_status"] == "none"
    assert payload["subscription_status"] is None
    assert all(feature["is_unlimited"] is True for feature in payload["features"])


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        (
            "/checkout-session",
            "This user is managed internally and cannot use Stripe billing.",
        ),
        (
            "/portal-session",
            "This user is managed internally and cannot use Stripe billing.",
        ),
    ],
)
def test_superuser_cannot_access_stripe_billing_sessions(
    client: TestClient,
    db: Session,
    path: str,
    expected_detail: str,
) -> None:
    email = random_email()
    password = random_password()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    user.is_superuser = True
    db.add(user)
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id=f"cus_{user.id}"))
    db.commit()
    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.post(f"{settings.API_V1_STR}/billing{path}", headers=headers)

    assert response.status_code == 402
    assert response.json()["detail"] == expected_detail


def test_read_billing_me_returns_scheduled_cancellation_date(
    client: TestClient,
    db: Session,
) -> None:
    email = random_email()
    password = random_password()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    now = datetime.now(timezone.utc)
    cancel_at = now + timedelta(days=7)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="trialing",
        cancel_at=cancel_at,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(subscription)
    db.commit()

    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.get(f"{settings.API_V1_STR}/billing/me", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["subscription_status"] == "trialing"
    assert payload["cancel_at"] is not None
    assert (
        datetime.fromisoformat(payload["cancel_at"].replace("Z", "+00:00")) == cancel_at
    )


def test_read_billing_me_refunded_subscription_looks_canceled_and_blocked(
    client: TestClient,
    db: Session,
) -> None:
    email = random_email()
    password = random_password()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    now = datetime.now(timezone.utc)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        latest_invoice_id=f"in_{user.id}",
        latest_invoice_status="refunded",
        access_revoked_at=now,
        access_revoked_reason="refunded",
    )
    db.add(subscription)
    db.commit()

    headers = user_authentication_headers(client=client, email=email, password=password)

    response = client.get(f"{settings.API_V1_STR}/billing/me", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_status"] == "base"
    assert payload["subscription_status"] == "canceled"
    assert payload["latest_invoice_status"] == "refunded"
    assert payload["access_revoked_reason"] == "refunded"
    assert payload["cancel_at"] is None
    assert payload["current_period_end"] is None
    assert all(feature["remaining"] == 0 for feature in payload["features"])
