from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramScrapeJobTerminalizationRequest,
)
from kiizama_scrape_core.ig_scraper.service import (
    build_batch_scrape_summary,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
    scrape_profiles_batch,
)
from kiizama_scrape_core.ig_scraper.types.session_validator import (
    configure_credentials_store_resolver,
)

from app.features.ig_scraper_jobs import get_instagram_job_queue_spec
from app.features.ig_scraper_runtime import (
    BackendInstagramCredentialsStore,
    BackendInstagramProfileAnalysisService,
    BackendInstagramScrapePersistence,
)
from app.features.job_control import (
    JobControlRepository,
    JobWorkerRuntime,
    QueuedJobMessage,
)

from scrape_worker.backend_client import (
    ScrapeWorkerBackendClient,
    WorkerBackendCompletionResult,
)
from scrape_worker.config import WorkerSettings, get_settings
from scrape_worker.mongodb import (
    close_worker_mongo_client,
    get_worker_mongo_database,
)
from scrape_worker.redis import close_worker_redis_client, get_worker_redis_client
from scrape_worker.types import BackendCompletionPort, WorkerRuntimePort

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_worker")
TERMINAL_ACK_STATUS_CODES = frozenset({200, 409})


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


async def execute_job_payload(
    payload: dict[str, Any],
) -> tuple[InstagramBatchScrapeSummaryResponse, str | None]:
    request = InstagramBatchScrapeRequest.model_validate(payload)
    original_request = request.model_copy(deep=True)
    database = get_worker_mongo_database()

    profiles_collection = database.get_collection("profiles")
    posts_collection = database.get_collection("posts")
    reels_collection = database.get_collection("reels")
    metrics_collection = database.get_collection("metrics")
    snapshots_collection = database.get_collection("profile_snapshots")
    persistence = BackendInstagramScrapePersistence(
        profiles_collection=profiles_collection,
        posts_collection=posts_collection,
        reels_collection=reels_collection,
        metrics_collection=metrics_collection,
        snapshots_collection=snapshots_collection,
    )
    analysis_service = BackendInstagramProfileAnalysisService()

    request, early_response = await prepare_scrape_batch_payload(
        request,
        persistence,
    )
    if early_response is not None:
        summary = build_batch_scrape_summary(
            original_request,
            request,
            response=None,
            early_response=early_response,
        )
        return summary, summary.error

    response = await scrape_profiles_batch(request)
    response = await enrich_with_ai_analysis(
        response,
        analysis_service=analysis_service,
    )
    response = await persist_scrape_results_to_db(
        response,
        persistence=persistence,
    )

    summary = build_batch_scrape_summary(original_request, request, response=response)
    return summary, response.error or summary.error


async def process_message(
    *,
    runtime: WorkerRuntimePort,
    backend_client: BackendCompletionPort,
    message: QueuedJobMessage,
) -> None:
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
                summary, error = await execute_job_payload(handle.message.payload)
                status = "done"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Scrape job %s failed: %s", handle.job_id, exc)
                summary = _build_exhausted_summary(handle.message.payload).model_copy(
                    update={"error": _truncate_error(str(exc))}
                )
                error = _truncate_error(str(exc))
                status = "failed"

        if handle.lease_lost.is_set():
            logger.warning(
                "Skipping finalization for job %s because lease was lost.",
                handle.job_id,
            )
            return

        completion_result = await backend_client.complete_job(
            job_id=handle.job_id,
            payload=InstagramScrapeJobTerminalizationRequest(
                status=status,
                attempt=handle.attempt,
                worker_id=settings.worker_id,
                completed_at=datetime.now(timezone.utc),
                summary=summary,
                error=error,
            ),
        )
        ack = _should_ack_completion_result(completion_result)
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
    database = get_worker_mongo_database()
    configure_credentials_store_resolver(
        lambda: BackendInstagramCredentialsStore(
            lambda: database.get_collection("ig_credentials")
        )
    )

    ping_response = await database.command("ping")
    if int(ping_response.get("ok", 0)) != 1:
        raise RuntimeError("Problem connecting to database cluster.")

    redis = get_worker_redis_client()
    await redis.ping()

    repository = JobControlRepository(
        spec=get_instagram_job_queue_spec(),
        redis_provider=get_worker_redis_client,
    )
    runtime = JobWorkerRuntime(
        repository=repository,
        worker_id=settings.worker_id,
        lease_seconds=settings.lease_seconds,
        heartbeat_seconds=settings.heartbeat_seconds,
        poll_seconds=settings.poll_seconds,
    )
    await runtime.ensure_consumer_group()

    backend_client = ScrapeWorkerBackendClient(base_url=settings.backend_base_url)
    logger.info(
        "Worker started. id=%s poll=%.2fs heartbeat=%.2fs lease=%ss max_attempts=%s",
        settings.worker_id,
        settings.poll_seconds,
        settings.heartbeat_seconds,
        settings.lease_seconds,
        settings.max_attempts,
    )

    try:
        while True:
            try:
                messages = await runtime.poll_messages()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Failed to poll scrape jobs: %s", exc)
                await asyncio.sleep(settings.poll_seconds)
                continue

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
                    logger.exception(
                        "Unexpected worker failure while handling job %s: %s",
                        getattr(message, "job_id", "<unknown>"),
                        exc,
                    )
    finally:
        await backend_client.aclose()


async def run() -> None:
    try:
        await worker_loop()
    finally:
        await close_worker_redis_client()
        await close_worker_mongo_client()


__all__ = [
    "TERMINAL_ACK_STATUS_CODES",
    "_attempt_exhausted",
    "_should_ack_completion_result",
    "execute_job_payload",
    "process_message",
    "run",
    "worker_loop",
]
