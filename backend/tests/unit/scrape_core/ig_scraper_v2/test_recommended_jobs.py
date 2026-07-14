from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2.feature_flags import is_feature_flag_enabled
from kiizama_scrape_core.ig_scraper_v2.recommended_jobs import (
    INTERNAL_RECOMMENDED_SOURCE,
    build_internal_recommended_payload,
    chunk_recommended_usernames,
    enqueue_internal_recommended_jobs,
    extract_recommended_usernames,
    is_internal_recommended_job_payload,
    resolve_recommended_usernames_to_enqueue,
    should_collect_recommended_usernames,
)
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeResponse,
    InstagramProfileSchema,
    InstagramSuggestedUserSchema,
)


class FakePersistence:
    def __init__(self, profiles: list[dict[str, Any]] | None = None) -> None:
        self.profiles = profiles or []

    async def get_profiles_by_usernames(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        username_set = set(usernames)
        return [
            profile
            for profile in self.profiles
            if str(profile.get("username", "")).lower() in username_set
        ]

    async def persist_scrape_results(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        return response


class FakeRedis:
    def __init__(self, existing_keys: set[str] | None = None) -> None:
        self.keys = existing_keys or set()
        self.deleted: list[str] = []

    async def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool,
        ex: int,
    ) -> bool:
        del value, ex
        if nx and key in self.keys:
            return False
        self.keys.add(key)
        return True

    async def delete(self, *keys: str) -> None:
        self.deleted.extend(keys)
        for key in keys:
            self.keys.discard(key)


class FakeRepository:
    def __init__(self, redis: FakeRedis | None = None) -> None:
        self.redis = redis or FakeRedis()
        self.messages: list[Any] = []

    def require_redis_client(self) -> FakeRedis:
        return self.redis

    async def enqueue_job(self, message: Any) -> None:
        self.messages.append(message)


class FakeFeatureFlagSession:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    def __enter__(self) -> FakeFeatureFlagSession:
        return self

    def __exit__(self, *args: Any) -> None:
        del args

    def execute(self, statement: Any, params: dict[str, Any]) -> Any:
        del statement, params
        if self.error:
            raise self.error
        return self

    def first(self) -> Any:
        return self.result


def expiring_cdn_url(*, seconds_from_now: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(seconds=seconds_from_now)
    return f"https://cdn.example.test/profile.jpg?oe={int(expires_at.timestamp()):X}"


def response_with_recommended(usernames: list[str]) -> InstagramBatchScrapeResponse:
    return InstagramBatchScrapeResponse(
        results={
            "source": InstagramBatchProfileResult(
                success=True,
                user=InstagramProfileSchema(username="source"),
                recommended_users=[
                    InstagramSuggestedUserSchema(username=username)
                    for username in usernames
                ],
            ),
            "failed_source": InstagramBatchProfileResult(
                success=False,
                recommended_users=[InstagramSuggestedUserSchema(username="ignored")],
            ),
        },
        counters=InstagramBatchCountersSchema(requested=2, successful=1, failed=1),
    )


def test_recommended_payload_helpers_identify_internal_jobs() -> None:
    payload = build_internal_recommended_payload(
        usernames=["alpha"],
        origin_job_id="job-1",
        origin_execution_mode="apify",
    )

    assert payload["internal_source"] == INTERNAL_RECOMMENDED_SOURCE
    assert payload["enqueue_recommended"] is False
    assert is_internal_recommended_job_payload(payload) is True
    assert should_collect_recommended_usernames(payload, feature_enabled=True) is False
    assert (
        should_collect_recommended_usernames(
            {"usernames": ["alpha"]},
            feature_enabled=True,
        )
        is True
    )
    assert (
        should_collect_recommended_usernames(
            {"usernames": ["alpha"]},
            feature_enabled=False,
        )
        is False
    )


def test_is_feature_flag_enabled_reads_database_value() -> None:
    assert (
        is_feature_flag_enabled(
            session_factory=lambda: FakeFeatureFlagSession(result=(True,)),
            key="IG_SCRAPER_RECOMMENDED_BACKGROUND_JOBS_ENABLED",
        )
        is True
    )


def test_is_feature_flag_enabled_defaults_when_missing_or_read_fails() -> None:
    assert (
        is_feature_flag_enabled(
            session_factory=lambda: FakeFeatureFlagSession(result=None),
            key="missing",
        )
        is False
    )
    assert (
        is_feature_flag_enabled(
            session_factory=lambda: FakeFeatureFlagSession(
                error=RuntimeError("database unavailable")
            ),
            key="broken",
        )
        is False
    )


def test_extract_recommended_usernames_normalizes_valid_and_unique_successes() -> None:
    response = response_with_recommended(
        ["@Alpha", "alpha", "bad username", "", "beta"],
    )

    assert extract_recommended_usernames(response) == ["alpha", "beta"]


@pytest.mark.anyio
async def test_resolve_recommended_usernames_filters_fresh_existing_profiles() -> None:
    response = response_with_recommended(["alpha", "fresh", "stale"])
    persistence = FakePersistence(
        [
            {
                "username": "fresh",
                "profile_pic_url": expiring_cdn_url(seconds_from_now=3600),
            },
            {
                "username": "stale",
                "profile_pic_url": expiring_cdn_url(seconds_from_now=-3600),
            },
        ]
    )

    usernames = await resolve_recommended_usernames_to_enqueue(
        response,
        persistence=persistence,
    )

    assert usernames == ["alpha", "stale"]


@pytest.mark.anyio
async def test_enqueue_internal_recommended_jobs_batches_and_dedupes_usernames() -> (
    None
):
    usernames = [f"user_{index}" for index in range(21)]
    existing_key = "jobs:dedupe:ig-recommended-background:user_5"
    repository = FakeRepository(FakeRedis(existing_keys={existing_key}))

    count = await enqueue_internal_recommended_jobs(
        repository=repository,
        usernames=usernames,
        origin_job_id="source-job",
        origin_execution_mode="worker",
        logger=__import__("logging").getLogger(__name__),
        now=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
    )

    assert count == 2
    assert [message.payload["usernames"] for message in repository.messages] == [
        usernames[:5] + usernames[6:11],
        usernames[11:21],
    ]
    assert all(
        message.payload["internal_source"] == INTERNAL_RECOMMENDED_SOURCE
        for message in repository.messages
    )
    assert all(message.execution_mode == "worker" for message in repository.messages)


def test_chunk_recommended_usernames_uses_batch_size() -> None:
    assert chunk_recommended_usernames(["a", "b", "c"], batch_size=2) == [
        ["a", "b"],
        ["c"],
    ]
