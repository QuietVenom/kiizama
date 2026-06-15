from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from kiizama_core.job_control.schemas import JobExecutionMode
from kiizama_scrape_core.ig_scraper_v2.jobs import (
    APIFY_JOB_EXECUTION_MODE,
    WORKER_JOB_EXECUTION_MODE,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchScrapeSummaryResponse,
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobCreateResponse,
)
from sqlmodel import Session

from app.features.billing import (
    FEATURE_ENDPOINT_KEYS,
    attach_job_id_to_reservation,
    build_usage_request_key,
    finalize_usage_reservation,
    publish_billing_event,
    release_usage_reservation,
    reserve_feature_usage,
)


class InstagramJobCreator(Protocol):
    async def create_job(
        self,
        *,
        payload: InstagramScrapeJobCreateRequest,
        owner_user_id: str,
        execution_mode: JobExecutionMode = WORKER_JOB_EXECUTION_MODE,
    ) -> str: ...


@dataclass(frozen=True)
class InstagramJobBillingPolicy:
    feature_code: str
    endpoint_key: str
    request_scope: str


IG_SCRAPER_BILLING_FEATURE_CODE = "ig_scraper_apify"
_BILLING_POLICIES: dict[JobExecutionMode, InstagramJobBillingPolicy] = {
    WORKER_JOB_EXECUTION_MODE: InstagramJobBillingPolicy(
        feature_code=IG_SCRAPER_BILLING_FEATURE_CODE,
        endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_worker"],
        request_scope="ig-scraper-worker",
    ),
    APIFY_JOB_EXECUTION_MODE: InstagramJobBillingPolicy(
        feature_code=IG_SCRAPER_BILLING_FEATURE_CODE,
        endpoint_key=FEATURE_ENDPOINT_KEYS["ig_scraper_apify"],
        request_scope="ig-scraper-apify",
    ),
}


def get_instagram_job_billing_policy(
    execution_mode: JobExecutionMode,
) -> InstagramJobBillingPolicy | None:
    return _BILLING_POLICIES.get(execution_mode)


async def create_billable_instagram_job(
    *,
    session: Session,
    job_service: InstagramJobCreator,
    payload: InstagramScrapeJobCreateRequest,
    owner_user_id: uuid.UUID,
    execution_mode: JobExecutionMode,
    idempotency_key: str | None,
) -> InstagramScrapeJobCreateResponse:
    policy = get_instagram_job_billing_policy(execution_mode)
    request_key: str | None = None
    if policy is not None:
        request_key = build_usage_request_key(
            user_id=owner_user_id,
            request_scope=policy.request_scope,
            idempotency_key=idempotency_key,
        )
        reservation = reserve_feature_usage(
            session=session,
            user_id=owner_user_id,
            feature_code=policy.feature_code,
            endpoint_key=policy.endpoint_key,
            max_units_requested=len(payload.usernames),
            request_key=request_key,
            metadata={
                "usernames": payload.usernames,
                "execution_mode": execution_mode,
            },
        )
        if reservation is not None and reservation.job_id:
            return InstagramScrapeJobCreateResponse(
                job_id=reservation.job_id,
                status="queued",
            )

    try:
        job_id = await job_service.create_job(
            payload=payload,
            owner_user_id=str(owner_user_id),
            execution_mode=execution_mode,
        )
    except Exception:
        if request_key is not None:
            release_usage_reservation(session=session, request_key=request_key)
            await publish_billing_event(
                session=session,
                user_id=owner_user_id,
                event_name="account.usage.updated",
            )
        raise

    if request_key is not None:
        attach_job_id_to_reservation(
            session=session,
            request_key=request_key,
            job_id=job_id,
        )
        await publish_billing_event(
            session=session,
            user_id=owner_user_id,
            event_name="account.usage.updated",
        )

    return InstagramScrapeJobCreateResponse(job_id=job_id, status="queued")


async def finalize_instagram_job_billing(
    *,
    session: Session,
    owner_user_id: uuid.UUID,
    job_id: str,
    execution_mode: JobExecutionMode,
    job_status: str,
    summary: InstagramBatchScrapeSummaryResponse,
) -> None:
    policy = get_instagram_job_billing_policy(execution_mode)
    if policy is None:
        return

    metadata = {
        "job_status": job_status,
        "execution_mode": execution_mode,
    }
    if summary.counters.successful > 0:
        finalize_usage_reservation(
            session=session,
            job_id=job_id,
            quantity_consumed=summary.counters.successful,
            metadata=metadata,
        )
    else:
        release_usage_reservation(
            session=session,
            job_id=job_id,
            metadata=metadata,
        )
    await publish_billing_event(
        session=session,
        user_id=owner_user_id,
        event_name="account.usage.updated",
    )


__all__ = [
    "IG_SCRAPER_BILLING_FEATURE_CODE",
    "InstagramJobBillingPolicy",
    "create_billable_instagram_job",
    "finalize_instagram_job_billing",
    "get_instagram_job_billing_policy",
]
