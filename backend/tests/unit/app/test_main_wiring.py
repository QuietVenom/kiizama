import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from sqlalchemy.exc import OperationalError

from app import main
from app.core.resilience import DependencyUnavailableError, UpstreamBadResponseError
from app.features.rate_limit import RateLimitExceededError


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }
    )


def test_custom_generate_unique_id_uses_first_tag_and_route_name() -> None:
    route = SimpleNamespace(tags=["users"], name="read_users")

    assert main.custom_generate_unique_id(route) == "users-read_users"


@pytest.mark.parametrize("environment", ["local", "staging"])
def test_build_docs_config_keeps_openapi_enabled_outside_production(
    environment: str,
) -> None:
    assert main.build_docs_config(environment=environment, api_v1_str="/api/v1") == (
        "/docs",
        "/redoc",
        "/api/v1/openapi.json",
    )


def test_build_docs_config_disables_docs_and_openapi_in_production() -> None:
    assert main.build_docs_config(environment="production", api_v1_str="/api/v1") == (
        None,
        None,
        None,
    )


def test_dependency_and_upstream_error_responses_preserve_contract() -> None:
    dependency_response = main._build_dependency_error_response(
        DependencyUnavailableError(
            dependency="redis",
            detail="Redis unavailable.",
            retryable=False,
        )
    )
    upstream_response = main._build_dependency_error_response(
        UpstreamBadResponseError(
            dependency="openai",
            detail="OpenAI bad response.",
        )
    )

    assert dependency_response.status_code == 503
    assert json.loads(dependency_response.body) == {
        "detail": "Redis unavailable.",
        "dependency": "redis",
        "retryable": False,
    }
    assert upstream_response.status_code == 502


def test_rate_limit_error_response_sets_retry_and_rate_limit_headers() -> None:
    response = main._build_rate_limit_error_response(
        RateLimitExceededError(
            policy="login",
            retry_after_seconds=30,
            limit=5,
            remaining=0,
            reset_after_seconds=60,
        )
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert response.headers["RateLimit-Limit"] == "5"
    assert response.headers["RateLimit-Remaining"] == "0"
    assert response.headers["RateLimit-Reset"] == "60"
    assert response.headers["RateLimit-Policy"] == "login"


@pytest.mark.anyio
async def test_postgres_dependency_middleware_translates_connectivity_errors() -> None:
    async def call_next(_request: Request):
        raise OperationalError("select 1", {}, Exception("connection refused"))

    response = await main.postgres_dependency_middleware(_request(), call_next)

    assert response.status_code == 503
    assert json.loads(response.body)["dependency"] == "postgres"


@pytest.mark.anyio
async def test_lifespan_marks_postgres_success_and_degraded_redis_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str | None]] = []

    class FakeStripeCustomerSyncSupervisor:
        async def start(self) -> None:
            events.append(("stripe", "start", None))

        async def stop(self) -> None:
            events.append(("stripe", "stop", None))

    async def close_redis_client() -> None:
        events.append(("redis", "close", None))

    monkeypatch.setattr(main, "ensure_postgres_connection", lambda: None)
    monkeypatch.setattr(main.settings, "_resolved_redis_url", lambda: None)
    monkeypatch.setattr(
        main,
        "StripeCustomerSyncSupervisor",
        FakeStripeCustomerSyncSupervisor,
    )
    monkeypatch.setattr(main, "close_redis_client", close_redis_client)
    monkeypatch.setattr(
        main,
        "mark_dependency_success",
        lambda dependency, **kwargs: events.append(
            (dependency, "success", kwargs.get("context"))
        ),
    )
    monkeypatch.setattr(
        main,
        "mark_dependency_failure",
        lambda dependency, **kwargs: events.append(
            (dependency, "failure", kwargs.get("context"))
        ),
    )

    async with main.lifespan(FastAPI()):
        events.append(("app", "running", None))

    assert ("postgres", "success", "startup") in events
    assert ("redis", "failure", "startup") in events
    assert ("stripe", "start", None) in events
    assert ("stripe", "stop", None) in events
    assert ("redis", "close", None) in events


@pytest.mark.anyio
async def test_supervisor_stop_cancels_running_tasks() -> None:
    class WaitingSupervisor(main.StripeCustomerSyncSupervisor):
        async def _run(self) -> None:
            await asyncio.sleep(60)

    supervisor = WaitingSupervisor()
    await supervisor.start()

    assert supervisor._task is not None

    await supervisor.stop()

    assert supervisor._task is None
