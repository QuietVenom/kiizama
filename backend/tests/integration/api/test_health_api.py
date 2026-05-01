import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.api.routes import health
from app.core.config import settings
from app.core.resilience import DependencyStateRegistry


class StubRedisClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def ping(self) -> bool:
        if self.should_fail:
            raise RuntimeError("redis down")
        return True


@pytest.fixture(autouse=True)
def isolated_dependency_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> DependencyStateRegistry:
    registry = DependencyStateRegistry(log_window_seconds=60)
    monkeypatch.setattr("app.core.resilience.dependency_state_registry", registry)
    monkeypatch.setattr(health, "dependency_state_registry", registry)
    return registry


def test_ping_resend_requires_api_key() -> None:
    with patch("app.api.routes.health.settings.RESEND_API_KEY", None):
        with pytest.raises(RuntimeError, match="RESEND_API_KEY is not configured"):
            health._ping_resend()


def test_ping_resend_calls_domains_api() -> None:
    with (
        patch("app.api.routes.health.settings.RESEND_API_KEY", "re_test_123"),
        patch(
            "app.api.routes.health.settings.EMAILS_FROM_EMAIL",
            "noreply@mail.kiizama.com",
        ),
        patch(
            "app.api.routes.health.resend.Domains.list", return_value={"data": []}
        ) as domains_list,
    ):
        health._ping_resend()

    domains_list.assert_called_once_with()


def test_ping_resend_requires_from_email() -> None:
    with (
        patch("app.api.routes.health.settings.RESEND_API_KEY", "re_test_123"),
        patch("app.api.routes.health.settings.EMAILS_FROM_EMAIL", None),
    ):
        with pytest.raises(RuntimeError, match="EMAILS_FROM_EMAIL is not configured"):
            health._ping_resend()


def test_ping_resend_rejects_unexpected_domains_payload() -> None:
    with (
        patch("app.api.routes.health.settings.RESEND_API_KEY", "re_test_123"),
        patch(
            "app.api.routes.health.settings.EMAILS_FROM_EMAIL",
            "noreply@mail.kiizama.com",
        ),
        patch(
            "app.api.routes.health.resend.Domains.list", return_value={"data": "bad"}
        ),
    ):
        with pytest.raises(RuntimeError, match="Unexpected Resend domains response"):
            health._ping_resend()


def test_ping_openai_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not configured"):
        health._ping_openai()


def test_live_health_check_does_not_touch_dependencies(client: TestClient) -> None:
    with (
        patch("app.api.routes.health.ping_postgres") as ping_postgres,
        patch("app.api.routes.health.get_redis_client") as get_redis_client,
    ):
        response = client.get(f"{settings.API_V1_STR}/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
    ping_postgres.assert_not_called()
    get_redis_client.assert_not_called()


def test_ready_health_check_returns_degraded_when_redis_fails(
    client: TestClient,
) -> None:
    with (
        patch(
            "app.api.routes.health.settings._resolved_redis_url",
            return_value="redis://test/0",
        ),
        patch("app.api.routes.health.ping_postgres", return_value=None),
        patch(
            "app.api.routes.health.get_redis_client",
            return_value=StubRedisClient(should_fail=True),
        ),
    ):
        response = client.get(f"{settings.API_V1_STR}/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "DEGRADED"
    assert payload["checks"]["postgres"]["status"] == "OK"
    assert payload["checks"]["redis"]["status"] == "DEGRADED"


def test_ready_health_check_returns_503_when_postgres_fails(
    client: TestClient,
) -> None:
    with (
        patch(
            "app.api.routes.health.settings._resolved_redis_url",
            return_value="redis://test/0",
        ),
        patch(
            "app.api.routes.health.ping_postgres", side_effect=RuntimeError("db down")
        ),
        patch(
            "app.api.routes.health.classify_postgres_exception",
            return_value=health.DependencyUnavailableError(
                dependency="postgres",
                detail="Postgres is unavailable.",
            ),
        ),
        patch(
            "app.api.routes.health.get_redis_client",
            return_value=StubRedisClient(should_fail=False),
        ),
    ):
        response = client.get(f"{settings.API_V1_STR}/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "ERROR"
    assert payload["checks"]["postgres"]["status"] == "ERROR"
    assert payload["checks"]["redis"]["status"] == "OK"


def test_health_check_alias_delegates_to_ready_health_check(client: TestClient) -> None:
    expected_response = JSONResponse(
        status_code=200,
        content={"status": "OK", "checks": {"postgres": {"status": "OK"}}},
    )

    with patch(
        "app.api.routes.health.ready_health_check",
        new=AsyncMock(return_value=expected_response),
    ) as ready_health_check:
        response = client.get(f"{settings.API_V1_STR}/health-check/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "OK",
        "checks": {"postgres": {"status": "OK"}},
    }
    ready_health_check.assert_awaited_once_with()


def test_run_check_returns_dependency_payload_for_known_services() -> None:
    async def successful_check() -> None:
        return None

    service, payload = asyncio.run(health._run_check("openai", successful_check))

    assert service == "openai"
    assert payload["status"] == "OK"
    assert isinstance(payload["duration_ms"], int)


def test_run_check_returns_generic_error_payload_for_unknown_service() -> None:
    async def failing_check() -> None:
        raise RuntimeError("instagram unavailable")

    service, payload = asyncio.run(
        health._run_check("instagram_upstream", failing_check)
    )

    assert service == "instagram_upstream"
    assert payload == {
        "status": "ERROR",
        "duration_ms": payload["duration_ms"],
        "error": "instagram unavailable",
    }
    assert isinstance(payload["duration_ms"], int)


def test_deep_health_check_returns_ok_with_skipped_local_dependencies(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    async def successful_check() -> None:
        return None

    with (
        patch(
            "app.api.routes.health.settings._resolved_redis_url",
            return_value=None,
        ),
        patch("app.api.routes.health.settings.ENVIRONMENT", "local"),
        patch("app.api.routes.health._check_postgres", successful_check),
        patch("app.api.routes.health._check_openai", successful_check),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/health-check/deep",
            headers=superuser_token_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "OK"
    assert payload["checks"]["postgres"]["status"] == "OK"
    assert payload["checks"]["openai"]["status"] == "OK"
    assert payload["checks"]["redis"] == {
        "status": "SKIPPED",
        "duration_ms": 0,
        "reason": "REDIS_URL is not configured",
    }
    assert payload["checks"]["resend"] == {
        "status": "SKIPPED",
        "duration_ms": 0,
        "reason": "Skipped in local environment",
    }
    assert isinstance(payload["duration_ms_total"], int)


def test_deep_health_check_returns_503_when_openai_fails(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    async def successful_check() -> None:
        return None

    async def failing_openai_check() -> None:
        raise RuntimeError("openai down")

    with (
        patch(
            "app.api.routes.health.settings._resolved_redis_url",
            return_value=None,
        ),
        patch("app.api.routes.health.settings.ENVIRONMENT", "local"),
        patch("app.api.routes.health._check_postgres", successful_check),
        patch("app.api.routes.health._check_openai", failing_openai_check),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/health-check/deep",
            headers=superuser_token_headers,
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "ERROR"
    assert detail["checks"]["openai"]["status"] == "DEGRADED"
    assert detail["checks"]["openai"]["error"] == "openai down"
    assert detail["errors"] == {"openai": "openai down"}


def test_deep_health_check_returns_503_when_resend_fails_in_non_local_environment(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    async def successful_check() -> None:
        return None

    async def failing_resend_check() -> None:
        raise RuntimeError("resend down")

    with (
        patch(
            "app.api.routes.health.settings._resolved_redis_url",
            return_value="redis://test/0",
        ),
        patch("app.api.routes.health.settings.ENVIRONMENT", "staging"),
        patch("app.api.routes.health._check_postgres", successful_check),
        patch("app.api.routes.health._check_openai", successful_check),
        patch("app.api.routes.health._check_redis", successful_check),
        patch("app.api.routes.health._check_resend", failing_resend_check),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/health-check/deep",
            headers=superuser_token_headers,
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["checks"]["postgres"]["status"] == "OK"
    assert detail["checks"]["openai"]["status"] == "OK"
    assert detail["checks"]["redis"]["status"] == "OK"
    assert detail["checks"]["resend"]["status"] == "DEGRADED"
    assert detail["checks"]["resend"]["error"] == "resend down"
    assert detail["errors"] == {"resend": "resend down"}


def test_deep_health_check_marks_timeout_as_error(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    async def fake_wait(tasks, timeout: int):
        del timeout
        return set(), set(tasks)

    with (
        patch(
            "app.api.routes.health.settings._resolved_redis_url",
            return_value=None,
        ),
        patch("app.api.routes.health.settings.ENVIRONMENT", "local"),
        patch("app.api.routes.health.asyncio.wait", side_effect=fake_wait),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/health-check/deep",
            headers=superuser_token_headers,
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "ERROR"
    assert detail["checks"]["postgres"]["status"] == "ERROR"
    assert detail["checks"]["openai"]["status"] == "ERROR"
    assert detail["checks"]["postgres"]["error"].startswith("Timed out after ")
    assert detail["checks"]["openai"]["error"].startswith("Timed out after ")
    assert set(detail["errors"]) == {"postgres", "openai"}
