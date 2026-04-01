from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from kiizama_scrape_core.job_control.schemas import JobExecutionMode, JobQueueSpec

from .schemas import (
    InstagramBatchScrapeSummaryResponse,
    InstagramScrapeJobReferences,
    InstagramScrapeJobStatusResponse,
)

JOB_COLLECTION_NAME = "ig_scrape_jobs"
JOB_TTL_HOURS = 24
JOB_STATUS_VALUES = {"queued", "running", "done", "failed"}
WORKER_JOB_EXECUTION_MODE: JobExecutionMode = "worker"
APIFY_JOB_EXECUTION_MODE: JobExecutionMode = "apify"
JOB_EXECUTION_MODE_VALUES = {
    WORKER_JOB_EXECUTION_MODE,
    APIFY_JOB_EXECUTION_MODE,
}
JOB_QUEUE_DOMAIN_BY_EXECUTION_MODE: dict[JobExecutionMode, str] = {
    WORKER_JOB_EXECUTION_MODE: "ig-scrape",
    APIFY_JOB_EXECUTION_MODE: "ig-scrape-apify",
}
JobDocument = dict[str, Any]


def build_instagram_job_queue_spec(
    state_ttl_seconds: int,
    queue_maxlen: int,
    *,
    execution_mode: JobExecutionMode = WORKER_JOB_EXECUTION_MODE,
) -> JobQueueSpec:
    return JobQueueSpec(
        domain=JOB_QUEUE_DOMAIN_BY_EXECUTION_MODE[execution_mode],
        execution_mode=execution_mode,
        state_ttl_seconds=state_ttl_seconds,
        queue_maxlen=queue_maxlen,
    )


def default_job_expires_at(*, reference_time: datetime | None = None) -> datetime:
    now = reference_time or datetime.now(timezone.utc)
    return now + timedelta(hours=JOB_TTL_HOURS)


def build_job_projection_document(
    *,
    job_id: str,
    owner_user_id: str,
    payload: dict[str, Any],
    execution_mode: JobExecutionMode,
    created_at: datetime,
    expires_at: datetime,
) -> JobDocument:
    return {
        "_id": job_id,
        "ownerUserId": owner_user_id,
        "executionMode": execution_mode,
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

    raw_execution_mode = doc.get("executionMode") or WORKER_JOB_EXECUTION_MODE
    if raw_execution_mode not in JOB_EXECUTION_MODE_VALUES:
        raise ValueError(
            "Invalid job execution mode stored in job projection: "
            f"{raw_execution_mode!r}"
        )

    return InstagramScrapeJobStatusResponse(
        job_id=str(doc["_id"]),
        execution_mode=raw_execution_mode,
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
    "APIFY_JOB_EXECUTION_MODE",
    "JOB_COLLECTION_NAME",
    "JOB_EXECUTION_MODE_VALUES",
    "JOB_QUEUE_DOMAIN_BY_EXECUTION_MODE",
    "JOB_STATUS_VALUES",
    "WORKER_JOB_EXECUTION_MODE",
    "build_instagram_job_queue_spec",
    "build_job_projection_document",
    "default_job_expires_at",
    "build_job_references",
    "serialize_job_document",
]
