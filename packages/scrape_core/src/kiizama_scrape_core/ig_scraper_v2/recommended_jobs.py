from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from kiizama_core.job_control.schemas import (
    JobExecutionMode,
    QueuedJobMessage,
)
from redis.exceptions import RedisError

from .ports import InstagramScrapePersistence
from .profile_navigation import normalize_username
from .schemas import (
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
)
from .service import is_valid_instagram_username, prepare_scrape_batch_payload

INTERNAL_RECOMMENDED_SOURCE = "ig-recommended-background"
INTERNAL_RECOMMENDED_OWNER_USER_ID = "internal:ig-recommended-background"
RECOMMENDED_INTERNAL_BATCH_SIZE = 10
RECOMMENDED_USERNAME_DEDUPE_TTL_SECONDS = 60 * 60 * 24
RECOMMENDED_USERNAME_DEDUPE_PREFIX = "jobs:dedupe:ig-recommended-background"


class RecommendedJobControlRepository(Protocol):
    async def enqueue_job(self, message: QueuedJobMessage) -> None: ...

    def require_redis_client(self) -> Any: ...


def is_internal_recommended_job_payload(payload: dict[str, Any]) -> bool:
    return payload.get("internal_source") == INTERNAL_RECOMMENDED_SOURCE


def should_collect_recommended_usernames(
    payload: dict[str, Any],
    *,
    feature_enabled: bool,
) -> bool:
    if not feature_enabled:
        return False
    if is_internal_recommended_job_payload(payload):
        return False
    return payload.get("enqueue_recommended", True) is not False


def build_internal_recommended_payload(
    *,
    usernames: Sequence[str],
    origin_job_id: str,
    origin_execution_mode: JobExecutionMode,
) -> dict[str, Any]:
    return {
        "usernames": list(usernames),
        "internal_source": INTERNAL_RECOMMENDED_SOURCE,
        "enqueue_recommended": False,
        "origin_job_id": origin_job_id,
        "origin_execution_mode": origin_execution_mode,
    }


def extract_recommended_usernames(
    response: InstagramBatchScrapeResponse,
) -> list[str]:
    usernames: list[str] = []
    seen: set[str] = set()

    for result in response.results.values():
        if not result.success:
            continue
        for user in result.recommended_users:
            if not user.username:
                continue
            username = normalize_username(user.username)
            if (
                not username
                or username in seen
                or not is_valid_instagram_username(username)
            ):
                continue
            usernames.append(username)
            seen.add(username)

    return usernames


def chunk_recommended_usernames(
    usernames: Sequence[str],
    *,
    batch_size: int = RECOMMENDED_INTERNAL_BATCH_SIZE,
) -> list[list[str]]:
    return [
        list(usernames[index : index + batch_size])
        for index in range(0, len(usernames), batch_size)
    ]


async def resolve_recommended_usernames_to_enqueue(
    response: InstagramBatchScrapeResponse,
    *,
    persistence: InstagramScrapePersistence,
) -> list[str]:
    candidates = extract_recommended_usernames(response)
    if not candidates:
        return []

    usernames_to_enqueue: list[str] = []
    for batch in chunk_recommended_usernames(candidates):
        request = InstagramBatchScrapeRequest(usernames=batch)
        scrape_request, early_response = await prepare_scrape_batch_payload(
            request,
            persistence,
        )
        if early_response is not None:
            continue
        usernames_to_enqueue.extend(scrape_request.usernames)

    return usernames_to_enqueue


async def enqueue_internal_recommended_jobs(
    *,
    repository: RecommendedJobControlRepository,
    usernames: Sequence[str],
    origin_job_id: str,
    origin_execution_mode: JobExecutionMode,
    logger: logging.Logger,
    now: datetime | None = None,
) -> int:
    claimed_usernames = await _claim_recommended_usernames(
        repository=repository,
        usernames=usernames,
    )
    if not claimed_usernames:
        return 0

    enqueued_count = 0
    created_at = now or datetime.now(UTC)
    for batch in chunk_recommended_usernames(claimed_usernames):
        job_id = f"internal-recommended-{uuid.uuid4()}"
        try:
            await repository.enqueue_job(
                QueuedJobMessage(
                    job_id=job_id,
                    owner_user_id=INTERNAL_RECOMMENDED_OWNER_USER_ID,
                    execution_mode=origin_execution_mode,
                    created_at=created_at,
                    expires_at=None,
                    payload=build_internal_recommended_payload(
                        usernames=batch,
                        origin_job_id=origin_job_id,
                        origin_execution_mode=origin_execution_mode,
                    ),
                )
            )
        except Exception:
            await _release_recommended_usernames(repository=repository, usernames=batch)
            logger.exception(
                "Failed to enqueue internal recommended scrape job "
                "(origin_job_id=%s, execution_mode=%s, usernames=%s).",
                origin_job_id,
                origin_execution_mode,
                len(batch),
            )
            continue
        enqueued_count += 1

    return enqueued_count


def _dedupe_key(username: str) -> str:
    return f"{RECOMMENDED_USERNAME_DEDUPE_PREFIX}:{username}"


async def _claim_recommended_usernames(
    *,
    repository: RecommendedJobControlRepository,
    usernames: Sequence[str],
) -> list[str]:
    redis = repository.require_redis_client()
    claimed: list[str] = []
    for username in usernames:
        try:
            acquired = await redis.set(
                _dedupe_key(username),
                "1",
                nx=True,
                ex=RECOMMENDED_USERNAME_DEDUPE_TTL_SECONDS,
            )
        except RedisError:
            await _release_recommended_usernames(
                repository=repository,
                usernames=claimed,
            )
            raise
        if acquired:
            claimed.append(username)
    return claimed


async def _release_recommended_usernames(
    *,
    repository: RecommendedJobControlRepository,
    usernames: Sequence[str],
) -> None:
    if not usernames:
        return
    try:
        redis = repository.require_redis_client()
        await redis.delete(*[_dedupe_key(username) for username in usernames])
    except Exception:
        return


__all__ = [
    "INTERNAL_RECOMMENDED_SOURCE",
    "RECOMMENDED_INTERNAL_BATCH_SIZE",
    "RECOMMENDED_USERNAME_DEDUPE_TTL_SECONDS",
    "build_internal_recommended_payload",
    "chunk_recommended_usernames",
    "enqueue_internal_recommended_jobs",
    "extract_recommended_usernames",
    "is_internal_recommended_job_payload",
    "resolve_recommended_usernames_to_enqueue",
    "should_collect_recommended_usernames",
]
