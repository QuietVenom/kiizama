import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

import resend
from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from openai import OpenAI
from starlette.responses import Response

from app.api.deps import get_current_active_superuser
from app.core.config import settings
from app.core.db import ping_postgres
from app.core.redis import get_redis_client
from app.core.resilience import (
    DependencyName,
    DependencyUnavailableError,
    build_dependency_check,
    classify_postgres_exception,
    dependency_state_registry,
    mark_dependency_failure,
    mark_dependency_success,
    translate_redis_exception,
    translate_resend_exception,
)

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)
DEEP_HEALTH_TIMEOUT_SECONDS = 15


def _duration_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


async def _probe_postgres(*, context: str) -> dict[str, Any]:
    started_at = perf_counter()
    try:
        await to_thread.run_sync(ping_postgres)
    except Exception as exc:
        translated = classify_postgres_exception(exc) or DependencyUnavailableError(
            dependency="postgres",
            detail="Postgres health check failed.",
        )
        mark_dependency_failure(
            "postgres",
            context=context,
            detail=translated.detail,
            exc=exc,
        )
    else:
        mark_dependency_success(
            "postgres",
            context=context,
            detail="Postgres is healthy.",
        )
    return build_dependency_check("postgres", duration_ms=_duration_ms(started_at))


async def _probe_redis(*, context: str) -> dict[str, Any]:
    started_at = perf_counter()
    if not settings._resolved_redis_url():
        mark_dependency_failure(
            "redis",
            context=context,
            detail="REDIS_URL is not configured.",
            status="degraded",
        )
        return build_dependency_check("redis", duration_ms=_duration_ms(started_at))

    try:
        await get_redis_client().ping()
    except Exception as exc:
        translated = translate_redis_exception(
            exc,
            detail="Redis health check failed.",
        )
        mark_dependency_failure(
            "redis",
            context=context,
            detail=translated.detail,
            status="degraded",
            exc=exc,
        )
    else:
        mark_dependency_success(
            "redis",
            context=context,
            detail="Redis is healthy.",
        )
    return build_dependency_check("redis", duration_ms=_duration_ms(started_at))


@router.get("/health/live")
async def live_health_check() -> dict[str, str]:
    return {"status": "OK"}


@router.get("/health/ready", response_model=None)
async def ready_health_check() -> Response:
    checks = {
        "postgres": await _probe_postgres(context="readiness"),
        "redis": await _probe_redis(context="readiness"),
    }
    postgres_status = dependency_state_registry.snapshot("postgres").status
    redis_status = dependency_state_registry.snapshot("redis").status

    overall_status = "OK"
    status_code = status.HTTP_200_OK
    if postgres_status != "healthy":
        overall_status = "ERROR"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif redis_status != "healthy":
        overall_status = "DEGRADED"

    payload = {"status": overall_status, "checks": checks}
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/health-check/", response_model=None)
async def health_check() -> Response:
    return await ready_health_check()


def _ping_resend() -> None:
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured")
    if not settings.EMAILS_FROM_EMAIL:
        raise RuntimeError("EMAILS_FROM_EMAIL is not configured")

    resend.api_key = settings.RESEND_API_KEY
    payload = resend.Domains.list()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Unexpected Resend domains response")


def _ping_openai() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=api_key, timeout=10, max_retries=0)
    client.models.list()


async def _check_postgres() -> None:
    result = await _probe_postgres(context="deep-health")
    if result["status"] != "OK":
        raise RuntimeError(result.get("detail", "Postgres health check failed."))


async def _check_redis() -> None:
    result = await _probe_redis(context="deep-health")
    if result["status"] != "OK":
        raise RuntimeError(result.get("detail", "Redis health check failed."))


async def _check_openai() -> None:
    await to_thread.run_sync(_ping_openai)
    mark_dependency_success(
        "openai", context="deep-health", detail="OpenAI is healthy."
    )


async def _check_resend() -> None:
    await to_thread.run_sync(_ping_resend)
    mark_dependency_success(
        "resend", context="deep-health", detail="Resend is healthy."
    )


async def _run_check(
    service: DependencyName,
    check_fn: Callable[[], Awaitable[None]],
) -> tuple[DependencyName, dict[str, Any]]:
    started_at = perf_counter()
    try:
        await check_fn()
        if service in {"postgres", "redis", "openai", "resend"}:
            return service, build_dependency_check(
                service,
                duration_ms=_duration_ms(started_at),
            )
        return service, {"status": "OK", "duration_ms": _duration_ms(started_at)}
    except Exception as exc:
        if service == "resend":
            translated = translate_resend_exception(exc)
            mark_dependency_failure(
                "resend",
                context="deep-health",
                detail=translated.detail,
                status="degraded",
                exc=exc,
            )
        elif service == "openai":
            mark_dependency_failure(
                "openai",
                context="deep-health",
                detail=str(exc) or "OpenAI health check failed.",
                status="degraded",
                exc=exc,
            )
        message = str(exc) or f"{service} health check failed"
        logger.exception(
            "Deep health check failed for service '%s': %s",
            service,
            message,
        )
        if service in {"postgres", "redis", "openai", "resend"}:
            result = build_dependency_check(
                service, duration_ms=_duration_ms(started_at)
            )
            result["error"] = message
            return service, result
        return service, {
            "status": "ERROR",
            "duration_ms": _duration_ms(started_at),
            "error": message,
        }


@router.get(
    "/health-check/deep",
    dependencies=[Depends(get_current_active_superuser)],
)
async def deep_health_check() -> dict[str, Any]:
    total_started_at = perf_counter()
    checks: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    check_functions: dict[DependencyName, Callable[[], Awaitable[None]]] = {
        "postgres": _check_postgres,
        "openai": _check_openai,
    }
    if settings._resolved_redis_url():
        check_functions["redis"] = _check_redis
    else:
        checks["redis"] = {
            "status": "SKIPPED",
            "duration_ms": 0,
            "reason": "REDIS_URL is not configured",
        }
    if settings.ENVIRONMENT != "local":
        check_functions["resend"] = _check_resend
    else:
        checks["resend"] = {
            "status": "SKIPPED",
            "duration_ms": 0,
            "reason": "Skipped in local environment",
        }

    task_started_at: dict[str, float] = {}
    task_by_service: dict[
        DependencyName,
        asyncio.Task[tuple[DependencyName, dict[str, Any]]],
    ] = {}
    service_by_task: dict[
        asyncio.Task[tuple[DependencyName, dict[str, Any]]],
        DependencyName,
    ] = {}

    for service, check_fn in check_functions.items():
        task_started_at[service] = perf_counter()
        task = asyncio.create_task(_run_check(service, check_fn))
        task_by_service[service] = task
        service_by_task[task] = service

    done, pending = await asyncio.wait(
        task_by_service.values(),
        timeout=DEEP_HEALTH_TIMEOUT_SECONDS,
    )

    for task in done:
        service, result = task.result()
        checks[service] = result
        if result["status"] == "ERROR":
            errors[service] = str(result.get("error") or result.get("detail"))

    for task in pending:
        service = service_by_task[task]
        task.cancel()
        timeout_message = f"Timed out after {DEEP_HEALTH_TIMEOUT_SECONDS}s"
        if service in {"openai", "resend"}:
            mark_dependency_failure(
                service,
                context="deep-health",
                detail=timeout_message,
                status="degraded",
            )
        logger.error(
            "Deep health check timed out for service '%s' after %ss",
            service,
            DEEP_HEALTH_TIMEOUT_SECONDS,
        )
        if service in {"postgres", "redis", "openai", "resend"}:
            checks[service] = build_dependency_check(
                service,
                duration_ms=_duration_ms(task_started_at[service]),
            )
            checks[service]["status"] = "ERROR"
            checks[service]["error"] = timeout_message
        else:
            checks[service] = {
                "status": "ERROR",
                "duration_ms": _duration_ms(task_started_at[service]),
                "error": timeout_message,
            }
        errors[service] = timeout_message

    total_duration_ms = _duration_ms(total_started_at)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "ERROR",
                "checks": checks,
                "errors": errors,
                "duration_ms_total": total_duration_ms,
            },
        )

    return {"status": "OK", "checks": checks, "duration_ms_total": total_duration_ms}


__all__ = [
    "deep_health_check",
    "health_check",
    "live_health_check",
    "ready_health_check",
]
