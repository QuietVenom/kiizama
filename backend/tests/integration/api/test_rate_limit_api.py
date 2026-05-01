from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.sse import ServerSentEvent
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud_users as crud
from app.api.deps import get_profile_snapshots_collection
from app.core.config import settings
from app.core.redis import configure_redis_client_resolver, create_redis_client
from app.features.ig_scraper_jobs import get_instagram_job_service
from app.features.user_events.service import get_user_event_stream_service
from app.main import app
from app.models import UserCreate
from tests.utils.utils import random_email, random_password


class StubInstagramJobService:
    async def create_job(self, *, payload, owner_user_id: str) -> str:
        del payload, owner_user_id
        return "job-1"

    async def get_job(self, *, job_id: str, owner_user_id: str):
        del owner_user_id
        return {
            "job_id": job_id,
            "status": "queued",
            "created_at": "2026-03-21T12:00:00Z",
            "updated_at": "2026-03-21T12:00:00Z",
            "expires_at": "2026-03-22T12:00:00Z",
            "attempts": 0,
            "lease_owner": None,
            "leased_until": None,
            "heartbeat_at": None,
            "summary": None,
            "references": None,
            "error": None,
        }


class StubEventStreamService:
    async def assert_connection_available(self) -> None:
        return None

    def stream_events(
        self, request: Request, *, user_id: str, last_event_id: str | None
    ):
        del request, user_id, last_event_id

        async def iterator():
            yield ServerSentEvent(id="1-0", event="ok", data={"ok": True})

        return iterator()


class FailingRateLimitRedis:
    async def evalsha(self, *_: Any) -> object:
        raise RuntimeError("redis unavailable")


def _use_real_rate_limit_redis() -> None:
    redis_url = settings._resolved_redis_url()
    if redis_url is None:
        raise RuntimeError("REDIS_URL is not configured.")

    async def flush() -> None:
        client = create_redis_client(redis_url)
        try:
            await client.flushdb()
        finally:
            await client.aclose()

    asyncio.run(flush())
    configure_redis_client_resolver(lambda: create_redis_client(redis_url))


def _ensure_password_recovery_user(db: Session) -> None:
    if crud.get_user_by_email(session=db, email=settings.EMAIL_TEST_USER) is not None:
        return
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=settings.EMAIL_TEST_USER,
            password=random_password(),
            is_active=True,
        ),
    )


@pytest.fixture(autouse=True)
def _reset_redis_resolver() -> Generator[None, None, None]:
    configure_redis_client_resolver(None)
    try:
        yield
    finally:
        configure_redis_client_resolver(None)


@pytest.fixture(autouse=True)
def _enable_rate_limit() -> Generator[None, None, None]:
    previous = settings.RATE_LIMIT_ENABLED
    settings.RATE_LIMIT_ENABLED = True
    try:
        yield
    finally:
        settings.RATE_LIMIT_ENABLED = previous


def test_login_access_token_returns_429_after_ip_username_limit(
    client: TestClient,
) -> None:
    _use_real_rate_limit_redis()
    headers = {"X-Forwarded-For": "203.0.113.10"}

    last_response = None
    for _ in range(6):
        last_response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            headers=headers,
            data={"username": settings.FIRST_SUPERUSER, "password": "incorrect"},
        )

    assert last_response is not None
    assert last_response.status_code == 429
    assert last_response.json()["detail"] == "Rate limit exceeded."
    assert last_response.json()["policy"] == "public_auth_login"
    assert last_response.json()["retry_after_seconds"] in {599, 600}
    assert last_response.headers["RateLimit-Policy"] == "public_auth_login"


def test_password_recovery_enforces_ip_email_limit(
    client: TestClient,
    db: Session,
) -> None:
    _use_real_rate_limit_redis()
    _ensure_password_recovery_user(db)
    headers = {"X-Forwarded-For": "203.0.113.11"}

    with (
        patch("app.api.routes.login.send_email_or_raise", return_value=None),
        patch("app.core.config.settings.RESEND_API_KEY", "re_test_123"),
    ):
        for _ in range(2):
            response = client.post(
                f"{settings.API_V1_STR}/password-recovery/{settings.EMAIL_TEST_USER}",
                headers=headers,
            )
            assert response.status_code == 200

        blocked = client.post(
            f"{settings.API_V1_STR}/password-recovery/{settings.EMAIL_TEST_USER}",
            headers=headers,
        )

    assert blocked.status_code == 429
    assert blocked.json()["policy"] == "public_auth_password_recovery"


def test_password_recovery_enforces_email_limit_across_ips(
    client: TestClient,
    db: Session,
) -> None:
    _use_real_rate_limit_redis()
    _ensure_password_recovery_user(db)

    with (
        patch("app.api.routes.login.send_email_or_raise", return_value=None),
        patch("app.core.config.settings.RESEND_API_KEY", "re_test_123"),
    ):
        for index in range(3):
            response = client.post(
                f"{settings.API_V1_STR}/password-recovery/{settings.EMAIL_TEST_USER}",
                headers={"X-Forwarded-For": f"203.0.113.{20 + index}"},
            )
            assert response.status_code == 200

        blocked = client.post(
            f"{settings.API_V1_STR}/password-recovery/{settings.EMAIL_TEST_USER}",
            headers={"X-Forwarded-For": "203.0.113.30"},
        )

    assert blocked.status_code == 429


def test_password_recovery_enforces_ip_limit_across_emails(
    client: TestClient,
    db: Session,
) -> None:
    _use_real_rate_limit_redis()
    headers = {"X-Forwarded-For": "203.0.113.40"}
    emails: list[str] = []

    for _ in range(6):
        email = random_email()
        password = random_password()
        crud.create_user(
            session=db,
            user_create=UserCreate(email=email, password=password, is_active=True),
        )
        emails.append(email)

    with (
        patch("app.api.routes.login.send_email_or_raise", return_value=None),
        patch("app.core.config.settings.RESEND_API_KEY", "re_test_123"),
    ):
        for email in emails[:5]:
            response = client.post(
                f"{settings.API_V1_STR}/password-recovery/{email}",
                headers=headers,
            )
            assert response.status_code == 200

        blocked = client.post(
            f"{settings.API_V1_STR}/password-recovery/{emails[5]}",
            headers=headers,
        )

    assert blocked.status_code == 429


def test_signup_returns_429_after_same_ip_limit(
    client: TestClient,
) -> None:
    _use_real_rate_limit_redis()
    headers = {"X-Forwarded-For": "203.0.113.50"}
    signup_payload = {
        "password": random_password(),
        "legal_acceptances": {
            "privacy_notice": True,
            "terms_conditions": True,
        },
    }

    for _ in range(5):
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            headers=headers,
            json={**signup_payload, "email": random_email()},
        )
        assert response.status_code == 200

    blocked = client.post(
        f"{settings.API_V1_STR}/users/signup",
        headers=headers,
        json={**signup_payload, "email": random_email()},
    )
    assert blocked.status_code == 429


def test_public_waiting_list_returns_429_after_same_ip_limit(
    client: TestClient,
) -> None:
    _use_real_rate_limit_redis()
    headers = {"X-Forwarded-For": "203.0.113.60"}

    for _ in range(5):
        response = client.post(
            f"{settings.API_V1_STR}/public/waiting-list/",
            headers=headers,
            json={"email": random_email(), "interest": "marketing"},
        )
        assert response.status_code == 200

    blocked = client.post(
        f"{settings.API_V1_STR}/public/waiting-list/",
        headers=headers,
        json={"email": random_email(), "interest": "marketing"},
    )
    assert blocked.status_code == 429


def test_jobs_write_limit_is_user_based_not_ip_based(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    _use_real_rate_limit_redis()
    app.dependency_overrides[get_instagram_job_service] = lambda: (
        StubInstagramJobService()
    )
    try:
        for index in range(12):
            response = client.post(
                f"{settings.API_V1_STR}/ig-scraper/jobs",
                headers={
                    **normal_user_token_headers,
                    "X-Forwarded-For": f"203.0.113.{70 + index}",
                },
                json={"usernames": ["alpha"]},
            )
            assert response.status_code == 202

        blocked = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs",
            headers={**normal_user_token_headers, "X-Forwarded-For": "198.51.100.1"},
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert blocked.status_code == 429


def test_stream_connect_returns_429_after_handshake_limit(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    _use_real_rate_limit_redis()
    app.dependency_overrides[get_user_event_stream_service] = lambda: (
        StubEventStreamService()
    )
    try:
        for _ in range(6):
            response = client.get(
                f"{settings.API_V1_STR}/events/stream",
                headers=normal_user_token_headers,
            )
            assert response.status_code == 200

        blocked = client.get(
            f"{settings.API_V1_STR}/events/stream",
            headers=normal_user_token_headers,
        )
    finally:
        app.dependency_overrides.pop(get_user_event_stream_service, None)

    assert blocked.status_code == 429


def test_private_basic_policy_is_shared_across_endpoints(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    _use_real_rate_limit_redis()

    for _ in range(179):
        response = client.get(
            f"{settings.API_V1_STR}/users/me",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200

    response = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200

    blocked = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    assert blocked.status_code == 429


def test_public_auth_fail_closed_returns_503_when_redis_fails(
    client: TestClient,
) -> None:
    configure_redis_client_resolver(FailingRateLimitRedis)

    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        headers={"X-Forwarded-For": "203.0.113.90"},
        data={"username": settings.FIRST_SUPERUSER, "password": "incorrect"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "redis unavailable",
        "dependency": "redis",
        "retryable": True,
    }


def test_jobs_write_fail_open_allows_request_when_redis_fails(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    configure_redis_client_resolver(FailingRateLimitRedis)
    app.dependency_overrides[get_instagram_job_service] = lambda: (
        StubInstagramJobService()
    )
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs",
            headers=normal_user_token_headers,
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 202


def test_private_expensive_headers_are_present_on_success(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    _use_real_rate_limit_redis()
    fake_collection = object()
    app.dependency_overrides[get_profile_snapshots_collection] = lambda: fake_collection
    try:
        with patch(
            "app.api.routes.ig_profile_snapshots.list_profile_snapshots_full",
            new=MagicMock(return_value=[]),
        ):
            response = client.get(
                f"{settings.API_V1_STR}/ig-profile-snapshots/advanced",
                headers=normal_user_token_headers,
            )
    finally:
        app.dependency_overrides.pop(get_profile_snapshots_collection, None)

    assert response.status_code == 200
    assert response.headers["RateLimit-Policy"] == "private_expensive"
