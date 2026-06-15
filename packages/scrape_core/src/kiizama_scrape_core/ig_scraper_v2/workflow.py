from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlmodel import Session

from .executor import InstagramScrapeJobExecutor
from .persistence import SqlInstagramScrapePersistenceV2
from .ports import InstagramProfileAnalysisService, InstagramScraperBackend
from .schemas import InstagramBatchScrapeSummaryResponse


async def execute_scrape_job_payload(
    payload: dict[str, Any],
    *,
    session_factory: Callable[[], Session],
    scraper_backend: InstagramScraperBackend,
    analysis_service: InstagramProfileAnalysisService,
) -> tuple[InstagramBatchScrapeSummaryResponse, str | None]:
    with session_factory() as session:
        persistence = SqlInstagramScrapePersistenceV2(session=session)
        executor = InstagramScrapeJobExecutor(
            scraper_backend=scraper_backend,
            persistence=persistence,
            analysis_service=analysis_service,
        )
        result = await executor.execute(payload)
        return result.summary, result.error


__all__ = ["execute_scrape_job_payload"]
