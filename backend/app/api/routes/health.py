import asyncio
import logging
import os
import smtplib
import ssl
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI

from app.api.deps import get_current_active_superuser
from app.core.config import settings
from app.core.db import ping_postgres
from app.core.mongodb import get_mongo_client

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)
DEEP_HEALTH_TIMEOUT_SECONDS = 15


@router.get("/health-check/")
async def health_check() -> bool:
    try:
        ping_postgres()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Postgres health check failed",
        ) from exc

    try:
        database = get_mongo_client()[settings.MONGODB_KIIZAMA_IG]
        ping_response = await database.command("ping")
        if int(ping_response.get("ok", 0)) != 1:
            raise RuntimeError("MongoDB ping returned non-ok response")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB health check failed",
        ) from exc

    return True


def _ping_sendgrid() -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not configured")
    if not settings.SMTP_PORT:
        raise RuntimeError("SMTP_PORT is not configured")
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise RuntimeError("SMTP_USER and SMTP_PASSWORD must be configured")

    timeout_seconds = 10
    tls_context = ssl.create_default_context()

    if settings.SMTP_SSL:
        with smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=timeout_seconds,
            context=tls_context,
        ) as smtp:
            smtp.ehlo()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            status_code, _ = smtp.noop()
            if status_code != 250:
                raise RuntimeError(f"SMTP NOOP returned status {status_code}")
        return

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=timeout_seconds,
    ) as smtp:
        smtp.ehlo()
        if settings.SMTP_TLS:
            smtp.starttls(context=tls_context)
            smtp.ehlo()
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        status_code, _ = smtp.noop()
        if status_code != 250:
            raise RuntimeError(f"SMTP NOOP returned status {status_code}")


def _ping_openai() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=api_key, timeout=10, max_retries=0)
    client.models.list()


def _duration_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


async def _check_postgres() -> None:
    await to_thread.run_sync(ping_postgres)


async def _check_mongo() -> None:
    database = get_mongo_client()[settings.MONGODB_KIIZAMA_IG]
    ping_response = await database.command("ping")
    if int(ping_response.get("ok", 0)) != 1:
        raise RuntimeError("MongoDB ping returned non-ok response")


async def _check_openai() -> None:
    await to_thread.run_sync(_ping_openai)


async def _check_sendgrid() -> None:
    await to_thread.run_sync(_ping_sendgrid)


async def _run_check(
    service: str, check_fn: Callable[[], Awaitable[None]]
) -> tuple[str, dict[str, Any]]:
    started_at = perf_counter()
    try:
        await check_fn()
        return service, {"status": "OK", "duration_ms": _duration_ms(started_at)}
    except Exception as exc:
        message = str(exc) or f"{service} health check failed"
        logger.exception(
            "Deep health check failed for service '%s': %s", service, message
        )
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

    check_functions: dict[str, Callable[[], Awaitable[None]]] = {
        "postgres": _check_postgres,
        "mongo": _check_mongo,
        "openai": _check_openai,
    }
    if settings.ENVIRONMENT != "local":
        check_functions["sendgrid"] = _check_sendgrid
    else:
        checks["sendgrid"] = {
            "status": "SKIPPED",
            "duration_ms": 0,
            "reason": "Skipped in local environment",
        }
    task_started_at: dict[str, float] = {}
    task_by_service: dict[str, asyncio.Task[tuple[str, dict[str, Any]]]] = {}
    service_by_task: dict[asyncio.Task[tuple[str, dict[str, Any]]], str] = {}

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
            errors[service] = str(result["error"])

    for task in pending:
        service = service_by_task[task]
        task.cancel()
        timeout_message = f"Timed out after {DEEP_HEALTH_TIMEOUT_SECONDS}s"
        logger.error(
            "Deep health check timed out for service '%s' after %ss",
            service,
            DEEP_HEALTH_TIMEOUT_SECONDS,
        )
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
