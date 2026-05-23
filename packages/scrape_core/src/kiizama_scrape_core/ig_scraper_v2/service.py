from __future__ import annotations

import re
from typing import Literal

from .ports import InstagramProfileAnalysisService, InstagramScrapePersistence
from .schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
)
from .utils import should_refresh_profile

NOT_FOUND_ERROR = "Instagram username does not exist"
INSTAGRAM_USERNAME_RE = re.compile(r"^(?!.*\.\.)(?!\.)(?!.*\.$)[a-z0-9._]{1,30}$")
BatchUsernameStatus = Literal["success", "failed", "skipped", "not_found"]


def is_valid_instagram_username(username: str) -> bool:
    return bool(INSTAGRAM_USERNAME_RE.fullmatch(username))


async def prepare_scrape_batch_payload(
    payload: InstagramBatchScrapeRequest,
    persistence: InstagramScrapePersistence,
) -> tuple[InstagramBatchScrapeRequest, InstagramBatchScrapeResponse | None]:
    requested_usernames = payload.usernames
    if not requested_usernames:
        return payload, InstagramBatchScrapeResponse(
            counters=InstagramBatchCountersSchema(requested=0)
        )

    existing_profiles = await persistence.get_profiles_by_usernames(requested_usernames)
    existing_profiles_by_username = {
        str(profile.get("username", "")).lower(): profile
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


def build_batch_scrape_summary(
    payload: InstagramBatchScrapeRequest,
    scrape_payload: InstagramBatchScrapeRequest,
    response: InstagramBatchScrapeResponse | None,
    *,
    early_response: InstagramBatchScrapeResponse | None = None,
) -> InstagramBatchScrapeSummaryResponse:
    original_usernames = payload.usernames
    scraped_usernames = scrape_payload.usernames
    scraped_set = set(scraped_usernames)
    if response is None and early_response is not None:
        scraped_set = set()

    usernames: list[InstagramBatchUsernameStatus] = []
    for username in original_usernames:
        if username in scraped_set:
            status: BatchUsernameStatus = "failed"
            error: str | None = None
            if response and username in response.results:
                result = response.results[username]
                error = result.error
                if result.success:
                    status = "success"
                    error = None
                elif result.error == NOT_FOUND_ERROR:
                    status = "not_found"
                else:
                    status = "failed"
            usernames.append(
                InstagramBatchUsernameStatus(
                    username=username,
                    status=status,
                    error=error,
                )
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


async def enrich_with_ai_analysis(
    response: InstagramBatchScrapeResponse,
    *,
    analysis_service: InstagramProfileAnalysisService,
) -> InstagramBatchScrapeResponse:
    return await analysis_service.enrich_scrape_response(response)


async def persist_scrape_results_to_db(
    response: InstagramBatchScrapeResponse,
    *,
    persistence: InstagramScrapePersistence,
) -> InstagramBatchScrapeResponse:
    return await persistence.persist_scrape_results(response)


__all__ = [
    "INSTAGRAM_USERNAME_RE",
    "NOT_FOUND_ERROR",
    "build_batch_scrape_summary",
    "enrich_with_ai_analysis",
    "is_valid_instagram_username",
    "persist_scrape_results_to_db",
    "prepare_scrape_batch_payload",
]
