from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import AnyUrl, BaseModel, TypeAdapter, ValidationError

from app.crud.metrics import create_metrics, replace_metrics
from app.crud.posts import create_post, replace_post
from app.crud.profile import (
    create_profile,
    get_profile_by_username,
    get_profiles_by_usernames,
    update_profile,
)
from app.crud.profile_snapshots import (
    create_profile_snapshot,
    get_profile_snapshot_by_profile_id,
    replace_profile_snapshot,
)
from app.crud.reels import create_reel, replace_reel
from app.features.openai.classes import (
    IG_OPENAI_REQUEST,
    InstagramProfileAnalysisInput,
    deserialize_profile_analysis_response,
    serialize_profile_analysis_payload,
)
from app.features.openai.classes.openai_system_prompts import (
    SYSTEM_PROMPT_IG_OPENAI_REQUEST,
)
from app.features.openai.service import OpenAIService
from app.schemas import (
    Metrics,
    Post,
    Profile,
    ProfileSnapshot,
    Reel,
    UpdateProfile,
)

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
_URL_ADAPTER = TypeAdapter(AnyUrl)


def _get_field_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump()
    return {}


def _coerce_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


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


def _sanitize_optional_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = _URL_ADAPTER.validate_python(candidate)
    except ValidationError:
        return None
    return str(parsed)


def _sanitize_bio_links(value: Any) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for item in _coerce_list(value):
        if not isinstance(item, dict):
            continue
        url = _sanitize_optional_url(item.get("url"))
        if not url:
            continue
        title_raw = item.get("title")
        title = title_raw.strip() if isinstance(title_raw, str) else ""
        sanitized.append({"title": title, "url": url})
    return sanitized


async def prepare_scrape_batch_payload(
    payload: InstagramBatchScrapeRequest,
    profiles_collection: Any,
) -> tuple[InstagramBatchScrapeRequest, InstagramBatchScrapeResponse | None]:
    requested_usernames = _normalize_usernames(payload.usernames)
    if not requested_usernames:
        return payload, InstagramBatchScrapeResponse(
            counters=InstagramBatchCountersSchema(requested=0)
        )

    existing_profiles = await get_profiles_by_usernames(
        profiles_collection,
        requested_usernames,
    )
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
            status = "failed"
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
        status = "failed"
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
        openai_service_factory: Callable[[], OpenAIService] | None = None,
    ):
        self.batch_scraper_factory = batch_scraper_factory
        self.recommendations_factory = recommendations_factory
        self._openai_service_factory = openai_service_factory
        self._openai_service: OpenAIService | None = None
        self._logger = logging.getLogger(__name__)

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

    def _get_openai_service(self) -> OpenAIService:
        if self._openai_service is None:
            factory = self._openai_service_factory or OpenAIService
            self._openai_service = factory()
        return self._openai_service

    async def scrape_profiles_batch(
        self, payload: InstagramBatchScrapeRequest | dict[str, Any]
    ) -> InstagramBatchScrapeResponse:
        """Scrape multiple Instagram profiles concurrently with controlled parallelism."""
        request = self._ensure_batch_request(payload)
        batch_scraper = self.batch_scraper_factory(request)
        result = await batch_scraper.run()
        return InstagramBatchScrapeResponse.model_validate(result)

    async def enrich_with_ai_analysis(
        self, response: InstagramBatchScrapeResponse
    ) -> InstagramBatchScrapeResponse:
        """
        Run OpenAI categorization for all profiles (single batch call) and attach categories/roles.
        """

        if response.error:
            self._logger.info(
                "Skipping AI analysis because batch response has error: %s",
                response.error,
            )
            return response

        if not response.results:
            return response

        openai_service = self._get_openai_service()

        usernames: list[str] = []
        inputs: list[InstagramProfileAnalysisInput] = []

        for username, profile_result in response.results.items():
            if not profile_result.success:
                self._logger.debug(
                    "Skipping AI analysis for %s because scrape failed", username
                )
                continue
            ai_input = InstagramProfileAnalysisInput(
                username=profile_result.user.username or username,
                biography=profile_result.user.biography,
                follower_count=profile_result.user.follower_count,
                posts=profile_result.posts,
            )
            usernames.append(username)
            inputs.append(ai_input)

        if not inputs:
            return response

        try:
            serialized = serialize_profile_analysis_payload(inputs)
            req_kwargs = IG_OPENAI_REQUEST.to_function_kwargs()
            req_kwargs["prompt"] = json.dumps(serialized, ensure_ascii=False)
            req_kwargs["system_prompt"] = SYSTEM_PROMPT_IG_OPENAI_REQUEST

            text = await asyncio.to_thread(
                openai_service.execute,
                "create_response",
                function_kwargs=req_kwargs,
            )

            raw = json.loads(text)
            parsed = deserialize_profile_analysis_response(raw)
            ai_results = parsed.results

            if len(ai_results) != len(inputs):
                self._logger.warning(
                    "AI results count mismatch: expected %s got %s",
                    len(inputs),
                    len(ai_results),
                )

            for idx, username in enumerate(usernames):
                profile_result = response.results[username]
                if idx < len(ai_results):
                    profile_result.ai_categories = ai_results[idx].categories
                    profile_result.ai_roles = ai_results[idx].roles
                else:
                    profile_result.ai_error = "AI response missing for this profile"

        except Exception as exc:  # pragma: no cover - resilience for AI call
            self._logger.warning("AI analysis failed for batch: %s", exc)
            for username in usernames:
                response.results[username].ai_error = str(exc)

        return response

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


def create_default_batch_scraper(request: InstagramBatchScrapeRequest):
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
):
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
    profiles_collection: Any,
    posts_collection: Any,
    reels_collection: Any,
    metrics_collection: Any,
    snapshots_collection: Any,
) -> InstagramBatchScrapeResponse:
    if response.error or not response.results:
        return response

    errors: list[str] = []
    now = datetime.now(timezone.utc)

    for username, profile_result in response.results.items():
        if not profile_result.success:
            continue

        try:
            user = profile_result.user
            ig_id = _get_field_value(user, "id")
            if not ig_id:
                raise ValueError("Missing ig_id")

            profile_pic_url = _get_field_value(user, "profile_pic_url")
            if not profile_pic_url:
                raise ValueError("Missing profile_pic_url")

            username_value = _get_field_value(user, "username") or username
            external_url = _sanitize_optional_url(
                _get_field_value(user, "external_url")
            )
            bio_links = _sanitize_bio_links(
                _get_field_value(user, "bio_links", []) or []
            )
            profile_payload = {
                "ig_id": ig_id,
                "username": username_value,
                "full_name": _get_field_value(user, "full_name") or "",
                "biography": _get_field_value(user, "biography") or "",
                "is_private": bool(_get_field_value(user, "is_private", False)),
                "is_verified": bool(_get_field_value(user, "is_verified", False)),
                "profile_pic_url": profile_pic_url,
                "external_url": external_url,
                "updated_date": now,
                "follower_count": int(_get_field_value(user, "follower_count", 0) or 0),
                "following_count": int(
                    _get_field_value(user, "following_count", 0) or 0
                ),
                "media_count": int(_get_field_value(user, "media_count", 0) or 0),
                "bio_links": bio_links,
                "ai_categories": profile_result.ai_categories or [],
                "ai_roles": profile_result.ai_roles or [],
            }

            existing_profile = await get_profile_by_username(
                profiles_collection, username_value
            )
            if not existing_profile:
                existing_profile = await profiles_collection.find_one({"ig_id": ig_id})

            if existing_profile:
                profile_doc = await update_profile(
                    profiles_collection,
                    str(existing_profile["_id"]),
                    UpdateProfile(**profile_payload),
                )
            else:
                profile_doc = await create_profile(
                    profiles_collection,
                    Profile(**profile_payload),
                )

            profile_id = str(profile_doc["_id"])

            posts_payload = []
            for post in _coerce_list(profile_result.posts):
                code = _get_field_value(post, "code")
                if not code:
                    continue
                posts_payload.append(
                    {
                        "code": code,
                        "caption_text": _get_field_value(post, "caption_text"),
                        "is_paid_partnership": _get_field_value(
                            post, "is_paid_partnership"
                        ),
                        "coauthor_producers": _get_field_value(
                            post, "coauthor_producers", []
                        )
                        or [],
                        "comment_count": _get_field_value(post, "comment_count"),
                        "like_count": _get_field_value(post, "like_count"),
                        "usertags": _get_field_value(post, "usertags", []) or [],
                        "media_type": _get_field_value(post, "media_type"),
                        "product_type": _get_field_value(post, "product_type"),
                    }
                )

            reels_payload = []
            for reel in _coerce_list(profile_result.reels):
                code = _get_field_value(reel, "code")
                if not code:
                    continue
                reels_payload.append(
                    {
                        "code": code,
                        "play_count": _get_field_value(reel, "play_count"),
                        "comment_count": _get_field_value(reel, "comment_count"),
                        "like_count": _get_field_value(reel, "like_count"),
                        "media_type": _get_field_value(reel, "media_type"),
                        "product_type": _get_field_value(reel, "product_type"),
                    }
                )

            snapshot_doc = await get_profile_snapshot_by_profile_id(
                snapshots_collection, profile_id
            )

            post_id = None
            if snapshot_doc:
                post_ids = snapshot_doc.get("post_ids") or []
                if post_ids:
                    post_id = str(post_ids[0])

            if post_id:
                post_doc = await replace_post(
                    posts_collection,
                    post_id,
                    Post(
                        profile_id=profile_id,
                        posts=posts_payload,
                        updated_at=now,
                    ),
                )
            else:
                post_doc = await create_post(
                    posts_collection,
                    Post(
                        profile_id=profile_id,
                        posts=posts_payload,
                        updated_at=now,
                    ),
                )

            reel_id = None
            if snapshot_doc:
                reel_ids = snapshot_doc.get("reel_ids") or []
                if reel_ids:
                    reel_id = str(reel_ids[0])

            if reel_id:
                reel_doc = await replace_reel(
                    reels_collection,
                    reel_id,
                    Reel(
                        profile_id=profile_id,
                        reels=reels_payload,
                        updated_at=now,
                    ),
                )
            else:
                reel_doc = await create_reel(
                    reels_collection,
                    Reel(
                        profile_id=profile_id,
                        reels=reels_payload,
                        updated_at=now,
                    ),
                )

            metrics_source = profile_result.metrics
            metrics_payload = {
                "post_metrics": _coerce_dict(
                    _get_field_value(metrics_source, "post_metrics")
                ),
                "reel_metrics": _coerce_dict(
                    _get_field_value(metrics_source, "reel_metrics")
                ),
                "overall_engagement_rate": float(
                    _get_field_value(metrics_source, "overall_engagement_rate", 0.0)
                    or 0.0
                ),
            }

            metrics_id = None
            if snapshot_doc and snapshot_doc.get("metrics_id"):
                metrics_id = str(snapshot_doc["metrics_id"])

            if metrics_id:
                metrics_doc = await replace_metrics(
                    metrics_collection,
                    metrics_id,
                    Metrics(**metrics_payload),
                )
            else:
                metrics_doc = await create_metrics(
                    metrics_collection, Metrics(**metrics_payload)
                )

            snapshot_payload = ProfileSnapshot(
                profile_id=profile_id,
                post_ids=[str(post_doc["_id"])],
                reel_ids=[str(reel_doc["_id"])],
                metrics_id=str(metrics_doc["_id"]),
                scraped_at=now,
            )

            if snapshot_doc:
                await replace_profile_snapshot(
                    snapshots_collection,
                    str(snapshot_doc["_id"]),
                    snapshot_payload,
                )
            else:
                await create_profile_snapshot(snapshots_collection, snapshot_payload)

        except Exception as exc:
            errors.append(f"{username}: {exc}")

    if errors:
        response.error = "Persistence errors: " + "; ".join(errors)

    return response


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
) -> InstagramBatchScrapeResponse:
    """Enrich scrape results with OpenAI categories/roles using the default service."""

    return await _default_service.enrich_with_ai_analysis(response)


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
