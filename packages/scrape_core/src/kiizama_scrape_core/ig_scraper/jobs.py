from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from .schemas import (
    InstagramBatchScrapeSummaryResponse,
    InstagramScrapeJobReferences,
    InstagramScrapeJobStatusResponse,
)

JOB_COLLECTION_NAME = "ig_scrape_jobs"
JOB_TTL_HOURS = 24
JOB_STATUS_VALUES = {"queued", "running", "done", "failed"}
JobDocument = dict[str, Any]
JobsCollection = AsyncCollection[JobDocument]


async def ensure_job_indexes(jobs: JobsCollection) -> None:
    await jobs.create_index(
        [("expiresAt", 1)],
        expireAfterSeconds=0,
        name="ttl_ig_scrape_jobs_expires_at",
    )
    await jobs.create_index(
        [("ownerUserId", 1), ("createdAt", -1)],
        name="idx_ig_scrape_jobs_owner_created_at",
    )
    await jobs.create_index(
        [("status", 1), ("createdAt", 1)],
        name="idx_ig_scrape_jobs_status_created_at",
    )


def default_job_expires_at(*, reference_time: datetime | None = None) -> datetime:
    now = reference_time or datetime.now(timezone.utc)
    return now + timedelta(hours=JOB_TTL_HOURS)


def build_job_projection_document(
    *,
    job_id: str,
    owner_user_id: str,
    payload: dict[str, Any],
    created_at: datetime,
    expires_at: datetime,
) -> JobDocument:
    return {
        "_id": job_id,
        "ownerUserId": owner_user_id,
        "status": "queued",
        "createdAt": created_at,
        "updatedAt": created_at,
        "completedAt": None,
        "expiresAt": expires_at,
        "payload": payload,
        "summary": None,
        "references": None,
        "error": None,
        "notificationId": None,
    }


def build_job_references(
    summary: InstagramBatchScrapeSummaryResponse,
) -> InstagramScrapeJobReferences:
    references = InstagramScrapeJobReferences(
        all_usernames=[item.username for item in summary.usernames],
        successful_usernames=[
            item.username for item in summary.usernames if item.status == "success"
        ],
        failed_usernames=[
            item.username for item in summary.usernames if item.status == "failed"
        ],
        skipped_usernames=[
            item.username for item in summary.usernames if item.status == "skipped"
        ],
        not_found_usernames=[
            item.username for item in summary.usernames if item.status == "not_found"
        ],
    )
    return references


def serialize_job_document(doc: dict[str, Any]) -> InstagramScrapeJobStatusResponse:
    raw_status = doc.get("status")
    if raw_status not in JOB_STATUS_VALUES:
        raise ValueError(f"Invalid job status stored in job projection: {raw_status!r}")

    raw_summary = doc.get("summary")
    summary = (
        InstagramBatchScrapeSummaryResponse.model_validate(raw_summary)
        if isinstance(raw_summary, dict)
        else None
    )

    raw_references = doc.get("references")
    references = (
        InstagramScrapeJobReferences.model_validate(raw_references)
        if isinstance(raw_references, dict)
        else None
    )

    return InstagramScrapeJobStatusResponse(
        job_id=str(doc["_id"]),
        status=raw_status,
        created_at=doc["createdAt"],
        updated_at=doc["updatedAt"],
        expires_at=doc["expiresAt"],
        attempts=int(doc.get("attempts", 0) or 0),
        lease_owner=doc.get("worker_id"),
        leased_until=doc.get("leased_until"),
        heartbeat_at=doc.get("heartbeat_at"),
        summary=summary,
        references=references,
        error=doc.get("error"),
    )


__all__ = [
    "JOB_COLLECTION_NAME",
    "JOB_STATUS_VALUES",
    "build_job_projection_document",
    "default_job_expires_at",
    "ensure_job_indexes",
    "build_job_references",
    "serialize_job_document",
]
