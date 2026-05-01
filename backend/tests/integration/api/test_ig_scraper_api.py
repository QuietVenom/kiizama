from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import httpx
from fastapi.testclient import TestClient
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeRequest,
    InstagramBatchScrapeResponse,
    InstagramProfileSchema,
    InstagramScrapeJobTerminalizationResponse,
)
from sqlmodel import Session

from app import crud_admin
from app.api.routes import ig_scraper as ig_scraper_routes
from app.core.config import settings
from app.features.ig_scraper_jobs import get_instagram_job_service
from app.features.job_control.repository import JobControlUnavailableError
from app.main import app
from tests.utils.utils import random_email, random_lower_string


class StubInstagramJobService:
    def __init__(self) -> None:
        self.create_calls: list[tuple[dict[str, Any], str]] = []
        self.get_calls: list[tuple[str, str]] = []
        self.complete_calls: list[tuple[str, dict[str, Any]]] = []
        self.create_exception: Exception | None = None
        self.get_exception: Exception | None = None
        self.create_job_id = "job-1"
        self.get_result: Any = None
        self.complete_result: Any = None

    async def create_job(
        self,
        *,
        payload: Any,
        owner_user_id: str,
        execution_mode: str = "worker",
    ) -> str:
        self.create_calls.append(
            (
                payload.model_dump(mode="json") | {"execution_mode": execution_mode},
                owner_user_id,
            )
        )
        if self.create_exception is not None:
            raise self.create_exception
        return self.create_job_id

    async def get_job(self, *, job_id: str, owner_user_id: str) -> Any:
        if self.get_exception is not None:
            raise self.get_exception
        self.get_calls.append((job_id, owner_user_id))
        return self.get_result

    async def complete_job(self, *, job_id: str, payload: Any) -> Any:
        self.complete_calls.append((job_id, payload.model_dump(mode="json")))
        return self.complete_result


def _internal_headers(client: TestClient, db: Session) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    role = crud_admin.get_admin_role_by_code(session=db, code="system")
    assert role
    crud_admin.create_admin_user(session=db, email=email, password=password, role=role)

    response = client.post(
        f"{settings.API_V1_STR}/internal/login/access-token",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _successful_batch_response(username: str = "alpha") -> InstagramBatchScrapeResponse:
    return InstagramBatchScrapeResponse(
        results={
            username: InstagramBatchProfileResult(
                user=InstagramProfileSchema(username=username),
                success=True,
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, successful=1),
    )


def _early_batch_response(username: str = "alpha") -> InstagramBatchScrapeResponse:
    return InstagramBatchScrapeResponse(
        results={
            username: InstagramBatchProfileResult(
                user=InstagramProfileSchema(username=username),
                success=False,
                error="already processed",
            )
        },
        counters=InstagramBatchCountersSchema(requested=1, failed=1),
        error="already processed",
    )


def test_create_instagram_scrape_job_uses_service_and_current_user(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubInstagramJobService()
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs",
            headers=normal_user_token_headers,
            json={"usernames": ["Alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 202
    assert response.json() == {"job_id": "job-1", "status": "queued"}
    assert service.create_calls
    assert service.create_calls[0][0]["usernames"] == ["alpha"]


def test_create_worker_job_disabled_returns_503(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    service = StubInstagramJobService()
    monkeypatch.setattr(settings, "IG_SCRAPER_WORKER_JOBS_ENABLED", False)
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs",
            headers=normal_user_token_headers,
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "Legacy worker Instagram jobs are disabled."}
    assert service.create_calls == []


def test_create_instagram_scrape_job_returns_503_when_redis_is_unavailable(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubInstagramJobService()
    service.create_exception = JobControlUnavailableError("Redis is unavailable.")
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs",
            headers=normal_user_token_headers,
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Redis is unavailable.",
        "dependency": "redis",
        "retryable": True,
    }


def test_create_apify_job_disabled_returns_503(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    service = StubInstagramJobService()
    monkeypatch.setattr(settings, "IG_SCRAPER_APIFY_JOBS_ENABLED", False)
    monkeypatch.setattr(settings, "APIFY_API_TOKEN", "test-apify-token")
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs/apify",
            headers=normal_user_token_headers,
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "Instagram scraping jobs are disabled."}
    assert service.create_calls == []


def test_create_apify_job_without_token_returns_503(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    service = StubInstagramJobService()
    monkeypatch.setattr(settings, "IG_SCRAPER_APIFY_JOBS_ENABLED", True)
    monkeypatch.setattr(settings, "APIFY_API_TOKEN", None)
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs/apify",
            headers=normal_user_token_headers,
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "APIFY_API_TOKEN is not configured."}
    assert service.create_calls == []


def test_create_apify_job_existing_reservation_returns_existing_job_id(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    service = StubInstagramJobService()
    calls: dict[str, Any] = {}
    monkeypatch.setattr(settings, "IG_SCRAPER_APIFY_JOBS_ENABLED", True)
    monkeypatch.setattr(settings, "APIFY_API_TOKEN", "test-apify-token")
    monkeypatch.setattr(
        ig_scraper_routes,
        "build_usage_request_key",
        lambda **_kwargs: "usage-key",
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "reserve_feature_usage",
        lambda **_kwargs: calls.setdefault(
            "reservation",
            SimpleNamespace(job_id="existing-job"),
        ),
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "attach_job_id_to_reservation",
        lambda **kwargs: calls.setdefault("attached", kwargs),
    )
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs/apify",
            headers=normal_user_token_headers,
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 202
    assert response.json() == {"job_id": "existing-job", "status": "queued"}
    assert service.create_calls == []
    assert "attached" not in calls


def test_create_apify_job_failure_releases_usage_reservation(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    service = StubInstagramJobService()
    service.create_exception = JobControlUnavailableError("Redis is unavailable.")
    calls: dict[str, Any] = {}
    monkeypatch.setattr(settings, "IG_SCRAPER_APIFY_JOBS_ENABLED", True)
    monkeypatch.setattr(settings, "APIFY_API_TOKEN", "test-apify-token")
    monkeypatch.setattr(
        ig_scraper_routes,
        "build_usage_request_key",
        lambda **_kwargs: "usage-key",
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "reserve_feature_usage",
        lambda **_kwargs: SimpleNamespace(job_id=None),
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )

    async def publish_billing_event(**kwargs: Any) -> None:
        calls.setdefault("published_events", []).append(kwargs["event_name"])

    monkeypatch.setattr(
        ig_scraper_routes,
        "publish_billing_event",
        publish_billing_event,
    )
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/jobs/apify",
            headers=normal_user_token_headers,
            json={"usernames": ["alpha"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 503
    assert calls["released"]["request_key"] == "usage-key"
    assert calls["published_events"] == ["account.usage.updated"]
    assert service.create_calls[0][0]["execution_mode"] == "apify"


def test_get_instagram_scrape_job_uses_service(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubInstagramJobService()
    service.get_result = {
        "job_id": "job-1",
        "status": "running",
        "created_at": "2026-03-21T12:00:00Z",
        "updated_at": "2026-03-21T12:01:00Z",
        "expires_at": "2026-03-22T12:00:00Z",
        "attempts": 2,
        "lease_owner": "worker-1",
        "leased_until": "2026-03-21T12:10:00Z",
        "heartbeat_at": "2026-03-21T12:01:00Z",
        "summary": None,
        "references": None,
        "error": None,
    }
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.get(
            f"{settings.API_V1_STR}/ig-scraper/jobs/job-1",
            headers=normal_user_token_headers,
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert len(service.get_calls) == 1
    assert service.get_calls[0][0] == "job-1"
    assert service.get_calls[0][1]


def test_get_instagram_scrape_job_returns_404_for_missing_or_foreign_job(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubInstagramJobService()
    service.get_result = None
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.get(
            f"{settings.API_V1_STR}/ig-scraper/jobs/job-1",
            headers=normal_user_token_headers,
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Scrape job not found."}


def test_profiles_batch_early_response_returns_summary_without_scraping(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    calls: dict[str, Any] = {}
    early_response = _early_batch_response("alpha")

    async def fake_prepare_scrape_batch_payload(
        payload: InstagramBatchScrapeRequest,
        persistence: Any,
    ) -> tuple[InstagramBatchScrapeRequest, InstagramBatchScrapeResponse]:
        calls["prepared_usernames"] = payload.usernames
        calls["persistence"] = persistence
        return payload, early_response

    async def fail_scrape_profiles_batch(payload: InstagramBatchScrapeRequest) -> Any:
        del payload
        raise AssertionError("scrape_profiles_batch should not run")

    monkeypatch.setattr(
        ig_scraper_routes,
        "prepare_scrape_batch_payload",
        fake_prepare_scrape_batch_payload,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "scrape_profiles_batch",
        fail_scrape_profiles_batch,
    )

    response = client.post(
        f"{settings.API_V1_STR}/ig-scraper/profiles/batch",
        headers=superuser_token_headers,
        json={"usernames": ["alpha"]},
    )

    assert response.status_code == 200
    assert response.json()["error"] == "already processed"
    assert calls["prepared_usernames"] == ["alpha"]


def test_profiles_batch_upstream_error_marks_dependency_failure(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    failures: list[dict[str, Any]] = []

    async def fake_prepare_scrape_batch_payload(
        payload: InstagramBatchScrapeRequest,
        persistence: Any,
    ) -> tuple[InstagramBatchScrapeRequest, None]:
        del persistence
        return payload, None

    async def failing_scrape_profiles_batch(
        payload: InstagramBatchScrapeRequest,
    ) -> InstagramBatchScrapeResponse:
        del payload
        raise httpx.ConnectError("instagram down")

    monkeypatch.setattr(
        ig_scraper_routes,
        "prepare_scrape_batch_payload",
        fake_prepare_scrape_batch_payload,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "scrape_profiles_batch",
        failing_scrape_profiles_batch,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "mark_dependency_failure",
        lambda dependency, **kwargs: failures.append(
            {"dependency": dependency, **kwargs}
        ),
    )

    response = client.post(
        f"{settings.API_V1_STR}/ig-scraper/profiles/batch",
        headers=superuser_token_headers,
        json={"usernames": ["alpha"]},
    )

    assert response.status_code == 503
    assert response.json()["dependency"] == "instagram_upstream"
    assert failures[0]["dependency"] == "instagram_upstream"
    assert failures[0]["status"] == "degraded"


def test_profiles_batch_ai_error_marks_openai_degraded(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    failures: list[dict[str, Any]] = []

    async def fake_prepare_scrape_batch_payload(
        payload: InstagramBatchScrapeRequest,
        persistence: Any,
    ) -> tuple[InstagramBatchScrapeRequest, None]:
        del persistence
        return payload, None

    async def fake_scrape_profiles_batch(
        payload: InstagramBatchScrapeRequest,
    ) -> InstagramBatchScrapeResponse:
        del payload
        return _successful_batch_response("alpha")

    async def fake_enrich_with_ai_analysis(
        response: InstagramBatchScrapeResponse,
        *,
        analysis_service: Any,
    ) -> InstagramBatchScrapeResponse:
        del analysis_service
        response.results["alpha"].ai_error = "OpenAI timeout"
        return response

    async def fake_persist_scrape_results_to_db(
        response: InstagramBatchScrapeResponse,
        *,
        persistence: Any,
    ) -> InstagramBatchScrapeResponse:
        del persistence
        return response

    monkeypatch.setattr(
        ig_scraper_routes,
        "prepare_scrape_batch_payload",
        fake_prepare_scrape_batch_payload,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "scrape_profiles_batch",
        fake_scrape_profiles_batch,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "enrich_with_ai_analysis",
        fake_enrich_with_ai_analysis,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "persist_scrape_results_to_db",
        fake_persist_scrape_results_to_db,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "mark_dependency_failure",
        lambda dependency, **kwargs: failures.append(
            {"dependency": dependency, **kwargs}
        ),
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "mark_dependency_success",
        lambda *_args, **_kwargs: None,
    )

    response = client.post(
        f"{settings.API_V1_STR}/ig-scraper/profiles/batch",
        headers=superuser_token_headers,
        json={"usernames": ["alpha"]},
    )

    assert response.status_code == 200
    assert response.json()["counters"]["successful"] == 1
    assert failures == [
        {
            "dependency": "openai",
            "context": "ig-scraper-ai-enrichment",
            "detail": "AI enrichment skipped: OpenAI timeout",
            "status": "degraded",
        }
    ]


def test_recommendations_upstream_error_returns_translated_failure(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    failures: list[dict[str, Any]] = []

    async def failing_scrape_recommendations_batch(payload: Any) -> Any:
        del payload
        raise httpx.ConnectError("instagram down")

    monkeypatch.setattr(
        ig_scraper_routes,
        "scrape_recommendations_batch",
        failing_scrape_recommendations_batch,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "mark_dependency_failure",
        lambda dependency, **kwargs: failures.append(
            {"dependency": dependency, **kwargs}
        ),
    )

    response = client.post(
        f"{settings.API_V1_STR}/ig-scraper/profiles/recommendations",
        headers=superuser_token_headers,
        json={"usernames": ["alpha"], "recommended_limit": 5},
    )

    assert response.status_code == 503
    assert response.json()["dependency"] == "instagram_upstream"
    assert failures[0]["context"] == "ig-scraper-recommendations"


def test_instagram_scrape_profiles_apify_batch_uses_scrape_pipeline_without_jobs(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    service = StubInstagramJobService()
    calls: dict[str, Any] = {}

    async def fake_prepare_scrape_batch_payload(
        payload: InstagramBatchScrapeRequest,
        persistence: Any,
    ) -> tuple[InstagramBatchScrapeRequest, None]:
        calls["prepare_usernames"] = payload.usernames
        calls["persistence"] = persistence
        return payload.model_copy(update={"usernames": ["beta"]}), None

    class FakeApifyInstagramProfileScraper:
        def __init__(
            self,
            *,
            api_token: str,
            usernames: list[str],
        ) -> None:
            calls["api_token"] = api_token
            calls["scraper_usernames"] = usernames

        async def run(self) -> dict[str, Any]:
            return {
                "results": {
                    "beta": InstagramBatchProfileResult(
                        user=InstagramProfileSchema(
                            id="123",
                            username="beta",
                            profile_pic_url="https://cdn.example.com/beta.jpg",
                        ),
                        success=True,
                    ).model_dump(mode="json")
                },
                "counters": InstagramBatchCountersSchema(
                    requested=1,
                    successful=1,
                ).model_dump(mode="json"),
                "error": None,
            }

    async def fake_enrich_with_ai_analysis(
        response: InstagramBatchScrapeResponse,
        *,
        analysis_service: Any,
    ) -> InstagramBatchScrapeResponse:
        calls["analysis_service"] = analysis_service
        response.results["beta"].ai_categories = ["Fashion"]
        return response

    async def fake_persist_scrape_results_to_db(
        response: InstagramBatchScrapeResponse,
        *,
        persistence: Any,
    ) -> InstagramBatchScrapeResponse:
        calls["persisted_usernames"] = list(response.results)
        calls["persisted_persistence"] = persistence
        return response

    monkeypatch.setattr(settings, "APIFY_API_TOKEN", "test-apify-token")
    monkeypatch.setattr(
        ig_scraper_routes,
        "prepare_scrape_batch_payload",
        fake_prepare_scrape_batch_payload,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "ApifyInstagramProfileScraper",
        FakeApifyInstagramProfileScraper,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "enrich_with_ai_analysis",
        fake_enrich_with_ai_analysis,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "persist_scrape_results_to_db",
        fake_persist_scrape_results_to_db,
    )
    app.dependency_overrides[get_instagram_job_service] = lambda: service

    try:
        response = client.post(
            f"{settings.API_V1_STR}/ig-scraper/profiles/apify-batch",
            headers=superuser_token_headers,
            json={"usernames": ["alpha", "beta"]},
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 200
    assert calls["prepare_usernames"] == ["alpha", "beta"]
    assert calls["scraper_usernames"] == ["beta"]
    assert calls["persisted_usernames"] == ["beta"]
    assert response.json()["results"]["beta"]["ai_categories"] == ["Fashion"]
    assert service.create_calls == []


def test_apify_batch_without_token_returns_503(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "APIFY_API_TOKEN", None)

    response = client.post(
        f"{settings.API_V1_STR}/ig-scraper/profiles/apify-batch",
        headers=superuser_token_headers,
        json={"usernames": ["alpha"]},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "APIFY_API_TOKEN is not configured."}


def test_apify_batch_early_response_returns_without_scraper(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    early_response = _early_batch_response("alpha")

    async def fake_prepare_scrape_batch_payload(
        payload: InstagramBatchScrapeRequest,
        persistence: Any,
    ) -> tuple[InstagramBatchScrapeRequest, InstagramBatchScrapeResponse]:
        del persistence
        return payload, early_response

    class FailingApifyInstagramProfileScraper:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs
            raise AssertionError("Apify scraper should not run")

    monkeypatch.setattr(settings, "APIFY_API_TOKEN", "test-apify-token")
    monkeypatch.setattr(
        ig_scraper_routes,
        "prepare_scrape_batch_payload",
        fake_prepare_scrape_batch_payload,
    )
    monkeypatch.setattr(
        ig_scraper_routes,
        "ApifyInstagramProfileScraper",
        FailingApifyInstagramProfileScraper,
    )

    response = client.post(
        f"{settings.API_V1_STR}/ig-scraper/profiles/apify-batch",
        headers=superuser_token_headers,
        json={"usernames": ["alpha"]},
    )

    assert response.status_code == 200
    assert response.json()["error"] == "already processed"
    assert response.json()["results"]["alpha"]["success"] is False


def test_complete_instagram_scrape_job_uses_internal_auth_and_returns_conflict(
    client: TestClient,
    db: Session,
) -> None:
    service = StubInstagramJobService()
    service.complete_result = InstagramScrapeJobTerminalizationResponse(
        job_id="job-1",
        decision="conflict",
        status="done",
        notification_id="job:job-1:terminal",
        terminal_event_id="1-0",
    )
    app.dependency_overrides[get_instagram_job_service] = lambda: service
    try:
        response = client.post(
            f"{settings.API_V1_STR}/internal/ig-scraper/jobs/job-1/complete",
            headers=_internal_headers(client, db),
            json={
                "status": "done",
                "attempt": 1,
                "worker_id": "worker-1",
                "completed_at": datetime(2026, 3, 21, 12, 1, tzinfo=UTC).isoformat(),
                "summary": {
                    "usernames": [{"username": "alpha", "status": "success"}],
                    "counters": {
                        "requested": 1,
                        "successful": 1,
                        "failed": 0,
                        "not_found": 0,
                    },
                    "error": None,
                },
                "error": None,
            },
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 409
    assert response.json()["detail"]["decision"] == "conflict"
    assert service.complete_calls[0][0] == "job-1"


def test_complete_instagram_scrape_job_rejects_non_system_admin(
    client: TestClient,
    db: Session,
) -> None:
    service = StubInstagramJobService()
    app.dependency_overrides[get_instagram_job_service] = lambda: service

    email = random_email()
    password = random_lower_string()
    role = crud_admin.get_admin_role_by_code(session=db, code="platform_owner")
    assert role
    crud_admin.create_admin_user(session=db, email=email, password=password, role=role)
    token_response = client.post(
        f"{settings.API_V1_STR}/internal/login/access-token",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    try:
        response = client.post(
            f"{settings.API_V1_STR}/internal/ig-scraper/jobs/job-1/complete",
            headers=headers,
            json={
                "status": "done",
                "attempt": 1,
                "worker_id": "worker-1",
                "completed_at": datetime(2026, 3, 21, 12, 1, tzinfo=UTC).isoformat(),
                "summary": {
                    "usernames": [{"username": "alpha", "status": "success"}],
                    "counters": {
                        "requested": 1,
                        "successful": 1,
                        "failed": 0,
                        "not_found": 0,
                    },
                    "error": None,
                },
                "error": None,
            },
        )
    finally:
        app.dependency_overrides.pop(get_instagram_job_service, None)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "The admin user doesn't have enough privileges"
    }
    assert service.complete_calls == []
