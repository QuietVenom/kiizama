from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramScrapeJobTerminalizationResponse,
)
from sqlmodel import Session

from app import crud_admin
from app.core.config import settings
from app.features.ig_scraper_jobs import get_instagram_job_service
from app.features.job_control.repository import JobControlUnavailableError
from app.main import app
from tests.utils.utils import random_email, random_lower_string


class StubInstagramJobService:
    def __init__(self) -> None:
        self.create_calls: list[tuple[dict[str, Any], str]] = []
        self.get_calls: list[str] = []
        self.complete_calls: list[tuple[str, dict[str, Any]]] = []
        self.create_exception: Exception | None = None
        self.get_exception: Exception | None = None
        self.create_job_id = "job-1"
        self.get_result: Any = None
        self.complete_result: Any = None

    async def create_job(self, *, payload: Any, owner_user_id: str) -> str:
        if self.create_exception is not None:
            raise self.create_exception
        self.create_calls.append((payload.model_dump(mode="json"), owner_user_id))
        return self.create_job_id

    async def get_job(self, *, job_id: str) -> Any:
        if self.get_exception is not None:
            raise self.get_exception
        self.get_calls.append(job_id)
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
    assert service.get_calls == ["job-1"]


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
