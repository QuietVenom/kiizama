from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes import health
from app.core.config import settings


class StubRedisClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def ping(self) -> bool:
        if self.should_fail:
            raise RuntimeError("redis down")
        return True


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
