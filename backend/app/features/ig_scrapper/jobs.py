from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from app.features.ig_scrapper.schemas import (
    InstagramBatchScrapeSummaryResponse,
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobReferences,
    InstagramScrapeJobStatusResponse,
)

JOB_COLLECTION_NAME = "ig_scrape_jobs"
JOB_TTL_HOURS = 24
JOB_STATUS_VALUES = {"queued", "running", "done", "failed"}
_jobs_collection_resolver: Callable[[], Any] | None = None


def configure_jobs_collection_resolver(
    resolver: Callable[[], Any] | None,
) -> None:
    global _jobs_collection_resolver
    _jobs_collection_resolver = resolver


def get_jobs_collection():
    if _jobs_collection_resolver is not None:
        return _jobs_collection_resolver()

    from app.core.mongodb import get_mongo_kiizama_ig

    database = get_mongo_kiizama_ig()
    return database.get_collection(JOB_COLLECTION_NAME)


async def ensure_job_indexes() -> None:
    jobs = get_jobs_collection()
    await jobs.create_index(
        [("expiresAt", 1)],
        expireAfterSeconds=0,
        name="ttl_ig_scrape_jobs_expires_at",
    )
    await jobs.create_index(
        [("status", 1), ("createdAt", 1)],
        name="idx_ig_scrape_jobs_status_created_at",
    )
    await jobs.create_index(
        [("status", 1), ("leasedUntil", 1), ("createdAt", 1)],
        name="idx_ig_scrape_jobs_status_leased_until_created_at",
    )


async def create_scrape_job(payload: InstagramScrapeJobCreateRequest) -> str:
    now = datetime.now(timezone.utc)
    job_id = str(uuid.uuid4())
    jobs = get_jobs_collection()

    await jobs.insert_one(
        {
            "_id": job_id,
            "status": "queued",
            "createdAt": now,
            "updatedAt": now,
            "expiresAt": now + timedelta(hours=JOB_TTL_HOURS),
            "payload": payload.model_dump(mode="json"),
            "attempts": 0,
            "leaseOwner": None,
            "leasedUntil": None,
            "heartbeatAt": None,
            "summary": None,
            "references": None,
            "error": None,
        }
    )

    return job_id


async def get_scrape_job(job_id: str) -> dict[str, Any] | None:
    jobs = get_jobs_collection()
    return await jobs.find_one({"_id": job_id}, {"payload": 0})


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
        raise ValueError(f"Invalid job status stored in MongoDB: {raw_status!r}")

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
        lease_owner=doc.get("leaseOwner"),
        leased_until=doc.get("leasedUntil"),
        heartbeat_at=doc.get("heartbeatAt"),
        summary=summary,
        references=references,
        error=doc.get("error"),
    )


__all__ = [
    "JOB_COLLECTION_NAME",
    "JOB_STATUS_VALUES",
    "configure_jobs_collection_resolver",
    "ensure_job_indexes",
    "get_jobs_collection",
    "create_scrape_job",
    "get_scrape_job",
    "build_job_references",
    "serialize_job_document",
]
