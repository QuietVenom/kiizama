from __future__ import annotations

import logging
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

from app.api.deps import (
    CurrentUser,
    get_current_active_superuser,
    get_metrics_collection,
    get_posts_collection,
    get_profile_snapshots_collection,
    get_profiles_collection,
    get_reels_collection,
)
from app.core.resilience import (
    mark_dependency_failure,
    mark_dependency_success,
    translate_instagram_upstream_exception,
)
from app.features.ig_scraper_jobs import InstagramJobServiceDep
from app.features.ig_scraper_runtime import (
    BackendInstagramProfileAnalysisService,
    BackendInstagramScrapePersistence,
    configure_backend_instagram_scraper_runtime,
)
from app.features.rate_limit import POLICIES, rate_limit

router = APIRouter(prefix="/ig-scraper", tags=["instagram"])
logger = logging.getLogger(__name__)


@router.post(
    "/jobs",
    response_model=InstagramScrapeJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit(POLICIES.jobs_write))],
)
async def create_instagram_scrape_job(
    payload: InstagramScrapeJobCreateRequest,
    current_user: CurrentUser,
    job_service: InstagramJobServiceDep,
) -> InstagramScrapeJobCreateResponse:
    """Enqueue an asynchronous Instagram scraping job."""
    job_id = await job_service.create_job(
        payload=payload,
        owner_user_id=str(current_user.id),
    )
    return InstagramScrapeJobCreateResponse(job_id=job_id, status="queued")


@router.get(
    "/jobs/{job_id}",
    response_model=InstagramScrapeJobStatusResponse,
    dependencies=[Depends(rate_limit(POLICIES.jobs_read))],
)
async def get_instagram_scrape_job(
    job_id: str,
    _current_user: CurrentUser,
    job_service: InstagramJobServiceDep,
) -> InstagramScrapeJobStatusResponse:
    """Fetch status and summary for a scraping job."""
    job = await job_service.get_job(job_id=job_id)
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

    try:
        response = await scrape_profiles_batch(payload)
    except Exception as exc:
        translated = translate_instagram_upstream_exception(exc)
        mark_dependency_failure(
            "instagram_upstream",
            context="ig-scraper-batch",
            detail=translated.detail,
            status="degraded",
            exc=exc,
        )
        raise translated from exc
    else:
        mark_dependency_success(
            "instagram_upstream",
            context="ig-scraper-batch",
            detail="Instagram upstream scrape completed successfully.",
        )

    response = await enrich_with_ai_analysis(
        response,
        analysis_service=analysis_service,
    )
    ai_errors = sorted(
        {
            ai_error
            for result in response.results.values()
            if (ai_error := getattr(result, "ai_error", None)) is not None
        }
    )
    if ai_errors:
        detail = f"AI enrichment skipped: {ai_errors[0]}"
        mark_dependency_failure(
            "openai",
            context="ig-scraper-ai-enrichment",
            detail=detail,
            status="degraded",
        )
        logger.warning("AI enrichment skipped for ig-scraper batch: %s", ai_errors[0])
    else:
        mark_dependency_success(
            "openai",
            context="ig-scraper-ai-enrichment",
            detail="OpenAI enrichment completed successfully.",
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
    try:
        response = await scrape_recommendations_batch(payload)
    except Exception as exc:
        translated = translate_instagram_upstream_exception(exc)
        mark_dependency_failure(
            "instagram_upstream",
            context="ig-scraper-recommendations",
            detail=translated.detail,
            status="degraded",
            exc=exc,
        )
        raise translated from exc
    mark_dependency_success(
        "instagram_upstream",
        context="ig-scraper-recommendations",
        detail="Instagram recommendations completed successfully.",
    )
    return response


__all__ = ["router"]
