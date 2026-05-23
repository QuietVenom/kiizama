from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchScrapeSummaryResponse,
    InstagramBatchUsernameStatus,
    InstagramScrapeJobCreateRequest,
)
from sqlmodel import Session

from app.features.ig_scraper_jobs import billing

pytestmark = pytest.mark.anyio


class FakeJobService:
    def __init__(self) -> None:
        self.create_calls: list[dict[str, Any]] = []
        self.exception: Exception | None = None

    async def create_job(self, **kwargs: Any) -> str:
        self.create_calls.append(kwargs)
        if self.exception is not None:
            raise self.exception
        return "job-1"


def _payload() -> InstagramScrapeJobCreateRequest:
    return InstagramScrapeJobCreateRequest(usernames=["alpha", "beta"])


def _summary(*, successful: int) -> InstagramBatchScrapeSummaryResponse:
    return InstagramBatchScrapeSummaryResponse(
        usernames=[
            InstagramBatchUsernameStatus(username="alpha", status="success"),
            InstagramBatchUsernameStatus(username="beta", status="skipped"),
        ],
        counters=InstagramBatchCountersSchema(requested=2, successful=successful),
    )


def _fake_session() -> Session:
    return cast(Session, object())


async def test_create_billable_worker_job_reserves_attaches_and_publishes(
    monkeypatch,
) -> None:
    calls: dict[str, Any] = {"events": []}
    owner_user_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    job_service = FakeJobService()

    monkeypatch.setattr(
        billing,
        "build_usage_request_key",
        lambda **kwargs: calls.setdefault("request_key_kwargs", kwargs) or "usage-key",
    )

    def reserve_feature_usage(**kwargs: Any) -> SimpleNamespace:
        calls["reserve"] = kwargs
        return SimpleNamespace(job_id=None)

    monkeypatch.setattr(billing, "reserve_feature_usage", reserve_feature_usage)
    monkeypatch.setattr(
        billing,
        "attach_job_id_to_reservation",
        lambda **kwargs: calls.setdefault("attach", kwargs),
    )

    async def publish_billing_event(**kwargs: Any) -> None:
        calls["events"].append(kwargs)

    monkeypatch.setattr(billing, "publish_billing_event", publish_billing_event)

    response = await billing.create_billable_instagram_job(
        session=_fake_session(),
        job_service=job_service,
        payload=_payload(),
        owner_user_id=owner_user_id,
        execution_mode="worker",
        idempotency_key="same-request",
    )

    assert response.job_id == "job-1"
    assert calls["request_key_kwargs"]["request_scope"] == "ig-scraper-worker"
    assert calls["request_key_kwargs"]["idempotency_key"] == "same-request"
    assert calls["reserve"]["feature_code"] == "ig_scraper_apify"
    assert calls["reserve"]["endpoint_key"] == "ig-scraper.jobs.worker"
    assert calls["reserve"]["max_units_requested"] == 2
    assert calls["reserve"]["metadata"]["execution_mode"] == "worker"
    assert job_service.create_calls[0]["execution_mode"] == "worker"
    assert calls["attach"]["job_id"] == "job-1"
    assert [event["event_name"] for event in calls["events"]] == [
        "account.usage.updated"
    ]


async def test_create_billable_job_returns_existing_reserved_job_without_enqueue(
    monkeypatch,
) -> None:
    calls: dict[str, Any] = {}
    job_service = FakeJobService()

    monkeypatch.setattr(billing, "build_usage_request_key", lambda **_: "usage-key")

    def reserve_feature_usage(**kwargs: Any) -> SimpleNamespace:
        calls["reserve"] = kwargs
        return SimpleNamespace(job_id="existing-job")

    monkeypatch.setattr(billing, "reserve_feature_usage", reserve_feature_usage)

    response = await billing.create_billable_instagram_job(
        session=_fake_session(),
        job_service=job_service,
        payload=_payload(),
        owner_user_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        execution_mode="apify",
        idempotency_key="same-request",
    )

    assert response.job_id == "existing-job"
    assert calls["reserve"]["endpoint_key"] == "ig-scraper.jobs.apify"
    assert job_service.create_calls == []


async def test_create_billable_job_releases_reservation_when_enqueue_fails(
    monkeypatch,
) -> None:
    calls: dict[str, Any] = {"events": []}
    job_service = FakeJobService()
    job_service.exception = RuntimeError("redis down")

    monkeypatch.setattr(billing, "build_usage_request_key", lambda **_: "usage-key")
    monkeypatch.setattr(
        billing,
        "reserve_feature_usage",
        lambda **_: SimpleNamespace(job_id=None),
    )
    monkeypatch.setattr(
        billing,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("release", kwargs),
    )

    async def publish_billing_event(**kwargs: Any) -> None:
        calls["events"].append(kwargs)

    monkeypatch.setattr(billing, "publish_billing_event", publish_billing_event)

    try:
        await billing.create_billable_instagram_job(
            session=_fake_session(),
            job_service=job_service,
            payload=_payload(),
            owner_user_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
            execution_mode="worker",
            idempotency_key="same-request",
        )
    except RuntimeError as exc:
        assert str(exc) == "redis down"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected RuntimeError")

    assert calls["release"]["request_key"] == "usage-key"
    assert [event["event_name"] for event in calls["events"]] == [
        "account.usage.updated"
    ]


async def test_finalize_instagram_job_billing_consumes_successful_count_only(
    monkeypatch,
) -> None:
    calls: dict[str, Any] = {"events": []}

    monkeypatch.setattr(
        billing,
        "finalize_usage_reservation",
        lambda **kwargs: calls.setdefault("finalize", kwargs),
    )

    async def publish_billing_event(**kwargs: Any) -> None:
        calls["events"].append(kwargs)

    monkeypatch.setattr(billing, "publish_billing_event", publish_billing_event)

    await billing.finalize_instagram_job_billing(
        session=_fake_session(),
        owner_user_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        job_id="job-1",
        execution_mode="worker",
        job_status="done",
        summary=_summary(successful=1),
    )

    assert calls["finalize"]["job_id"] == "job-1"
    assert calls["finalize"]["quantity_consumed"] == 1
    assert calls["finalize"]["metadata"]["execution_mode"] == "worker"
    assert calls["events"][0]["event_name"] == "account.usage.updated"


async def test_finalize_instagram_job_billing_releases_when_no_successes(
    monkeypatch,
) -> None:
    calls: dict[str, Any] = {"events": []}

    monkeypatch.setattr(
        billing,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("release", kwargs),
    )

    async def publish_billing_event(**kwargs: Any) -> None:
        calls["events"].append(kwargs)

    monkeypatch.setattr(billing, "publish_billing_event", publish_billing_event)

    await billing.finalize_instagram_job_billing(
        session=_fake_session(),
        owner_user_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        job_id="job-1",
        execution_mode="worker",
        job_status="failed",
        summary=_summary(successful=0),
    )

    assert calls["release"]["job_id"] == "job-1"
    assert calls["release"]["metadata"]["job_status"] == "failed"
    assert calls["events"][0]["event_name"] == "account.usage.updated"
