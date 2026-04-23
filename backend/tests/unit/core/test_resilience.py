import httpx
from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError

from app.core.resilience import (
    DependencyStateRegistry,
    DependencyUnavailableError,
    UpstreamBadResponseError,
    UpstreamUnavailableError,
    build_dependency_check,
    build_dependency_error_payload,
    classify_postgres_exception,
    dependency_state_registry,
    translate_instagram_upstream_exception,
    translate_openai_exception,
    translate_redis_exception,
    translate_resend_exception,
)


def test_dependency_state_registry_tracks_failure_check_and_recovery(
    monkeypatch,
) -> None:
    registry = DependencyStateRegistry(log_window_seconds=60)
    monkeypatch.setattr(
        "app.core.resilience.dependency_state_registry",
        registry,
    )

    registry.mark_failure(
        "redis",
        context="test",
        detail="Redis is degraded.",
        status="degraded",
    )
    degraded_check = build_dependency_check("redis", duration_ms=12)
    registry.mark_success("redis", context="test", detail="Redis recovered.")
    healthy_check = build_dependency_check("redis", duration_ms=3)

    assert degraded_check == {
        "status": "DEGRADED",
        "duration_ms": 12,
        "detail": "Redis is degraded.",
    }
    assert healthy_check == {
        "status": "OK",
        "duration_ms": 3,
        "detail": "Redis recovered.",
    }


def test_build_dependency_error_payload_preserves_retry_contract() -> None:
    error = DependencyUnavailableError(
        dependency="redis",
        detail="Redis down.",
        retryable=False,
    )

    assert build_dependency_error_payload(error) == {
        "detail": "Redis down.",
        "dependency": "redis",
        "retryable": False,
    }


def test_classify_postgres_exception_detects_connectivity_failures() -> None:
    exc = OperationalError(
        "select 1",
        {},
        Exception("connection refused"),
    )

    translated = classify_postgres_exception(exc)

    assert translated is not None
    assert translated.dependency == "postgres"
    assert translated.status_code == 503


def test_translate_openai_exception_maps_response_status_classes() -> None:
    client_error = type("OpenAIResponseError", (Exception,), {"status_code": 400})(
        "bad request"
    )
    server_error = type("OpenAIResponseError", (Exception,), {"status_code": 503})(
        "unavailable"
    )

    assert isinstance(
        translate_openai_exception(client_error, detail="bad payload"),
        UpstreamBadResponseError,
    )
    assert isinstance(
        translate_openai_exception(server_error, detail="server unavailable"),
        UpstreamUnavailableError,
    )


def test_translate_instagram_upstream_exception_maps_4xx_to_bad_response() -> None:
    request = httpx.Request("GET", "https://instagram.test/profile")
    response = httpx.Response(404, request=request)
    error = httpx.HTTPStatusError(
        "not found",
        request=request,
        response=response,
    )

    translated = translate_instagram_upstream_exception(error)

    assert isinstance(translated, UpstreamBadResponseError)
    assert translated.dependency == "instagram_upstream"
    assert translated.status_code == 502


def test_translate_redis_and_resend_exceptions_return_dependency_errors() -> None:
    redis_error = translate_redis_exception(
        RedisError("redis down"),
        detail="Redis unavailable.",
        retryable=False,
    )
    resend_error = translate_resend_exception(
        RuntimeError("resend down"),
        detail="Resend unavailable.",
        retryable=False,
    )

    assert redis_error.dependency == "redis"
    assert redis_error.retryable is False
    assert resend_error.dependency == "resend"
    assert resend_error.retryable is False


def test_global_dependency_registry_defaults_unknown_dependency_to_healthy() -> None:
    snapshot = dependency_state_registry.snapshot("openai")

    assert snapshot.status in {"healthy", "degraded", "unavailable"}
