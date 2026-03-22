from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchRecommendationsRequest,
    InstagramBatchRecommendationsResponse,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeSummaryResponse,
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobCreateResponse,
    InstagramScrapeJobStatusResponse,
)
from kiizama_scrape_core.ig_scraper.service import (
    build_batch_scrape_summary,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
    scrape_profiles_batch,
    scrape_recommendations_batch,
)
from kiizama_scrape_core.job_control.repository import JobControlUnavailableError

from app.api.deps import (
    CurrentUser,
    get_current_active_superuser,
    get_metrics_collection,
    get_posts_collection,
    get_profile_snapshots_collection,
    get_profiles_collection,
    get_reels_collection,
)
from app.features.ig_scraper_jobs import InstagramJobServiceDep
from app.features.ig_scraper_runtime import (
    BackendInstagramProfileAnalysisService,
    BackendInstagramScrapePersistence,
    configure_backend_instagram_scraper_runtime,
)

router = APIRouter(prefix="/ig-scraper", tags=["instagram"])


@router.post(
    "/jobs",
    response_model=InstagramScrapeJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_instagram_scrape_job(
    payload: InstagramScrapeJobCreateRequest,
    current_user: CurrentUser,
    job_service: InstagramJobServiceDep,
) -> InstagramScrapeJobCreateResponse:
    """Enqueue an asynchronous Instagram scraping job."""
    try:
        job_id = await job_service.create_job(
            payload=payload,
            owner_user_id=str(current_user.id),
        )
    except JobControlUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return InstagramScrapeJobCreateResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=InstagramScrapeJobStatusResponse)
async def get_instagram_scrape_job(
    job_id: str,
    _current_user: CurrentUser,
    job_service: InstagramJobServiceDep,
) -> InstagramScrapeJobStatusResponse:
    """Fetch status and summary for a scraping job."""
    try:
        job = await job_service.get_job(job_id=job_id)
    except JobControlUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scrape job not found.",
        )

    return job


@router.post(
    "/profiles/batch",
    response_model=InstagramBatchScrapeSummaryResponse,
    dependencies=[Depends(get_current_active_superuser)],
)
async def instagram_scrape_profiles_batch(
    payload: InstagramBatchScrapeRequest,
    profiles_collection: Any = Depends(get_profiles_collection),
    posts_collection: Any = Depends(get_posts_collection),
    reels_collection: Any = Depends(get_reels_collection),
    metrics_collection: Any = Depends(get_metrics_collection),
    snapshots_collection: Any = Depends(get_profile_snapshots_collection),
) -> InstagramBatchScrapeSummaryResponse:
    """Scrape multiple Instagram profiles using stored credentials/session."""
    configure_backend_instagram_scraper_runtime()
    persistence = BackendInstagramScrapePersistence(
        profiles_collection=profiles_collection,
        posts_collection=posts_collection,
        reels_collection=reels_collection,
        metrics_collection=metrics_collection,
        snapshots_collection=snapshots_collection,
    )
    analysis_service = BackendInstagramProfileAnalysisService()
    original_payload = payload
    payload, early_response = await prepare_scrape_batch_payload(
        payload,
        persistence,
    )
    if early_response is not None:
        return build_batch_scrape_summary(
            original_payload,
            payload,
            response=None,
            early_response=early_response,
        )

    response = await scrape_profiles_batch(payload)

    # Always enrich with OpenAI categories/roles
    response = await enrich_with_ai_analysis(
        response,
        analysis_service=analysis_service,
    )

    response = await persist_scrape_results_to_db(
        response,
        persistence=persistence,
    )

    return build_batch_scrape_summary(
        original_payload,
        payload,
        response=response,
    )


@router.post(
    "/profiles/recommendations",
    response_model=InstagramBatchRecommendationsResponse,
    dependencies=[Depends(get_current_active_superuser)],
)
# TEMP: Recommendations endpoint uses dedicated request schema to expose `recommended_limit`.
async def instagram_profiles_recommendations(
    payload: InstagramBatchRecommendationsRequest,
) -> InstagramBatchRecommendationsResponse:
    """Fetch recommended users for multiple Instagram profiles."""
    configure_backend_instagram_scraper_runtime()
    return await scrape_recommendations_batch(payload)


__all__ = ["router"]
