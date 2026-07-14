from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from .ports import (
    InstagramProfileAnalysisService,
    InstagramScrapePersistence,
    InstagramScraperBackend,
)
from .recommended_jobs import resolve_recommended_usernames_to_enqueue
from .schemas import InstagramBatchScrapeRequest, InstagramBatchScrapeSummaryResponse
from .service import (
    build_batch_scrape_summary,
    enrich_with_ai_analysis,
    persist_scrape_results_to_db,
    prepare_scrape_batch_payload,
)


@dataclass(frozen=True, slots=True)
class InstagramScrapeJobExecutionResult:
    summary: InstagramBatchScrapeSummaryResponse
    error: str | None
    recommended_usernames: list[str] = field(default_factory=list)

    def __iter__(self) -> Iterator[Any]:
        yield self.summary
        yield self.error


class InstagramScrapeJobExecutor:
    def __init__(
        self,
        *,
        scraper_backend: InstagramScraperBackend,
        persistence: InstagramScrapePersistence,
        analysis_service: InstagramProfileAnalysisService,
    ) -> None:
        self.scraper_backend = scraper_backend
        self.persistence = persistence
        self.analysis_service = analysis_service

    async def execute(
        self,
        payload: dict[str, Any],
        *,
        collect_recommended_usernames: bool = False,
    ) -> InstagramScrapeJobExecutionResult:
        original_request = InstagramBatchScrapeRequest.model_validate(payload)
        scrape_request, early_response = await prepare_scrape_batch_payload(
            original_request.model_copy(deep=True),
            self.persistence,
        )
        if early_response is not None:
            summary = build_batch_scrape_summary(
                original_request,
                scrape_request,
                response=None,
                early_response=early_response,
            )
            return InstagramScrapeJobExecutionResult(
                summary=summary,
                error=summary.error,
                recommended_usernames=[],
            )

        response = await self.scraper_backend.scrape(scrape_request)
        response = await enrich_with_ai_analysis(
            response,
            analysis_service=self.analysis_service,
        )
        response = await persist_scrape_results_to_db(
            response,
            persistence=self.persistence,
        )
        summary = build_batch_scrape_summary(
            original_request,
            scrape_request,
            response=response,
        )
        recommended_usernames = (
            await resolve_recommended_usernames_to_enqueue(
                response,
                persistence=self.persistence,
            )
            if collect_recommended_usernames
            else []
        )
        return InstagramScrapeJobExecutionResult(
            summary=summary,
            error=response.error or summary.error,
            recommended_usernames=recommended_usernames,
        )


__all__ = ["InstagramScrapeJobExecutionResult", "InstagramScrapeJobExecutor"]
