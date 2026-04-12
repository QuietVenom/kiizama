from __future__ import annotations

import asyncio
import logging
import os
import socket
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any, Literal

from kiizama_scrape_core.ig_scraper.persistence import SqlInstagramScrapePersistence
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramProfileSchema,
    InstagramScrapeJobTerminalizationRequest,
)
from kiizama_scrape_core.ig_scraper.service import (
    build_batch_scrape_summary,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
)
from kiizama_scrape_core.ig_scraper.types import ApifyInstagramProfileScraper
from kiizama_scrape_core.job_control import JobControlUnavailableError, JobWorkerRuntime
from kiizama_scrape_core.job_control.schemas import QueuedJobMessage
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.features.ig_scraper_jobs.repository import SqlJobProjectionRepository
from app.features.ig_scraper_jobs.service import (
    InstagramJobService,
    get_instagram_apify_job_control_repository,
    get_instagram_job_control_repository,
    get_instagram_user_events_repository,
)
from app.features.ig_scraper_runtime import (
    BackendInstagramProfileAnalysisService,
    configure_backend_instagram_scraper_runtime,
)

logger = logging.getLogger(__name__)

TerminalJobStatus = Literal["done", "failed"]


def _build_worker_id() -> str:
    return f"{settings.IG_SCRAPER_APIFY_WORKER_ID}:{socket.gethostname()}:{os.getpid()}"


def _truncate_error(error: str) -> str:
    return error[:1000]


def _build_exhausted_summary(
    payload: dict[str, Any],
    *,
    error: str | None = None,
) -> InstagramBatchScrapeSummaryResponse:
    request = InstagramBatchScrapeRequest.model_validate(payload)
    return InstagramBatchScrapeSummaryResponse(
        usernames=[
            InstagramBatchUsernameStatus(
                username=username,
                status="failed",
                error=error,
            )
            for username in request.usernames
        ],
        counters=InstagramBatchCountersSchema(
            requested=len(request.usernames),
            failed=len(request.usernames),
        ),
        error=error or "Max attempts reached before successful completion.",
    )


def _is_dependency_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            JobControlUnavailableError,
            SQLAlchemyError,
            RedisError,
        ),
    )


class ApifyInstagramJobRunner:
    def __init__(self) -> None:
        self._worker_id = _build_worker_id()
        self._repository = get_instagram_apify_job_control_repository()
        self._runtime = JobWorkerRuntime(
            repository=self._repository,
            worker_id=self._worker_id,
            lease_seconds=settings.IG_SCRAPER_APIFY_LEASE_SECONDS,
            heartbeat_seconds=settings.IG_SCRAPER_APIFY_HEARTBEAT_SECONDS,
            poll_seconds=settings.IG_SCRAPER_APIFY_POLL_SECONDS,
            reclaimed_message_count=1,
            new_message_count=1,
        )
        self._stop_event = asyncio.Event()
        self._semaphore = asyncio.Semaphore(
            settings.IG_SCRAPER_APIFY_MAX_CONCURRENT_JOBS
        )
        self._loop_task: asyncio.Task[None] | None = None
        self._job_tasks: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        if self._loop_task is not None:
            return
        configure_backend_instagram_scraper_runtime()
        await self._runtime.ensure_consumer_group()
        self._loop_task = asyncio.create_task(self._run_loop())
        await asyncio.sleep(0)
        if self._loop_task.done():
            self._loop_task.result()
        logger.info("Apify Instagram job runner started.")

    @property
    def is_running(self) -> bool:
        return self._loop_task is not None and not self._loop_task.done()

    async def stop(self) -> None:
        self._stop_event.set()
        if self._loop_task is not None:
            self._loop_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._loop_task
        if self._job_tasks:
            for task in self._job_tasks:
                task.cancel()
            await asyncio.gather(*self._job_tasks, return_exceptions=True)
        logger.info("Apify Instagram job runner stopped.")

    async def _run_loop(self) -> None:
        dependency_backoff_seconds = settings.IG_SCRAPER_APIFY_POLL_SECONDS
        try:
            while not self._stop_event.is_set():
                await self._semaphore.acquire()
                if self._stop_event.is_set():
                    self._semaphore.release()
                    return

                try:
                    messages = await self._runtime.poll_messages()
                except asyncio.CancelledError:
                    self._semaphore.release()
                    raise
                except Exception as exc:
                    self._semaphore.release()
                    if _is_dependency_error(exc):
                        logger.warning(
                            "Apify job runner waiting on dependencies: %s", exc
                        )
                        await asyncio.sleep(dependency_backoff_seconds)
                        dependency_backoff_seconds = min(
                            dependency_backoff_seconds * 2,
                            30.0,
                        )
                        continue
                    logger.exception("Apify job runner failed to poll jobs: %s", exc)
                    await asyncio.sleep(settings.IG_SCRAPER_APIFY_POLL_SECONDS)
                    continue

                dependency_backoff_seconds = settings.IG_SCRAPER_APIFY_POLL_SECONDS
                if not messages:
                    self._semaphore.release()
                    continue

                task = asyncio.create_task(self._process_message(messages[0]))
                self._job_tasks.add(task)
                task.add_done_callback(self._finalize_job_task)
        except asyncio.CancelledError:
            raise

    def _finalize_job_task(self, task: asyncio.Task[None]) -> None:
        self._job_tasks.discard(task)
        self._semaphore.release()

    async def _process_message(self, message: QueuedJobMessage) -> None:
        handle = await self._runtime.start_job(message)
        if handle is None:
            return

        ack = False
        try:
            if handle.attempt > settings.IG_SCRAPER_APIFY_MAX_ATTEMPTS:
                summary = await self._build_terminal_failure_summary(
                    handle.message.payload,
                    error="Max attempts reached before successful completion.",
                )
                status: TerminalJobStatus = (
                    "failed" if summary.counters.failed > 0 else "done"
                )
                error = summary.error
            else:
                try:
                    summary, error = await self._execute_job_payload(
                        handle.message.payload
                    )
                    status = "done"
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "Apify scrape job %s failed on attempt %s/%s: %s",
                        handle.job_id,
                        handle.attempt,
                        settings.IG_SCRAPER_APIFY_MAX_ATTEMPTS,
                        exc,
                    )
                    if handle.attempt < settings.IG_SCRAPER_APIFY_MAX_ATTEMPTS:
                        return
                    error = _truncate_error(str(exc))
                    summary = await self._build_terminal_failure_summary(
                        handle.message.payload,
                        error=error,
                    )
                    status = "failed" if summary.counters.failed > 0 else "done"

            if handle.lease_lost.is_set():
                logger.warning(
                    "Skipping Apify job finalization for %s because lease was lost.",
                    handle.job_id,
                )
                return

            ack = await self._complete_job(
                job_id=handle.job_id,
                attempt=handle.attempt,
                status=status,
                summary=summary,
                error=error,
            )
        finally:
            await self._runtime.finish_job(handle, ack=ack)

    async def _execute_job_payload(
        self,
        payload: dict[str, Any],
    ) -> tuple[InstagramBatchScrapeSummaryResponse, str | None]:
        original_request = InstagramBatchScrapeRequest.model_validate(payload)
        request = original_request.model_copy(deep=True)

        with Session(engine) as session:
            persistence = SqlInstagramScrapePersistence(session=session)
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

            response = await self._scrape_profiles_batch(request)
            response = await enrich_with_ai_analysis(
                response,
                analysis_service=analysis_service,
            )
            response = await persist_scrape_results_to_db(
                response,
                persistence=persistence,
            )

            summary = build_batch_scrape_summary(
                original_request,
                request,
                response=response,
            )
            return summary, response.error or summary.error

    async def _build_terminal_failure_summary(
        self,
        payload: dict[str, Any],
        *,
        error: str,
    ) -> InstagramBatchScrapeSummaryResponse:
        original_request = InstagramBatchScrapeRequest.model_validate(payload)

        try:
            with Session(engine) as session:
                persistence = SqlInstagramScrapePersistence(session=session)
                scrape_request, early_response = await prepare_scrape_batch_payload(
                    original_request.model_copy(deep=True),
                    persistence,
                )
        except Exception:
            return _build_exhausted_summary(payload, error=error)

        if early_response is not None:
            return build_batch_scrape_summary(
                original_request,
                scrape_request,
                response=None,
                early_response=early_response,
            ).model_copy(update={"error": error})

        failed_response = InstagramBatchScrapeResponse(
            results={
                username: InstagramBatchProfileResult(
                    success=False,
                    error=error,
                    user=InstagramProfileSchema(username=username),
                )
                for username in scrape_request.usernames
            },
            counters=InstagramBatchCountersSchema(
                requested=len(scrape_request.usernames),
                failed=len(scrape_request.usernames),
            ),
            error=error,
        )
        return build_batch_scrape_summary(
            original_request,
            scrape_request,
            response=failed_response,
        )

    async def _scrape_profiles_batch(
        self,
        request: InstagramBatchScrapeRequest,
    ) -> InstagramBatchScrapeResponse:
        if not settings.APIFY_API_TOKEN:
            raise RuntimeError("APIFY_API_TOKEN is not configured.")

        scraper = ApifyInstagramProfileScraper(
            api_token=settings.APIFY_API_TOKEN,
            usernames=request.usernames,
            include_about_section=False,
        )
        return InstagramBatchScrapeResponse.model_validate(await scraper.run())

    async def _complete_job(
        self,
        *,
        job_id: str,
        attempt: int,
        status: TerminalJobStatus,
        summary: InstagramBatchScrapeSummaryResponse,
        error: str | None,
    ) -> bool:
        with Session(engine) as session:
            job_service = InstagramJobService(
                session=session,
                jobs_collection=SqlJobProjectionRepository(session=session),
                job_control_repositories={
                    "apify": self._repository,
                    "worker": get_instagram_job_control_repository(),
                },
                user_events_repository=get_instagram_user_events_repository(),
            )
            await job_service.complete_job(
                job_id=job_id,
                payload=InstagramScrapeJobTerminalizationRequest(
                    status=status,
                    attempt=attempt,
                    worker_id=self._worker_id,
                    completed_at=datetime.now(timezone.utc),
                    summary=summary,
                    error=error,
                ),
            )
        return True


__all__ = ["ApifyInstagramJobRunner"]
