from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlmodel import Session

from .executor import InstagramScrapeJobExecutionResult, InstagramScrapeJobExecutor
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
    result = await execute_scrape_job_payload_result(
        payload,
        session_factory=session_factory,
        scraper_backend=scraper_backend,
        analysis_service=analysis_service,
    )
    return result.summary, result.error


async def execute_scrape_job_payload_result(
    payload: dict[str, Any],
    *,
    session_factory: Callable[[], Session],
    scraper_backend: InstagramScraperBackend,
    analysis_service: InstagramProfileAnalysisService,
    collect_recommended_usernames: bool = False,
) -> InstagramScrapeJobExecutionResult:
    with session_factory() as session:
        persistence = SqlInstagramScrapePersistenceV2(session=session)
        executor = InstagramScrapeJobExecutor(
            scraper_backend=scraper_backend,
            persistence=persistence,
            analysis_service=analysis_service,
        )
        return await executor.execute(
            payload,
            collect_recommended_usernames=collect_recommended_usernames,
        )


__all__ = ["execute_scrape_job_payload", "execute_scrape_job_payload_result"]
