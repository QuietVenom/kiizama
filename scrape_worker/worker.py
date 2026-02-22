from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import ReturnDocument

from app.features.ig_scrapper.jobs import (
    JOB_COLLECTION_NAME,
    build_job_references,
    configure_jobs_collection_resolver,
    ensure_job_indexes,
    get_jobs_collection,
)
from app.features.ig_scrapper.schemas import (
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeSummaryResponse,
)
from app.features.ig_scrapper.service import (
    build_batch_scrape_summary,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
    scrape_profiles_batch,
)
from app.features.ig_scrapper.types.session_validator import (
    configure_credentials_collection_resolver,
)
from scrape_worker.config import settings
from scrape_worker.mongodb import (
    close_worker_mongo_client,
    get_worker_mongo_database,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_worker")


def _truncate_error(error: str) -> str:
    return error[: settings.max_error_length]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _lease_until(from_dt: datetime) -> datetime:
    return from_dt + timedelta(seconds=settings.lease_seconds)


def _stale_running_filter(now: datetime) -> dict[str, Any]:
    return {
        "status": "running",
        "$or": [
            {"leasedUntil": {"$lt": now}},
            {"leasedUntil": {"$exists": False}},
            {"leasedUntil": None},
        ],
    }


async def mark_exhausted_jobs() -> int:
    jobs = get_jobs_collection()
    now = _now_utc()
    result = await jobs.update_many(
        {
            "expiresAt": {"$gt": now},
            "attempts": {"$gte": settings.max_attempts},
            "$or": [
                {"status": "queued"},
                _stale_running_filter(now),
            ],
        },
        {
            "$set": {
                "status": "failed",
                "updatedAt": now,
                "error": _truncate_error(
                    "Max attempts reached before successful completion."
                ),
            },
            "$unset": {
                "leaseOwner": "",
                "leasedUntil": "",
                "heartbeatAt": "",
            },
        },
    )
    return int(result.modified_count)


async def reserve_next_job() -> dict[str, Any] | None:
    jobs = get_jobs_collection()
    now = _now_utc()
    return await jobs.find_one_and_update(
        filter={
            "expiresAt": {"$gt": now},
            "$and": [
                {
                    "$or": [
                        {"attempts": {"$lt": settings.max_attempts}},
                        {"attempts": {"$exists": False}},
                    ]
                },
                {
                    "$or": [
                        {"status": "queued"},
                        _stale_running_filter(now),
                    ]
                },
            ],
        },
        update={
            "$set": {
                "status": "running",
                "updatedAt": now,
                "leaseOwner": settings.worker_id,
                "leasedUntil": _lease_until(now),
                "heartbeatAt": now,
            },
            "$inc": {"attempts": 1},
        },
        sort=[("status", 1), ("createdAt", 1)],
        return_document=ReturnDocument.AFTER,
    )


async def renew_lease(job_id: str, lease_owner: str) -> bool:
    jobs = get_jobs_collection()
    now = _now_utc()
    result = await jobs.update_one(
        {"_id": job_id, "status": "running", "leaseOwner": lease_owner},
        {
            "$set": {
                "updatedAt": now,
                "heartbeatAt": now,
                "leasedUntil": _lease_until(now),
            }
        },
    )
    return result.matched_count == 1


async def maintain_heartbeat(
    job_id: str,
    lease_owner: str,
    *,
    lease_lost: asyncio.Event,
) -> None:
    try:
        while not lease_lost.is_set():
            await asyncio.sleep(settings.heartbeat_seconds)
            if lease_lost.is_set():
                return
            renewed = await renew_lease(job_id, lease_owner)
            if renewed:
                continue

            logger.warning(
                "Lease lost for job %s (owner=%s). The job will be retried by another worker.",
                job_id,
                lease_owner,
            )
            lease_lost.set()
            return
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - defensive worker resilience
        logger.exception(
            "Heartbeat failed for job %s (owner=%s): %s",
            job_id,
            lease_owner,
            exc,
        )
        lease_lost.set()


async def mark_done(
    job_id: str,
    *,
    lease_owner: str,
    summary: InstagramBatchScrapeSummaryResponse,
    error: str | None,
) -> bool:
    jobs = get_jobs_collection()
    now = _now_utc()
    references = build_job_references(summary)
    result = await jobs.update_one(
        {"_id": job_id, "status": "running", "leaseOwner": lease_owner},
        {
            "$set": {
                "status": "done",
                "updatedAt": now,
                "summary": summary.model_dump(mode="json"),
                "references": references.model_dump(mode="json"),
                "error": _truncate_error(error) if error else None,
            },
            "$unset": {
                "leaseOwner": "",
                "leasedUntil": "",
                "heartbeatAt": "",
            },
        },
    )
    return result.matched_count == 1


async def mark_failed(job_id: str, *, lease_owner: str, error: str) -> bool:
    jobs = get_jobs_collection()
    now = _now_utc()
    result = await jobs.update_one(
        {"_id": job_id, "status": "running", "leaseOwner": lease_owner},
        {
            "$set": {
                "status": "failed",
                "updatedAt": now,
                "error": _truncate_error(error),
            },
            "$unset": {
                "leaseOwner": "",
                "leasedUntil": "",
                "heartbeatAt": "",
            },
        },
    )
    return result.matched_count == 1


async def execute_job(
    job: dict[str, Any],
) -> tuple[InstagramBatchScrapeSummaryResponse, str | None]:
    payload = job.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Job payload is invalid.")

    request = InstagramBatchScrapeRequest.model_validate(payload)
    original_request = request.model_copy(deep=True)
    database = get_worker_mongo_database()

    profiles_collection = database.get_collection("profiles")
    posts_collection = database.get_collection("posts")
    reels_collection = database.get_collection("reels")
    metrics_collection = database.get_collection("metrics")
    snapshots_collection = database.get_collection("profile_snapshots")

    request, early_response = await prepare_scrape_batch_payload(
        request,
        profiles_collection,
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
    response = await enrich_with_ai_analysis(response)
    response = await persist_scrape_results_to_db(
        response,
        profiles_collection=profiles_collection,
        posts_collection=posts_collection,
        reels_collection=reels_collection,
        metrics_collection=metrics_collection,
        snapshots_collection=snapshots_collection,
    )

    summary = build_batch_scrape_summary(original_request, request, response=response)
    return summary, response.error or summary.error


async def worker_loop() -> None:
    database = get_worker_mongo_database()
    configure_jobs_collection_resolver(
        lambda: database.get_collection(JOB_COLLECTION_NAME)
    )
    configure_credentials_collection_resolver(
        lambda: database.get_collection("ig_credentials")
    )

    ping_response = await database.command("ping")
    if int(ping_response.get("ok", 0)) != 1:
        raise RuntimeError("Problem connecting to database cluster.")

    await ensure_job_indexes()
    logger.info(
        "Worker started. id=%s poll=%.2fs heartbeat=%.2fs lease=%ss max_attempts=%s",
        settings.worker_id,
        settings.poll_seconds,
        settings.heartbeat_seconds,
        settings.lease_seconds,
        settings.max_attempts,
    )

    while True:
        exhausted_count = await mark_exhausted_jobs()
        if exhausted_count:
            logger.warning("Marked %s exhausted jobs as failed.", exhausted_count)

        job = await reserve_next_job()
        if job is None:
            await asyncio.sleep(settings.poll_seconds)
            continue

        job_id = str(job["_id"])
        lease_owner = str(job.get("leaseOwner") or settings.worker_id)
        attempt = int(job.get("attempts", 0) or 0)
        logger.info(
            "Processing scrape job %s (attempt %s/%s, owner=%s)",
            job_id,
            attempt,
            settings.max_attempts,
            lease_owner,
        )

        lease_lost = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            maintain_heartbeat(job_id, lease_owner, lease_lost=lease_lost)
        )

        try:
            summary, error = await execute_job(job)
            if lease_lost.is_set():
                logger.warning(
                    "Skipping finalization for job %s because lease was lost.",
                    job_id,
                )
                continue

            marked = await mark_done(
                job_id,
                lease_owner=lease_owner,
                summary=summary,
                error=error,
            )
            if not marked:
                logger.warning(
                    "Could not mark job %s as done because lease is no longer owned.",
                    job_id,
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Scrape job %s failed: %s", job_id, exc)
            if lease_lost.is_set():
                logger.warning(
                    "Skipping failed finalization for job %s because lease was lost.",
                    job_id,
                )
                continue

            marked = await mark_failed(job_id, lease_owner=lease_owner, error=str(exc))
            if not marked:
                logger.warning(
                    "Could not mark job %s as failed because lease is no longer owned.",
                    job_id,
                )
        finally:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task


async def run() -> None:
    try:
        await worker_loop()
    finally:
        await close_worker_mongo_client()


__all__ = ["run", "worker_loop"]
