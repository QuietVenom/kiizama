import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud_users as crud
from app.core.config import settings
from app.core.redis import create_redis_client
from app.core.security import verify_password
from app.features.account_cleanup.services import user_cleanup as user_cleanup_service
from app.features.billing.models import (
    BillingCustomerSyncTask,
    BillingSubscription,
    UserAccessOverride,
    UserBillingAccount,
)
from app.features.billing.services import cleanup as billing_cleanup_service
from app.features.user_events.repository import (
    UserEventsRepository,
    build_user_events_stream_key,
)
from app.features.user_events.schemas import UserEventEnvelope
from app.models import IgScrapeJob, User, UserCreate, UserLegalAcceptance
from tests.fixtures.billing import cleanup_invalid_billing_subscriptions
from tests.utils.utils import random_email, random_lower_string, random_password


def legal_acceptances_payload() -> dict[str, bool]:
    return {
        "privacy_notice": True,
        "terms_conditions": True,
    }


def _create_user_with_headers(
    *,
    client: TestClient,
    db: Session,
) -> tuple[User, dict[str, str]]:
    password = random_password()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=password),
    )
    login_response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": user.email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


def _build_user_event_envelope(notification_id: str) -> UserEventEnvelope:
    return UserEventEnvelope(
        topic="account",
        source="backend",
        kind="account.subscription.updated",
        notification_id=notification_id,
        payload={"status": "active"},
    )


async def _publish_user_event_with_dedicated_redis_client(
    *,
    user_id: uuid.UUID,
    notification_id: str,
) -> None:
    redis_url = settings._resolved_redis_url()
    if redis_url is None:
        raise RuntimeError("REDIS_URL is not configured.")

    redis = create_redis_client(redis_url)
    try:
        repository = UserEventsRepository(redis_provider=lambda: redis)
        await repository.publish_event(
            user_id=str(user_id),
            event_name="account.subscription.updated",
            envelope=_build_user_event_envelope(notification_id),
        )
    finally:
        await redis.aclose()


async def _redis_key_exists(key: str) -> int:
    redis_url = settings._resolved_redis_url()
    if redis_url is None:
        raise RuntimeError("REDIS_URL is not configured.")

    redis = create_redis_client(redis_url)
    try:
        return int(await redis.exists(key))
    finally:
        await redis.aclose()


def _seed_user_cleanup_state(
    *,
    db: Session,
    user: User,
    include_cross_feature_state: bool = False,
) -> UserAccessOverride | None:
    now = datetime.now(UTC)
    db.add(
        BillingSubscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_{user.id}",
            stripe_customer_id=f"cus_{user.id}",
            stripe_price_id="price_base",
            plan_code="base",
            status="active",
            current_period_start=now,
            current_period_end=now,
        )
    )
    db.add(
        UserBillingAccount(
            user_id=user.id,
            stripe_customer_id=f"cus_{user.id}",
        )
    )

    override: UserAccessOverride | None = None
    if include_cross_feature_state:
        bind = db.get_bind()
        cast(Any, IgScrapeJob).__table__.create(bind=bind, checkfirst=True)
        other_user = crud.create_user(
            session=db,
            user_create=UserCreate(email=random_email(), password=random_password()),
        )
        db.add(
            UserLegalAcceptance(
                user_id=user.id,
                document_type="privacy_notice",
                document_version="v1",
                source="public_signup",
            )
        )
        db.add(
            IgScrapeJob(
                owner_user_id=user.id,
                expires_at=now + timedelta(hours=1),
                payload={"usernames": ["alpha"]},
            )
        )
        override = UserAccessOverride(
            user_id=other_user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=now,
            created_by_admin_id=user.id,
            notes="Created by deleted user",
        )
        db.add(override)

    db.commit()
    return override


def test_get_users_superuser_me(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=superuser_token_headers)
    current_user = r.json()
    assert current_user
    assert current_user["is_active"] is True
    assert current_user["is_superuser"]
    assert current_user["email"] == settings.FIRST_SUPERUSER


def test_get_users_normal_user_me(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers)
    current_user = r.json()
    assert current_user
    assert current_user["is_active"] is True
    assert current_user["is_superuser"] is False
    assert current_user["email"] == settings.EMAIL_TEST_USER


def test_create_user_new_email(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    with (
        patch("app.api.routes.users.send_email_best_effort", return_value=None),
        patch("app.core.config.settings.RESEND_API_KEY", "re_test_123"),
    ):
        username = random_email()
        password = random_password()
        data = {"email": username, "password": password}
        r = client.post(
            f"{settings.API_V1_STR}/users/",
            headers=superuser_token_headers,
            json=data,
        )
        assert 200 <= r.status_code < 300
        created_user = r.json()
        user = crud.get_user_by_email(session=db, email=username)
        assert user
        assert user.email == created_user["email"]


def test_create_user_rejects_superuser_ambassador_combination(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json={
            "email": random_email(),
            "password": random_password(),
            "is_superuser": True,
            "access_profile": "ambassador",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Superuser and ambassador are mutually exclusive. Move the user to standard first."
    )


def test_create_user_succeeds_when_email_delivery_fails(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    with patch(
        "app.utils.send_email_or_raise",
        side_effect=RuntimeError("resend down"),
    ):
        response = client.post(
            f"{settings.API_V1_STR}/users/",
            headers=superuser_token_headers,
            json={"email": username, "password": password},
        )

    assert 200 <= response.status_code < 300
    created_user = response.json()
    user = crud.get_user_by_email(session=db, email=username)
    assert user
    assert user.email == created_user["email"]


def test_get_existing_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id
    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert 200 <= r.status_code < 300
    api_user = r.json()
    existing_user = crud.get_user_by_email(session=db, email=username)
    assert existing_user
    assert existing_user.email == api_user["email"]


def test_get_existing_user_current_user(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id

    login_data = {
        "username": username,
        "password": password,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=headers,
    )
    assert 200 <= r.status_code < 300
    api_user = r.json()
    existing_user = crud.get_user_by_email(session=db, email=username)
    assert existing_user
    assert existing_user.email == api_user["email"]


def test_get_existing_user_permissions_error(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json() == {"detail": "The user doesn't have enough privileges"}


def test_create_user_existing_username(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    # username = email
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    crud.create_user(session=db, user_create=user_in)
    data = {"email": username, "password": password}
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=data,
    )
    created_user = r.json()
    assert r.status_code == 400
    assert "_id" not in created_user


def test_create_user_by_normal_user(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    username = random_email()
    password = random_password()
    data = {"email": username, "password": password}
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 403


def test_retrieve_users(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    crud.create_user(session=db, user_create=user_in)

    username2 = random_email()
    password2 = random_password()
    user_in2 = UserCreate(email=username2, password=password2)
    crud.create_user(session=db, user_create=user_in2)

    r = client.get(f"{settings.API_V1_STR}/users/", headers=superuser_token_headers)

    assert r.status_code == 200
    all_users = r.json()
    assert len(all_users["data"]) > 1
    assert "count" in all_users
    for item in all_users["data"]:
        assert "email" in item


def test_retrieve_users_with_invalid_billing_state_returns_conservative_user_view(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    db.add(
        BillingSubscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_invalid_list_{user.id}",
            stripe_customer_id=f"cus_invalid_list_{user.id}",
            stripe_price_id="price_base",
            plan_code="base",
            status="active",
            current_period_start=None,
            current_period_end=None,
        )
    )
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    invalid_user = next(
        item for item in payload["data"] if item["email"] == str(user.email)
    )
    assert invalid_user["billing_eligible"] is False
    assert invalid_user["plan_status"] == "none"
    assert invalid_user["managed_access_source"] is None

    assert cleanup_invalid_billing_subscriptions(session=db) >= 1


def test_retrieve_users_after_invalid_billing_state_cleanup_returns_users(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_invalid_period_{user.id}",
        stripe_customer_id=f"cus_invalid_period_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=None,
        current_period_end=None,
    )
    db.add(subscription)
    db.commit()
    subscription_id = subscription.id

    assert cleanup_invalid_billing_subscriptions(session=db) >= 1
    assert db.get(BillingSubscription, subscription_id) is None

    response = client.get(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert "count" in payload


def test_update_user_promotes_superuser_and_schedules_subscription_cancellation(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    now = datetime.now(UTC)
    subscription = BillingSubscription(
        user_id=user.id,
        stripe_subscription_id=f"sub_{user.id}",
        stripe_customer_id=f"cus_{user.id}",
        stripe_price_id="price_base",
        plan_code="base",
        status="active",
        current_period_start=now - timedelta(days=1),
        current_period_end=now + timedelta(days=29),
    )
    db.add(subscription)
    db.commit()

    with patch(
        "app.features.billing.clients.stripe._stripe_request",
        autospec=True,
        return_value={},
    ) as stripe_request:
        response = client.patch(
            f"{settings.API_V1_STR}/users/{user.id}",
            headers=superuser_token_headers,
            json={"is_superuser": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_superuser"] is True
    assert payload["managed_access_source"] == "admin"

    db.refresh(subscription)
    assert subscription.cancel_at_period_end is True
    stripe_request.assert_called_once()


def test_update_user_rejects_direct_superuser_to_ambassador_transition(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_password(),
            is_superuser=True,
        ),
    )

    response = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json={"is_superuser": False, "access_profile": "ambassador"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Superuser and ambassador are mutually exclusive. Move the user to standard first."
    )


def test_update_user_rejects_superuser_ambassador_combination_from_standard(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )

    response = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json={"is_superuser": True, "access_profile": "ambassador"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Superuser and ambassador are mutually exclusive. Move the user to standard first."
    )


def test_update_user_rejects_direct_ambassador_to_superuser_transition(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    db.add(
        UserAccessOverride(
            user_id=user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=datetime.now(UTC),
            notes="Ambassador access",
        )
    )
    db.commit()

    response = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json={"is_superuser": True, "access_profile": "standard"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Superuser and ambassador are mutually exclusive. Move the user to standard first."
    )


def test_update_user_access_profile_rejects_ambassador_for_superuser(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_password(),
            is_superuser=True,
        ),
    )

    response = client.put(
        f"{settings.API_V1_STR}/users/{user.id}/access-profile",
        headers=superuser_token_headers,
        json={"access_profile": "ambassador"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Superuser and ambassador are mutually exclusive. Move the user to standard first."
    )


def test_update_user_allows_superuser_to_standard_transition(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_password(),
            is_superuser=True,
        ),
    )

    response = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json={"is_superuser": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_superuser"] is False
    assert payload["access_profile"] == "standard"
    assert payload["managed_access_source"] is None


def test_update_user_access_profile_allows_ambassador_to_standard_transition(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    db.add(
        UserAccessOverride(
            user_id=user.id,
            code="ambassador",
            is_unlimited=True,
            starts_at=datetime.now(UTC),
            notes="Ambassador access",
        )
    )
    db.commit()

    response = client.put(
        f"{settings.API_V1_STR}/users/{user.id}/access-profile",
        headers=superuser_token_headers,
        json={"access_profile": "standard"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_superuser"] is False
    assert payload["access_profile"] == "standard"
    assert payload["managed_access_source"] is None


def test_admin_update_user_email_change_enqueues_customer_sync_task(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id="cus_admin_user"))
    db.commit()

    response = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json={"email": "admin-updated@example.com"},
    )

    assert response.status_code == 200
    task = db.exec(
        select(BillingCustomerSyncTask).where(
            BillingCustomerSyncTask.user_id == user.id
        )
    ).one()
    db.refresh(user)
    assert user.email == "admin-updated@example.com"
    assert task.status == "pending"
    assert task.desired_email == "admin-updated@example.com"
    assert task.attempt_count == 0
    assert task.last_stripe_request_id is None


def test_update_user_me(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    full_name = "Updated Name"
    email = random_email()
    data = {"full_name": full_name, "email": email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()
    assert updated_user["email"] == email
    assert updated_user["full_name"] == full_name

    user_query = select(User).where(User.email == email)
    user_db = db.exec(user_query).first()
    assert user_db
    assert user_db.email == email
    assert user_db.full_name == full_name


def test_update_user_me_email_change_enqueues_customer_sync_task(
    client: TestClient,
    db: Session,
) -> None:
    user, headers = _create_user_with_headers(client=client, db=db)
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id="cus_test_user"))
    db.commit()

    response = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
        json={"email": "updated-inline@example.com"},
    )

    assert response.status_code == 200
    task = db.exec(
        select(BillingCustomerSyncTask).where(
            BillingCustomerSyncTask.user_id == user.id
        )
    ).one()
    db.refresh(user)
    assert user.email == "updated-inline@example.com"
    assert task.status == "pending"
    assert task.desired_email == "updated-inline@example.com"
    assert task.attempt_count == 0
    assert task.last_http_status is None
    assert task.last_stripe_request_id is None


def test_update_user_me_email_change_leaves_pending_sync_task(
    client: TestClient,
    db: Session,
) -> None:
    user, headers = _create_user_with_headers(client=client, db=db)
    db.add(UserBillingAccount(user_id=user.id, stripe_customer_id="cus_retry_user"))
    db.commit()

    response = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
        json={"email": "retry-inline@example.com"},
    )

    assert response.status_code == 200
    task = db.exec(
        select(BillingCustomerSyncTask).where(
            BillingCustomerSyncTask.user_id == user.id
        )
    ).one()
    db.refresh(user)
    assert user.email == "retry-inline@example.com"
    assert task.status == "pending"
    assert task.desired_email == "retry-inline@example.com"
    assert task.attempt_count == 0
    assert task.last_http_status is None
    assert task.last_error is None
    assert task.next_attempt_at is not None


def test_update_password_me(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    new_password = random_password()
    data = {
        "current_password": settings.FIRST_SUPERUSER_PASSWORD,
        "new_password": new_password,
    }
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()
    assert updated_user["message"] == "Password updated successfully"

    user_query = select(User).where(User.email == settings.FIRST_SUPERUSER)
    user_db = db.exec(user_query).first()
    assert user_db
    assert user_db.email == settings.FIRST_SUPERUSER
    assert verify_password(new_password, user_db.hashed_password)

    # Revert to the old password to keep consistency in test
    old_data = {
        "current_password": new_password,
        "new_password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=old_data,
    )
    db.refresh(user_db)

    assert r.status_code == 200
    assert verify_password(settings.FIRST_SUPERUSER_PASSWORD, user_db.hashed_password)


def test_update_password_me_incorrect_password(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    new_password = random_password()
    data = {"current_password": new_password, "new_password": new_password}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 400
    updated_user = r.json()
    assert updated_user["detail"] == "Incorrect password"


def test_update_user_me_email_exists(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    data = {"email": user.email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "User with this email already exists"


def test_update_password_me_same_password_error(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {
        "current_password": settings.FIRST_SUPERUSER_PASSWORD,
        "new_password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 400
    updated_user = r.json()
    assert (
        updated_user["detail"] == "New password cannot be the same as the current one"
    )


def test_register_user(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_password()
    full_name = random_lower_string()
    data = {
        "email": username,
        "password": password,
        "full_name": full_name,
        "legal_acceptances": legal_acceptances_payload(),
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )
    assert r.status_code == 200
    created_user = r.json()
    assert created_user["email"] == username
    assert created_user["full_name"] == full_name

    user_query = select(User).where(User.email == username)
    user_db = db.exec(user_query).first()
    assert user_db
    assert user_db.email == username
    assert user_db.full_name == full_name
    assert verify_password(password, user_db.hashed_password)

    acceptances = db.exec(
        select(UserLegalAcceptance).where(UserLegalAcceptance.user_id == user_db.id)
    ).all()
    assert len(acceptances) == 2
    assert {acceptance.document_type for acceptance in acceptances} == {
        "privacy_notice",
        "terms_conditions",
    }
    assert {acceptance.document_version for acceptance in acceptances} == {"v1.0"}
    assert {acceptance.source for acceptance in acceptances} == {"public_signup"}
    assert all(acceptance.accepted_at.tzinfo is not None for acceptance in acceptances)


def test_register_user_rejects_password_without_uppercase(client: TestClient) -> None:
    data = {
        "email": random_email(),
        "password": "lowercase1!",
        "full_name": "Test User",
        "legal_acceptances": legal_acceptances_payload(),
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )

    assert r.status_code == 422
    assert (
        r.json()["detail"][0]["msg"]
        == "Password must include at least 1 uppercase letter"
    )


def test_register_user_rejects_password_over_max_length(client: TestClient) -> None:
    data = {
        "email": random_email(),
        "password": f"Aa1!{'a' * 22}",
        "full_name": "Test User",
        "legal_acceptances": legal_acceptances_payload(),
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )

    assert r.status_code == 422
    assert "at most 25 characters" in r.json()["detail"][0]["msg"]


def test_register_user_already_exists_error(client: TestClient) -> None:
    password = random_password()
    full_name = random_lower_string()
    data = {
        "email": settings.FIRST_SUPERUSER,
        "password": password,
        "full_name": full_name,
        "legal_acceptances": legal_acceptances_payload(),
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "The user with this email already exists in the system"


def test_register_user_requires_legal_acceptances(client: TestClient) -> None:
    data = {
        "email": random_email(),
        "password": random_password(),
        "full_name": "Test User",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )

    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "legal_acceptances"]


def test_register_user_rejects_unchecked_legal_acceptances(client: TestClient) -> None:
    data = {
        "email": random_email(),
        "password": random_password(),
        "full_name": "Test User",
        "legal_acceptances": {
            "privacy_notice": True,
            "terms_conditions": False,
        },
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )

    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == [
        "body",
        "legal_acceptances",
        "terms_conditions",
    ]


def test_update_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    data = {"full_name": "Updated_full_name"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()

    assert updated_user["full_name"] == "Updated_full_name"

    user_query = select(User).where(User.email == username)
    user_db = db.exec(user_query).first()
    db.refresh(user_db)
    assert user_db
    assert user_db.full_name == "Updated_full_name"


def test_update_user_not_exists(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"full_name": "Updated_full_name"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "The user with this id does not exist in the system"


def test_update_user_email_exists(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    username2 = random_email()
    password2 = random_password()
    user_in2 = UserCreate(email=username2, password=password2)
    user2 = crud.create_user(session=db, user_create=user_in2)

    data = {"email": user2.email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "User with this email already exists"


def test_delete_user_me(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id

    login_data = {
        "username": username,
        "password": password,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    r = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
    )
    assert r.status_code == 200
    deleted_user = r.json()
    assert deleted_user["message"] == "User deleted successfully"
    result = db.exec(select(User).where(User.id == user_id)).first()
    assert result is None

    user_query = select(User).where(User.id == user_id)
    user_db = db.execute(user_query).first()
    assert user_db is None


def test_delete_user_me_removes_user_event_stream_after_cleanup_side_effects(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    user, headers = _create_user_with_headers(client=client, db=db)
    stream_key = build_user_events_stream_key(str(user.id))
    asyncio.run(
        _publish_user_event_with_dedicated_redis_client(
            user_id=user.id,
            notification_id="before-delete",
        )
    )
    assert asyncio.run(_redis_key_exists(stream_key)) == 1

    async def publish_during_cleanup(*, session: Session, user_id: uuid.UUID) -> None:
        assert session is not None
        assert user_id == user.id
        await _publish_user_event_with_dedicated_redis_client(
            user_id=user_id,
            notification_id="during-delete",
        )

    monkeypatch.setattr(
        user_cleanup_service,
        "delete_user_billing_state",
        publish_during_cleanup,
    )

    response = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"
    assert db.exec(select(User).where(User.id == user.id)).first() is None
    assert asyncio.run(_redis_key_exists(stream_key)) == 0


def test_delete_user_me_removes_owned_ig_scrape_jobs(
    client: TestClient, db: Session
) -> None:
    bind = db.get_bind()
    cast(Any, IgScrapeJob).__table__.create(bind=bind, checkfirst=True)

    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id
    other_user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )

    job = IgScrapeJob(
        owner_user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        payload={"usernames": ["alpha"]},
    )
    db.add(job)
    db.add(
        UserLegalAcceptance(
            user_id=user.id,
            document_type="privacy_notice",
            document_version="v1",
            source="public_signup",
        )
    )
    override = UserAccessOverride(
        user_id=other_user.id,
        code="ambassador",
        is_unlimited=True,
        starts_at=datetime.now(UTC),
        created_by_admin_id=user.id,
        notes="Created by deleted user",
    )
    db.add(override)
    db.commit()

    login_data = {
        "username": username,
        "password": password,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    r = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["message"] == "User deleted successfully"
    assert db.exec(select(User).where(User.id == user_id)).first() is None
    assert (
        db.exec(select(IgScrapeJob).where(IgScrapeJob.owner_user_id == user_id)).all()
        == []
    )
    assert (
        db.exec(
            select(UserLegalAcceptance).where(UserLegalAcceptance.user_id == user_id)
        ).all()
        == []
    )
    persisted_override = db.get(UserAccessOverride, override.id)
    assert persisted_override is not None
    assert persisted_override.user_id == other_user.id
    assert persisted_override.created_by_admin_id is None


def test_delete_user_me_continues_when_stripe_cleanup_times_out(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    user, headers = _create_user_with_headers(client=client, db=db)
    override = _seed_user_cleanup_state(
        db=db,
        user=user,
        include_cross_feature_state=True,
    )
    assert override is not None

    async def fail_cancel(*, stripe_subscription_id: str) -> None:
        assert stripe_subscription_id == f"sub_{user.id}"
        raise httpx.TimeoutException("Stripe timeout during subscription cleanup")

    async def fail_delete_customer(stripe_customer_id: str) -> None:
        assert stripe_customer_id == f"cus_{user.id}"
        raise httpx.TimeoutException("Stripe timeout during customer cleanup")

    monkeypatch.setattr(
        billing_cleanup_service,
        "cancel_stripe_subscription_immediately",
        fail_cancel,
    )
    monkeypatch.setattr(
        billing_cleanup_service,
        "delete_stripe_customer",
        fail_delete_customer,
    )

    response = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"
    assert db.exec(select(User).where(User.id == user.id)).first() is None
    assert (
        db.exec(
            select(BillingSubscription).where(BillingSubscription.user_id == user.id)
        ).all()
        == []
    )
    assert (
        db.exec(
            select(UserBillingAccount).where(UserBillingAccount.user_id == user.id)
        ).all()
        == []
    )
    assert (
        db.exec(select(IgScrapeJob).where(IgScrapeJob.owner_user_id == user.id)).all()
        == []
    )
    assert (
        db.exec(
            select(UserLegalAcceptance).where(UserLegalAcceptance.user_id == user.id)
        ).all()
        == []
    )
    persisted_override = db.get(UserAccessOverride, override.id)
    assert persisted_override is not None
    assert persisted_override.created_by_admin_id is None


def test_delete_user_me_as_superuser(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=superuser_token_headers,
    )
    assert r.status_code == 403
    response = r.json()
    assert response["detail"] == "Super users are not allowed to delete themselves"


def test_delete_user_super_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id
    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    deleted_user = r.json()
    assert deleted_user["message"] == "User deleted successfully"
    result = db.exec(select(User).where(User.id == user_id)).first()
    assert result is None


def test_delete_user_continues_when_stripe_cleanup_raises_http_error(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_password()),
    )
    _seed_user_cleanup_state(db=db, user=user)

    async def fail_cancel(*, stripe_subscription_id: str) -> None:
        assert stripe_subscription_id == f"sub_{user.id}"
        raise httpx.HTTPError("Stripe transport failure during subscription cleanup")

    async def fail_delete_customer(stripe_customer_id: str) -> None:
        assert stripe_customer_id == f"cus_{user.id}"
        raise httpx.HTTPError("Stripe transport failure during customer cleanup")

    monkeypatch.setattr(
        billing_cleanup_service,
        "cancel_stripe_subscription_immediately",
        fail_cancel,
    )
    monkeypatch.setattr(
        billing_cleanup_service,
        "delete_stripe_customer",
        fail_delete_customer,
    )

    response = client.delete(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"
    assert db.exec(select(User).where(User.id == user.id)).first() is None
    assert (
        db.exec(
            select(BillingSubscription).where(BillingSubscription.user_id == user.id)
        ).all()
        == []
    )
    assert (
        db.exec(
            select(UserBillingAccount).where(UserBillingAccount.user_id == user.id)
        ).all()
        == []
    )


def test_delete_user_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


def test_delete_user_current_super_user_error(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    super_user = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert super_user
    user_id = super_user.id

    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Super users are not allowed to delete themselves"


def test_delete_user_without_privileges(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_password()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    r = client.delete(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "The user doesn't have enough privileges"
