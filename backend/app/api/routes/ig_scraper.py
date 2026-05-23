from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from kiizama_scrape_core.ig_scraper_v2 import ApifyInstagramProfileScraper
from kiizama_scrape_core.ig_scraper_v2.jobs import (
    APIFY_JOB_EXECUTION_MODE,
    WORKER_JOB_EXECUTION_MODE,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramPublicScrapeRequest,
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobCreateResponse,
    InstagramScrapeJobStatusResponse,
)
from kiizama_scrape_core.ig_scraper_v2.service import (
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
)

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
    get_metrics_collection,
    get_posts_collection,
    get_profile_snapshots_collection,
    get_profiles_collection,
    get_reels_collection,
)
from app.core.config import settings
from app.features.billing import IDEMPOTENCY_HEADER_NAME
from app.features.ig_scraper_jobs import InstagramJobServiceDep
from app.features.ig_scraper_jobs.billing import create_billable_instagram_job
from app.features.ig_scraper_v2_runtime import (
    BackendInstagramProfileAnalysisServiceV2,
    BackendInstagramScrapePersistenceV2,
)
from app.features.rate_limit import POLICIES, rate_limit

router = APIRouter(prefix="/ig-scraper", tags=["instagram"])


@router.post(
    "/jobs",
    response_model=InstagramScrapeJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit(POLICIES.jobs_write))],
)
async def create_instagram_scrape_job(
    payload: InstagramScrapeJobCreateRequest,
    current_user: CurrentUser,
    session: SessionDep,
    job_service: InstagramJobServiceDep,
    idempotency_key: Annotated[
        str | None, Header(alias=IDEMPOTENCY_HEADER_NAME)
    ] = None,
) -> InstagramScrapeJobCreateResponse:
    """Enqueue an asynchronous Instagram scraping job."""
    if not settings.IG_SCRAPER_WORKER_JOBS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legacy worker Instagram jobs are disabled.",
        )

    return await create_billable_instagram_job(
        session=session,
        job_service=job_service,
        payload=payload,
        owner_user_id=current_user.id,
        execution_mode=WORKER_JOB_EXECUTION_MODE,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/jobs/apify",
    response_model=InstagramScrapeJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit(POLICIES.jobs_write))],
)
async def create_instagram_apify_scrape_job(
    payload: InstagramScrapeJobCreateRequest,
    current_user: CurrentUser,
    session: SessionDep,
    job_service: InstagramJobServiceDep,
    idempotency_key: Annotated[
        str | None, Header(alias=IDEMPOTENCY_HEADER_NAME)
    ] = None,
) -> InstagramScrapeJobCreateResponse:
    """Enqueue an asynchronous Instagram scraping job."""
    if not settings.IG_SCRAPER_APIFY_JOBS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Instagram scraping jobs are disabled.",
        )
    if not settings.APIFY_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="APIFY_API_TOKEN is not configured.",
        )

    return await create_billable_instagram_job(
        session=session,
        job_service=job_service,
        payload=payload,
        owner_user_id=current_user.id,
        execution_mode=APIFY_JOB_EXECUTION_MODE,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=InstagramScrapeJobStatusResponse,
    dependencies=[Depends(rate_limit(POLICIES.jobs_read))],
)
async def get_instagram_scrape_job(
    job_id: str,
    current_user: CurrentUser,
    job_service: InstagramJobServiceDep,
) -> InstagramScrapeJobStatusResponse:
    """Fetch status and summary for a scraping job."""
    job = await job_service.get_job(
        job_id=job_id,
        owner_user_id=str(current_user.id),
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scrape job not found.",
        )

    return job


@router.post(
    "/profiles/apify-batch",
    response_model=InstagramBatchScrapeResponse,
    dependencies=[Depends(get_current_active_superuser)],
)
async def instagram_scrape_profiles_apify_batch(
    payload: InstagramPublicScrapeRequest,
    profiles_collection: Any = Depends(get_profiles_collection),
    posts_collection: Any = Depends(get_posts_collection),
    reels_collection: Any = Depends(get_reels_collection),
    metrics_collection: Any = Depends(get_metrics_collection),
    snapshots_collection: Any = Depends(get_profile_snapshots_collection),
) -> InstagramBatchScrapeResponse:
    """Scrape multiple Instagram profiles and persist fresh results."""
    if not settings.APIFY_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="APIFY_API_TOKEN is not configured.",
        )

    persistence = BackendInstagramScrapePersistenceV2(
        profiles_collection=profiles_collection,
        posts_collection=posts_collection,
        reels_collection=reels_collection,
        metrics_collection=metrics_collection,
        snapshots_collection=snapshots_collection,
    )
    analysis_service = BackendInstagramProfileAnalysisServiceV2()
    scrape_payload = InstagramBatchScrapeRequest(usernames=payload.usernames)
    prepared_payload, early_response = await prepare_scrape_batch_payload(
        scrape_payload,
        persistence,
    )
    if early_response is not None:
        return early_response

    scraper = ApifyInstagramProfileScraper(
        api_token=settings.APIFY_API_TOKEN,
        usernames=prepared_payload.usernames,
    )
    response = InstagramBatchScrapeResponse.model_validate(await scraper.run())
    response = await enrich_with_ai_analysis(
        response,
        analysis_service=analysis_service,
    )
    return await persist_scrape_results_to_db(
        response,
        persistence=persistence,
    )


__all__ = ["router"]
