from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Literal

from .ports import InstagramProfileAnalysisService, InstagramScrapePersistence
from .schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchRecommendationsRequest,
    InstagramBatchRecommendationsResponse,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramSuggestedUserSchema,
)
from .utils import should_refresh_profile

NOT_FOUND_ERROR = "Instagram username does not exist"
INSTAGRAM_USERNAME_RE = re.compile(r"^(?!.*\.\.)(?!\.)(?!.*\.$)[a-z0-9._]{1,30}$")


def _normalize_usernames(usernames: list[str]) -> list[str]:
    return [
        username.strip().lower()
        for username in usernames
        if username and username.strip()
    ]


def _is_valid_instagram_username(username: str) -> bool:
    return bool(INSTAGRAM_USERNAME_RE.fullmatch(username))


def _dedupe_suggested_users(
    users: list[InstagramSuggestedUserSchema],
) -> list[InstagramSuggestedUserSchema]:
    deduped: list[InstagramSuggestedUserSchema] = []
    seen: set[str] = set()
    for user in users:
        if user.id:
            key = f"id:{user.id.strip()}"
        elif user.username:
            key = f"username:{user.username.strip().lower()}"
        else:
            deduped.append(user)
            continue

        if key in seen:
            continue
        seen.add(key)
        deduped.append(user)
    return deduped


BatchUsernameStatus = Literal["success", "failed", "skipped", "not_found"]


async def prepare_scrape_batch_payload(
    payload: InstagramBatchScrapeRequest,
    persistence: InstagramScrapePersistence,
) -> tuple[InstagramBatchScrapeRequest, InstagramBatchScrapeResponse | None]:
    requested_usernames = _normalize_usernames(payload.usernames)
    if not requested_usernames:
        return payload, InstagramBatchScrapeResponse(
            counters=InstagramBatchCountersSchema(requested=0)
        )

    existing_profiles = await persistence.get_profiles_by_usernames(requested_usernames)
    existing_profiles_by_username = {
        profile.get("username", "").lower(): profile
        for profile in existing_profiles
        if profile.get("username")
    }
    usernames_to_scrape = [
        username
        for username in requested_usernames
        if should_refresh_profile(existing_profiles_by_username.get(username))
    ]
    if not usernames_to_scrape:
        return payload, InstagramBatchScrapeResponse(
            counters=InstagramBatchCountersSchema(requested=0)
        )

    return payload.model_copy(update={"usernames": usernames_to_scrape}), None


# TEMP: Recommendations flow uses a dedicated payload model with `recommended_limit`.
def prepare_recommendations_batch_payload(
    payload: InstagramBatchRecommendationsRequest,
) -> tuple[
    InstagramBatchRecommendationsRequest,
    list[InstagramBatchUsernameStatus],
    InstagramBatchRecommendationsResponse | None,
]:
    usernames_to_scrape: list[str] = []
    skipped: list[InstagramBatchUsernameStatus] = []
    seen: set[str] = set()

    for username_raw in payload.usernames:
        normalized = username_raw.strip().lower() if username_raw else ""

        # Ignore duplicates silently (first occurrence wins).
        if normalized in seen:
            continue
        seen.add(normalized)

        if not normalized:
            skipped.append(
                InstagramBatchUsernameStatus(
                    username=normalized,
                    status="skipped",
                    error="Empty username",
                )
            )
            continue

        if not _is_valid_instagram_username(normalized):
            skipped.append(
                InstagramBatchUsernameStatus(
                    username=normalized,
                    status="skipped",
                    error="Invalid username format",
                )
            )
            continue

        usernames_to_scrape.append(normalized)

    prepared_payload = payload.model_copy(update={"usernames": usernames_to_scrape})
    if usernames_to_scrape:
        return prepared_payload, skipped, None

    return (
        prepared_payload,
        skipped,
        InstagramBatchRecommendationsResponse(
            usernames=skipped,
            recommendations={},
            counters=InstagramBatchCountersSchema(requested=0),
            error=None,
        ),
    )


def build_batch_scrape_summary(
    payload: InstagramBatchScrapeRequest,
    scrape_payload: InstagramBatchScrapeRequest,
    response: InstagramBatchScrapeResponse | None,
    *,
    early_response: InstagramBatchScrapeResponse | None = None,
) -> InstagramBatchScrapeSummaryResponse:
    original_usernames = _normalize_usernames(payload.usernames)
    scraped_usernames = _normalize_usernames(scrape_payload.usernames)
    scraped_set = set(scraped_usernames)
    if response is None and early_response is not None:
        scraped_set = set()

    usernames: list[InstagramBatchUsernameStatus] = []
    for username in original_usernames:
        if username in scraped_set:
            status: BatchUsernameStatus = "failed"
            if response and username in response.results:
                result = response.results[username]
                if result.success:
                    status = "success"
                elif result.error == NOT_FOUND_ERROR:
                    status = "not_found"
                else:
                    status = "failed"
            usernames.append(
                InstagramBatchUsernameStatus(username=username, status=status)
            )
        else:
            usernames.append(
                InstagramBatchUsernameStatus(username=username, status="skipped")
            )

    counters_source = response or early_response
    counters = (
        counters_source.counters
        if counters_source
        else InstagramBatchCountersSchema(requested=0)
    )
    error = counters_source.error if counters_source else None

    return InstagramBatchScrapeSummaryResponse(
        usernames=usernames,
        counters=counters,
        error=error,
    )


def build_batch_recommendations_summary(
    payload: InstagramBatchRecommendationsRequest,
    response: InstagramBatchScrapeResponse | None,
    *,
    prevalidated_usernames: list[InstagramBatchUsernameStatus] | None = None,
    early_response: InstagramBatchRecommendationsResponse | None = None,
) -> InstagramBatchRecommendationsResponse:
    usernames = list(prevalidated_usernames or [])
    recommendations: dict[str, list[InstagramSuggestedUserSchema]] = {}

    normalized = _normalize_usernames(payload.usernames)
    for username in normalized:
        status: BatchUsernameStatus = "failed"
        error: str | None = None
        users: list[InstagramSuggestedUserSchema] = []

        if response and username in response.results:
            result = response.results[username]
            users = _dedupe_suggested_users(result.recommended_users)
            if result.success:
                status = "success"
            elif result.error == NOT_FOUND_ERROR:
                status = "not_found"
                error = result.error
            else:
                status = "failed"
                error = result.error
        else:
            error = response.error if response else None

        usernames.append(
            InstagramBatchUsernameStatus(
                username=username,
                status=status,
                error=error,
            )
        )
        recommendations[username] = users

    source = early_response
    if source is None and response is not None:
        source = InstagramBatchRecommendationsResponse(
            usernames=[],
            recommendations={},
            counters=response.counters,
            error=response.error,
        )
    if source is None:
        source = InstagramBatchRecommendationsResponse(
            usernames=[],
            recommendations={},
            counters=InstagramBatchCountersSchema(requested=0),
            error=None,
        )

    return InstagramBatchRecommendationsResponse(
        usernames=usernames,
        recommendations=recommendations
        if response is not None
        else source.recommendations,
        counters=source.counters,
        error=source.error,
    )


class InstagramScraperService:
    """Service class with dependency injection for Instagram scraping."""

    def __init__(
        self,
        batch_scraper_factory: Callable[[InstagramBatchScrapeRequest], Any],
        recommendations_factory: Callable[[InstagramBatchRecommendationsRequest], Any],
    ):
        self.batch_scraper_factory = batch_scraper_factory
        self.recommendations_factory = recommendations_factory

    def _ensure_batch_request(
        self, data: InstagramBatchScrapeRequest | dict[str, Any]
    ) -> InstagramBatchScrapeRequest:
        if isinstance(data, InstagramBatchScrapeRequest):
            return data
        return InstagramBatchScrapeRequest(**data)

    # TEMP: Keep recommendations payload parsing separate from snapshot payloads.
    def _ensure_recommendations_request(
        self, data: InstagramBatchRecommendationsRequest | dict[str, Any]
    ) -> InstagramBatchRecommendationsRequest:
        if isinstance(data, InstagramBatchRecommendationsRequest):
            return data
        return InstagramBatchRecommendationsRequest(**data)

    async def scrape_profiles_batch(
        self, payload: InstagramBatchScrapeRequest | dict[str, Any]
    ) -> InstagramBatchScrapeResponse:
        """Scrape multiple Instagram profiles concurrently with controlled parallelism."""
        request = self._ensure_batch_request(payload)
        batch_scraper = self.batch_scraper_factory(request)
        result = await batch_scraper.run()
        return InstagramBatchScrapeResponse.model_validate(result)

    async def scrape_recommendations_batch(
        self, payload: InstagramBatchRecommendationsRequest | dict[str, Any]
    ) -> InstagramBatchRecommendationsResponse:
        """Scrape profiles but return only the recommended users per account."""
        request = self._ensure_recommendations_request(payload)
        (
            request,
            prevalidated_usernames,
            early_response,
        ) = prepare_recommendations_batch_payload(request)
        if early_response is not None:
            return early_response

        batch_scraper = self.recommendations_factory(request)
        raw_result = await batch_scraper.run()
        response = InstagramBatchScrapeResponse.model_validate(raw_result)

        return build_batch_recommendations_summary(
            request,
            response,
            prevalidated_usernames=prevalidated_usernames,
        )


def create_default_batch_scraper(request: InstagramBatchScrapeRequest) -> Any:
    from .types import InstagramBatchScraper

    return InstagramBatchScraper.create_snapshot(
        usernames=request.usernames,
        max_posts=request.max_posts,
        headless=request.headless,
        user_agent=request.user_agent,
        locale=request.locale,
        proxy=request.proxy,
        timeout_ms=request.timeout_ms,
        max_concurrent=request.max_concurrent,
        measure_network_bytes=request.measure_network_bytes,
    )


def create_recommendations_batch_scraper(
    request: InstagramBatchRecommendationsRequest,
) -> Any:
    from .types import InstagramBatchScraper

    return InstagramBatchScraper.create_recommendations(
        usernames=request.usernames,
        max_posts=request.max_posts,
        headless=request.headless,
        user_agent=request.user_agent,
        locale=request.locale,
        proxy=request.proxy,
        timeout_ms=request.timeout_ms,
        max_concurrent=request.max_concurrent,
        recommended_limit=request.recommended_limit,
        measure_network_bytes=request.measure_network_bytes,
    )


# Default service instance for backward compatibility
_default_service = InstagramScraperService(
    batch_scraper_factory=create_default_batch_scraper,
    recommendations_factory=create_recommendations_batch_scraper,
)


async def persist_scrape_results_to_db(
    response: InstagramBatchScrapeResponse,
    *,
    persistence: InstagramScrapePersistence,
) -> InstagramBatchScrapeResponse:
    return await persistence.persist_scrape_results(response)


async def scrape_profiles_batch(
    payload: InstagramBatchScrapeRequest | dict[str, Any],
) -> InstagramBatchScrapeResponse:
    """Scrape multiple Instagram profiles using the batch workflow."""
    return await _default_service.scrape_profiles_batch(payload)


async def scrape_recommendations_batch(
    payload: InstagramBatchRecommendationsRequest | dict[str, Any],
) -> InstagramBatchRecommendationsResponse:
    """Scrape multiple profiles returning only recommended accounts."""
    return await _default_service.scrape_recommendations_batch(payload)


async def enrich_with_ai_analysis(
    response: InstagramBatchScrapeResponse,
    *,
    analysis_service: InstagramProfileAnalysisService,
) -> InstagramBatchScrapeResponse:
    """Enrich scrape results with the configured profile analysis service."""
    return await analysis_service.enrich_scrape_response(response)


__all__ = [
    "InstagramScraperService",
    "scrape_profiles_batch",
    "scrape_recommendations_batch",
    "persist_scrape_results_to_db",
    "enrich_with_ai_analysis",
    "prepare_scrape_batch_payload",
    "build_batch_scrape_summary",
    "prepare_recommendations_batch_payload",
    "build_batch_recommendations_summary",
    "create_default_batch_scraper",
    "create_recommendations_batch_scraper",
]
