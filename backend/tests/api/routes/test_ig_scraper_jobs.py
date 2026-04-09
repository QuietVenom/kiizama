from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
        if self.create_exception is not None:
            raise self.create_exception
        self.create_calls.append(
            (
                payload.model_dump(mode="json") | {"execution_mode": execution_mode},
                owner_user_id,
            )
        )
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
                "completed_at": datetime(
                    2026, 3, 21, 12, 1, tzinfo=timezone.utc
                ).isoformat(),
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
                "completed_at": datetime(
                    2026, 3, 21, 12, 1, tzinfo=timezone.utc
                ).isoformat(),
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
