from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    CurrentUser,
    get_current_active_superuser,
    get_metrics_collection,
    get_posts_collection,
    get_profile_snapshots_collection,
    get_profiles_collection,
    get_reels_collection,
)
from app.features.ig_scrapper.jobs import (
    create_scrape_job,
    get_scrape_job,
    serialize_job_document,
)
from app.features.ig_scrapper.schemas import (
    InstagramBatchRecommendationsRequest,
    InstagramBatchRecommendationsResponse,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeSummaryResponse,
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobCreateResponse,
    InstagramScrapeJobStatusResponse,
)
from app.features.ig_scrapper.service import (
    build_batch_scrape_summary,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
    scrape_profiles_batch,
    scrape_recommendations_batch,
)

router = APIRouter(prefix="/ig-scrapper", tags=["instagram"])


@router.post(
    "/jobs",
    response_model=InstagramScrapeJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_instagram_scrape_job(
    payload: InstagramScrapeJobCreateRequest,
    _current_user: CurrentUser,
) -> InstagramScrapeJobCreateResponse:
    """Enqueue an asynchronous Instagram scraping job."""
    job_id = await create_scrape_job(payload)
    return InstagramScrapeJobCreateResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=InstagramScrapeJobStatusResponse)
async def get_instagram_scrape_job(
    job_id: str,
    _current_user: CurrentUser,
) -> InstagramScrapeJobStatusResponse:
    """Fetch status and summary for a scraping job."""
    doc = await get_scrape_job(job_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scrape job not found.",
        )

    return serialize_job_document(doc)


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
    original_payload = payload
    payload, early_response = await prepare_scrape_batch_payload(
        payload,
        profiles_collection,
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
    response = await enrich_with_ai_analysis(response)

    response = await persist_scrape_results_to_db(
        response,
        profiles_collection=profiles_collection,
        posts_collection=posts_collection,
        reels_collection=reels_collection,
        metrics_collection=metrics_collection,
        snapshots_collection=snapshots_collection,
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
    return await scrape_recommendations_batch(payload)


__all__ = ["router"]
