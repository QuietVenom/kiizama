from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramScrapeJobTerminalizationRequest,
    InstagramScrapeJobTerminalizationResponse,
)

from app.api.deps import CurrentSystemAdminAuth
from app.features.ig_scraper_jobs import InstagramJobServiceDep

router = APIRouter(prefix="/internal/ig-scraper", tags=["internal-instagram"])


@router.post(
    "/jobs/{job_id}/complete",
    response_model=InstagramScrapeJobTerminalizationResponse,
)
async def complete_instagram_scrape_job(
    job_id: str,
    payload: InstagramScrapeJobTerminalizationRequest,
    _current_admin: CurrentSystemAdminAuth,
    job_service: InstagramJobServiceDep,
) -> InstagramScrapeJobTerminalizationResponse:
    response = await job_service.complete_job(job_id=job_id, payload=payload)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scrape job not found.",
        )
    if response.decision == "conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=response.model_dump(mode="json"),
        )
    return response


__all__ = ["router", "complete_instagram_scrape_job"]
