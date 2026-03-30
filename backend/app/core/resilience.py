from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from openai import OpenAIError
from redis.exceptions import RedisError
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from app.features.openai.types import OpenAIResponseError

DependencyName = Literal[
    "postgres",
    "redis",
    "openai",
    "resend",
    "instagram_upstream",
]
DependencyStatus = Literal["healthy", "degraded", "unavailable"]

logger = logging.getLogger(__name__)
LOG_SUPPRESSION_WINDOW_SECONDS = 60.0
POSTGRES_CONNECTIVITY_HINTS = (
    "connection refused",
    "connection reset",
    "could not connect",
    "connection not open",
    "connection is closed",
    "server closed the connection unexpectedly",
    "terminating connection",
    "connection timeout",
    "timeout expired",
    "name or service not known",
    "temporary failure in name resolution",
)


class DependencyUnavailableError(RuntimeError):
    def __init__(
        self,
        *,
        dependency: DependencyName,
        detail: str,
        retryable: bool = True,
    ) -> None:
        super().__init__(detail)
        self.dependency = dependency
        self.detail = detail
        self.retryable = retryable
        self.status_code = 503


class UpstreamUnavailableError(DependencyUnavailableError):
    pass


class UpstreamBadResponseError(RuntimeError):
    def __init__(
        self,
        *,
        dependency: DependencyName,
        detail: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(detail)
        self.dependency = dependency
        self.detail = detail
        self.retryable = retryable
        self.status_code = 502


@dataclass(slots=True)
class DependencySnapshot:
    status: DependencyStatus = "healthy"
    detail: str | None = None
    updated_at: float = 0.0


@dataclass(slots=True)
class FailureLogState:
    last_logged_at: float = 0.0
    suppressed_count: int = 0


class DependencyStateRegistry:
    def __init__(
        self,
        *,
        log_window_seconds: float = LOG_SUPPRESSION_WINDOW_SECONDS,
    ) -> None:
        self._log_window_seconds = log_window_seconds
        self._snapshots: dict[DependencyName, DependencySnapshot] = {}
        self._failure_logs: dict[tuple[DependencyName, str], FailureLogState] = {}

    def snapshot(self, dependency: DependencyName) -> DependencySnapshot:
        return self._snapshots.get(dependency, DependencySnapshot())

    def mark_success(
        self,
        dependency: DependencyName,
        *,
        context: str,
        detail: str | None = None,
    ) -> None:
        now = time.time()
        previous = self.snapshot(dependency)
        self._snapshots[dependency] = DependencySnapshot(
            status="healthy",
            detail=detail,
            updated_at=now,
        )

        failure_log = self._failure_logs.get((dependency, context))
        repeated_failures = 0 if failure_log is None else failure_log.suppressed_count
        self._failure_logs.pop((dependency, context), None)

        if previous.status != "healthy":
            if repeated_failures > 0:
                logger.info(
                    "Dependency '%s' recovered while %s after %s repeated failures.",
                    dependency,
                    context,
                    repeated_failures,
                )
            else:
                logger.info("Dependency '%s' recovered while %s.", dependency, context)

    def mark_failure(
        self,
        dependency: DependencyName,
        *,
        context: str,
        detail: str,
        status: DependencyStatus = "unavailable",
        exc: BaseException | None = None,
    ) -> None:
        now = time.time()
        previous = self.snapshot(dependency)
        self._snapshots[dependency] = DependencySnapshot(
            status=status,
            detail=detail,
            updated_at=now,
        )

        key = (dependency, context)
        failure_log = self._failure_logs.setdefault(key, FailureLogState())
        should_log_full = previous.status != status or failure_log.last_logged_at == 0.0

        if should_log_full:
            failure_log.last_logged_at = now
            failure_log.suppressed_count = 0
            if exc is not None:
                logger.exception(
                    "Dependency '%s' entered %s while %s: %s",
                    dependency,
                    status,
                    context,
                    detail,
                )
            else:
                logger.warning(
                    "Dependency '%s' entered %s while %s: %s",
                    dependency,
                    status,
                    context,
                    detail,
                )
            return

        if now - failure_log.last_logged_at >= self._log_window_seconds:
            repeated_failures = failure_log.suppressed_count
            failure_log.last_logged_at = now
            failure_log.suppressed_count = 0
            logger.warning(
                "Dependency '%s' still %s while %s after %s repeated failures: %s",
                dependency,
                status,
                context,
                repeated_failures,
                detail,
            )
            return

        failure_log.suppressed_count += 1


dependency_state_registry = DependencyStateRegistry()


def mark_dependency_success(
    dependency: DependencyName,
    *,
    context: str,
    detail: str | None = None,
) -> None:
    dependency_state_registry.mark_success(
        dependency,
        context=context,
        detail=detail,
    )


def mark_dependency_failure(
    dependency: DependencyName,
    *,
    context: str,
    detail: str,
    status: DependencyStatus = "unavailable",
    exc: BaseException | None = None,
) -> None:
    dependency_state_registry.mark_failure(
        dependency,
        context=context,
        detail=detail,
        status=status,
        exc=exc,
    )


def build_dependency_error_payload(
    exc: DependencyUnavailableError | UpstreamBadResponseError,
) -> dict[str, Any]:
    return {
        "detail": exc.detail,
        "dependency": exc.dependency,
        "retryable": exc.retryable,
    }


def build_dependency_check(
    dependency: DependencyName,
    *,
    duration_ms: int,
) -> dict[str, Any]:
    snapshot = dependency_state_registry.snapshot(dependency)
    status = {
        "healthy": "OK",
        "degraded": "DEGRADED",
        "unavailable": "ERROR",
    }[snapshot.status]
    result: dict[str, Any] = {
        "status": status,
        "duration_ms": duration_ms,
    }
    if snapshot.detail:
        result["detail"] = snapshot.detail
    return result


def classify_postgres_exception(
    exc: BaseException,
) -> DependencyUnavailableError | None:
    if not isinstance(exc, (OperationalError, InterfaceError, DBAPIError)):
        return None

    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return DependencyUnavailableError(
            dependency="postgres",
            detail="Postgres is unavailable.",
        )

    message = " ".join(
        part.strip()
        for part in (
            str(exc),
            str(getattr(exc, "orig", "")),
        )
        if part and str(part).strip()
    ).lower()
    if any(hint in message for hint in POSTGRES_CONNECTIVITY_HINTS):
        return DependencyUnavailableError(
            dependency="postgres",
            detail="Postgres is unavailable.",
        )
    return None


def translate_openai_exception(
    exc: BaseException,
    *,
    detail: str | None = None,
) -> DependencyUnavailableError | UpstreamBadResponseError:
    if isinstance(exc, OpenAIResponseError):
        message = detail or str(exc)
        if exc.status_code >= 500:
            return UpstreamUnavailableError(
                dependency="openai",
                detail=message,
            )
        return UpstreamBadResponseError(
            dependency="openai",
            detail=message,
        )

    if isinstance(exc, (OpenAIError, httpx.TransportError)):
        return UpstreamUnavailableError(
            dependency="openai",
            detail=detail or f"OpenAI is unavailable: {exc}",
        )

    return UpstreamUnavailableError(
        dependency="openai",
        detail=detail or f"OpenAI is unavailable: {exc}",
    )


def translate_resend_exception(
    exc: BaseException,
    *,
    detail: str | None = None,
    retryable: bool = True,
) -> DependencyUnavailableError:
    return UpstreamUnavailableError(
        dependency="resend",
        detail=detail or f"Resend is unavailable: {exc}",
        retryable=retryable,
    )


def translate_instagram_upstream_exception(
    exc: BaseException,
    *,
    detail: str | None = None,
) -> DependencyUnavailableError | UpstreamBadResponseError:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
        return UpstreamBadResponseError(
            dependency="instagram_upstream",
            detail=detail or f"Instagram upstream returned an invalid response: {exc}",
        )

    if isinstance(
        exc,
        (httpx.TransportError, httpx.TimeoutException, httpx.HTTPStatusError),
    ):
        return UpstreamUnavailableError(
            dependency="instagram_upstream",
            detail=detail or f"Instagram upstream is unavailable: {exc}",
        )

    return UpstreamUnavailableError(
        dependency="instagram_upstream",
        detail=detail or f"Instagram upstream is unavailable: {exc}",
    )


def translate_redis_exception(
    exc: BaseException,
    *,
    detail: str,
    retryable: bool = True,
) -> DependencyUnavailableError:
    if isinstance(exc, (RedisError, RuntimeError, TimeoutError)):
        return DependencyUnavailableError(
            dependency="redis",
            detail=detail,
            retryable=retryable,
        )
    return DependencyUnavailableError(
        dependency="redis",
        detail=detail,
        retryable=retryable,
    )


__all__ = [
    "DependencyName",
    "DependencySnapshot",
    "DependencyUnavailableError",
    "DependencyStateRegistry",
    "UpstreamBadResponseError",
    "UpstreamUnavailableError",
    "build_dependency_check",
    "build_dependency_error_payload",
    "classify_postgres_exception",
    "dependency_state_registry",
    "mark_dependency_failure",
    "mark_dependency_success",
    "translate_instagram_upstream_exception",
    "translate_openai_exception",
    "translate_redis_exception",
    "translate_resend_exception",
]
