from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from kiizama_core.job_control import (
    JobControlRepository,
    JobControlUnavailableError,
    JobWorkerRuntime,
    QueuedJobMessage,
)
from kiizama_scrape_core.ig_scraper_v2 import (
    WORKER_JOB_EXECUTION_MODE,
    InstagramScraperV2Backend,
    OpenAIInstagramProfileAnalysisServiceV2,
    SqlInstagramCredentialsStoreV2,
    build_instagram_job_queue_spec,
    build_scraper_v2_config,
    execute_scrape_job_payload,
)
from kiizama_scrape_core.ig_scraper_v2.logging_utils import (
    format_counters,
    proxy_mode_label,
    sanitize_exception_for_log,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramScrapeJobTerminalizationRequest,
)
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from scrape_worker.backend_client import (
    ScrapeWorkerBackendClient,
    WorkerBackendCompletionResult,
)
from scrape_worker.config import WorkerSettings, get_settings
from scrape_worker.db import engine, ping_postgres
from scrape_worker.redis import close_worker_redis_client, get_worker_redis_client
from scrape_worker.types import BackendCompletionPort, WorkerRuntimePort

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_worker")
TERMINAL_ACK_STATUS_CODES = frozenset({200, 409})
MAX_DEPENDENCY_BACKOFF_SECONDS = 30.0


class WorkerDependencyUnavailableError(RuntimeError):
    """Raised when a transient external dependency is unavailable."""


def _settings() -> WorkerSettings:
    return get_settings()


def _truncate_error(error: str) -> str:
    return error[: _settings().max_error_length]


def _build_exhausted_summary(
    payload: dict[str, Any],
) -> InstagramBatchScrapeSummaryResponse:
    request = InstagramBatchScrapeRequest.model_validate(payload)
    return InstagramBatchScrapeSummaryResponse(
        usernames=[
            InstagramBatchUsernameStatus(username=username, status="failed")
            for username in request.usernames
        ],
        counters=InstagramBatchCountersSchema(
            requested=len(request.usernames),
            failed=len(request.usernames),
        ),
        error="Max attempts reached before successful completion.",
    )


def _attempt_exhausted(attempt: int) -> bool:
    return attempt > _settings().max_attempts


def _should_ack_completion_result(result: WorkerBackendCompletionResult) -> bool:
    return result.status_code in TERMINAL_ACK_STATUS_CODES


def _next_dependency_backoff_seconds(previous_delay: float | None) -> float:
    base_delay = _settings().poll_seconds
    if previous_delay is None:
        return base_delay
    return min(previous_delay * 2, MAX_DEPENDENCY_BACKOFF_SECONDS)


def _is_backend_dependency_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def _is_dependency_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            WorkerDependencyUnavailableError,
            JobControlUnavailableError,
            SQLAlchemyError,
            RedisError,
        ),
    ) or _is_backend_dependency_error(exc)


async def _ensure_worker_dependencies_ready(runtime: WorkerRuntimePort) -> None:
    try:
        await asyncio.to_thread(ping_postgres)
    except SQLAlchemyError as exc:
        raise WorkerDependencyUnavailableError(
            "Postgres is unavailable for scrape worker."
        ) from exc

    redis = get_worker_redis_client()
    try:
        await redis.ping()
        await runtime.ensure_consumer_group()
    except (JobControlUnavailableError, RedisError, RuntimeError) as exc:
        raise WorkerDependencyUnavailableError(
            "Redis is unavailable for scrape worker."
        ) from exc


async def execute_job_payload(
    payload: dict[str, Any],
    *,
    job_id: str | None = None,
) -> tuple[InstagramBatchScrapeSummaryResponse, str | None]:
    config = build_scraper_v2_config()
    usernames = payload.get("usernames", [])
    logger.info(
        "Starting IG v2 scrape runtime "
        "(job_id=%s, proxy_mode=%s, headless=%s, max_concurrent=%s, max_posts=%s, usernames=%s)",
        job_id or "unknown",
        proxy_mode_label(config),
        str(config.browser.headless).lower(),
        config.crawler.max_concurrent,
        config.max_posts,
        len(usernames) if isinstance(usernames, list) else 0,
    )
    credentials_store = SqlInstagramCredentialsStoreV2(lambda: Session(engine))
    scraper_backend = InstagramScraperV2Backend(
        config=config,
        credentials_store=credentials_store,
        logger=logger,
        job_id=job_id,
    )
    analysis_service = OpenAIInstagramProfileAnalysisServiceV2(
        api_key=_settings().openai_api_key
    )
    return await execute_scrape_job_payload(
        payload,
        session_factory=lambda: Session(engine),
        scraper_backend=scraper_backend,
        analysis_service=analysis_service,
    )


async def process_message(
    *,
    runtime: WorkerRuntimePort,
    backend_client: BackendCompletionPort,
    message: QueuedJobMessage,
) -> None:
    if message.execution_mode != WORKER_JOB_EXECUTION_MODE:
        logger.warning(
            "Ignoring job %s with execution_mode=%s in Playwright scrape worker. "
            "TODO: keep worker reserved for Playwright/login jobs only.",
            message.job_id,
            message.execution_mode,
        )

    settings = _settings()
    handle = await runtime.start_job(message)
    if handle is None:
        return

    ack = False
    try:
        logger.info(
            "Processing scrape job %s (attempt %s/%s, worker=%s)",
            handle.job_id,
            handle.attempt,
            settings.max_attempts,
            settings.worker_id,
        )
        if _attempt_exhausted(handle.attempt):
            logger.warning(
                "Job %s exceeded max attempts (%s > %s).",
                handle.job_id,
                handle.attempt,
                settings.max_attempts,
            )
            summary = _build_exhausted_summary(handle.message.payload)
            error = summary.error
            status = "failed"
        else:
            try:
                summary, error = await execute_job_payload(
                    handle.message.payload,
                    job_id=handle.job_id,
                )
                status = "done"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if _is_dependency_error(exc):
                    raise WorkerDependencyUnavailableError(
                        f"Dependency unavailable while executing job {handle.job_id}."
                    ) from exc
                sanitized_error = sanitize_exception_for_log(exc)
                logger.exception(
                    "Scrape job %s failed: %s",
                    handle.job_id,
                    sanitized_error,
                )
                summary = _build_exhausted_summary(handle.message.payload).model_copy(
                    update={"error": _truncate_error(sanitized_error)}
                )
                error = _truncate_error(sanitized_error)
                status = "failed"

        if handle.lease_lost.is_set():
            logger.warning(
                "Skipping finalization for job %s because lease was lost.",
                handle.job_id,
            )
            return

        try:
            completion_result = await backend_client.complete_job(
                job_id=handle.job_id,
                payload=InstagramScrapeJobTerminalizationRequest(
                    status=status,
                    attempt=handle.attempt,
                    worker_id=settings.worker_id,
                    completed_at=datetime.now(UTC),
                    summary=summary,
                    error=error,
                ),
            )
        except Exception as exc:
            if _is_dependency_error(exc):
                raise WorkerDependencyUnavailableError(
                    f"Dependency unavailable while finalizing job {handle.job_id}."
                ) from exc
            raise
        ack = _should_ack_completion_result(completion_result)
        logger.info(
            "Completed scrape job %s (status=%s, ack=%s, counters=%s)",
            handle.job_id,
            status,
            str(ack).lower(),
            format_counters(summary.counters),
        )
        if not ack:
            logger.warning(
                "Backend completion for job %s returned %s; leaving message pending.",
                handle.job_id,
                completion_result.status_code,
            )
    finally:
        await runtime.finish_job(handle, ack=ack)


async def worker_loop() -> None:
    settings = _settings()

    repository = JobControlRepository(
        spec=build_instagram_job_queue_spec(
            state_ttl_seconds=settings.job_control_terminal_state_ttl_seconds,
            queue_maxlen=settings.job_control_queue_maxlen,
        ),
        redis_provider=get_worker_redis_client,
    )
    runtime = JobWorkerRuntime(
        repository=repository,
        worker_id=settings.worker_id,
        lease_seconds=settings.lease_seconds,
        heartbeat_seconds=settings.heartbeat_seconds,
        poll_seconds=settings.poll_seconds,
    )

    backend_client = ScrapeWorkerBackendClient(base_url=settings.backend_base_url)
    logger.info(
        "Worker started. id=%s poll=%.2fs heartbeat=%.2fs lease=%ss max_attempts=%s",
        settings.worker_id,
        settings.poll_seconds,
        settings.heartbeat_seconds,
        settings.lease_seconds,
        settings.max_attempts,
    )

    dependency_backoff_seconds: float | None = None

    async def enter_degraded_mode(exc: Exception, *, context: str) -> None:
        nonlocal dependency_backoff_seconds

        delay = _next_dependency_backoff_seconds(dependency_backoff_seconds)
        if dependency_backoff_seconds is None:
            logger.exception(
                "Worker entering degraded mode while %s. Retrying in %.2fs.",
                context,
                delay,
            )
        else:
            logger.warning(
                "Worker still waiting on dependencies while %s. Retrying in %.2fs: %s",
                context,
                delay,
                exc,
            )
        dependency_backoff_seconds = delay
        await asyncio.sleep(delay)

    def reset_degraded_mode() -> None:
        nonlocal dependency_backoff_seconds
        if dependency_backoff_seconds is None:
            return
        logger.info("Worker dependencies recovered. Resuming scrape job polling.")
        dependency_backoff_seconds = None

    try:
        while True:
            try:
                await _ensure_worker_dependencies_ready(runtime)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if _is_dependency_error(exc):
                    await enter_degraded_mode(
                        exc,
                        context="verifying worker dependencies",
                    )
                    continue
                raise
            break

        while True:
            try:
                messages = await runtime.poll_messages()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if _is_dependency_error(exc):
                    await enter_degraded_mode(exc, context="polling scrape jobs")
                    continue
                logger.exception("Failed to poll scrape jobs: %s", exc)
                await asyncio.sleep(settings.poll_seconds)
                continue

            dependency_failure = False
            for message in messages:
                try:
                    await process_message(
                        runtime=runtime,
                        backend_client=backend_client,
                        message=message,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    if _is_dependency_error(exc):
                        dependency_failure = True
                        await enter_degraded_mode(
                            exc,
                            context=(
                                f"handling scrape job "
                                f"{getattr(message, 'job_id', '<unknown>')}"
                            ),
                        )
                        break
                    logger.exception(
                        "Unexpected worker failure while handling job %s: %s",
                        getattr(message, "job_id", "<unknown>"),
                        exc,
                    )
            if dependency_failure:
                continue

            reset_degraded_mode()
    finally:
        await backend_client.aclose()


async def run() -> None:
    try:
        await worker_loop()
    finally:
        await close_worker_redis_client()


__all__ = [
    "TERMINAL_ACK_STATUS_CODES",
    "_attempt_exhausted",
    "_ensure_worker_dependencies_ready",
    "_is_backend_dependency_error",
    "_is_dependency_error",
    "_next_dependency_backoff_seconds",
    "_should_ack_completion_result",
    "execute_job_payload",
    "process_message",
    "run",
    "WorkerDependencyUnavailableError",
    "worker_loop",
]
