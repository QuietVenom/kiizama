from __future__ import annotations

import asyncio

from fastapi import Response
from starlette.requests import Request

from app.core.resilience import DependencyUnavailableError
from app.features.rate_limit.policies import POLICIES
from app.features.rate_limit.repository import RateLimitRepository
from app.features.rate_limit.schemas import RateLimitDecision
from app.features.rate_limit.service import RateLimitExceededError, RateLimitService


def _request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [(b"x-forwarded-for", b"203.0.113.1")],
        "client": ("203.0.113.1", 1234),
        "path_params": {},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


class StubRepository(RateLimitRepository):
    def __init__(self, decisions: list[RateLimitDecision] | None = None) -> None:
        self.decisions = decisions or []
        self.exception: Exception | None = None
        self.calls = 0

    async def evaluate_rule(self, **_: object) -> RateLimitDecision:
        if self.exception is not None:
            raise self.exception
        decision = self.decisions[self.calls]
        self.calls += 1
        return decision


def test_service_sets_headers_on_allow() -> None:
    repository = StubRepository(
        decisions=[
            RateLimitDecision(
                allowed=True,
                limit=5,
                remaining=4,
                retry_after_seconds=0,
                reset_after_seconds=900,
                rule="ip",
            )
        ]
    )
    service = RateLimitService(repository=repository)
    response = Response()

    asyncio.run(
        service.enforce(
            policy=POLICIES.public_form_submit,
            request=_request(),
            response=response,
        )
    )

    assert response.headers["RateLimit-Limit"] == "5"
    assert response.headers["RateLimit-Remaining"] == "4"
    assert response.headers["RateLimit-Reset"] == "900"
    assert response.headers["RateLimit-Policy"] == "public_form_submit"


def test_service_raises_rate_limit_error_on_deny() -> None:
    repository = StubRepository(
        decisions=[
            RateLimitDecision(
                allowed=False,
                limit=5,
                remaining=0,
                retry_after_seconds=600,
                reset_after_seconds=600,
                rule="ip_username",
            )
        ]
    )
    service = RateLimitService(repository=repository)

    try:
        asyncio.run(
            service.enforce(
                policy=POLICIES.public_auth_login,
                request=_request(),
                response=Response(),
            )
        )
    except RateLimitExceededError as exc:
        assert exc.policy == "public_auth_login"
        assert exc.retry_after_seconds == 600
    else:
        raise AssertionError("Expected RateLimitExceededError")


def test_service_fail_open_on_redis_error() -> None:
    repository = StubRepository()
    repository.exception = RuntimeError("redis down")
    service = RateLimitService(repository=repository)

    asyncio.run(
        service.enforce(
            policy=POLICIES.public_form_submit,
            request=_request(),
            response=Response(),
        )
    )


def test_service_fail_closed_on_redis_error() -> None:
    repository = StubRepository()
    repository.exception = RuntimeError("redis down")
    service = RateLimitService(repository=repository)

    try:
        asyncio.run(
            service.enforce(
                policy=POLICIES.public_auth_login,
                request=_request(),
                response=Response(),
            )
        )
    except DependencyUnavailableError as exc:
        assert exc.dependency == "redis"
    else:
        raise AssertionError("Expected DependencyUnavailableError")
