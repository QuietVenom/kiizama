from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.config import settings
from app.features.creators_search_history import (
    CreatorsSearchHistoryCreateRequest,
    CreatorsSearchHistoryItem,
    CreatorsSearchHistoryListResponse,
    CreatorsSearchHistoryUnavailableError,
    get_creators_search_history_service,
)
from app.main import app


class StubCreatorsSearchHistoryService:
    def __init__(self) -> None:
        self.list_calls: list[tuple[str, int]] = []
        self.create_calls: list[tuple[str, dict[str, object]]] = []
        self.list_result = CreatorsSearchHistoryListResponse(items=[], count=0)
        self.create_result = CreatorsSearchHistoryItem(
            id="history-1",
            created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            source="direct-search",
            job_id=None,
            ready_usernames=["creator_one"],
        )
        self.list_exception: Exception | None = None
        self.create_exception: Exception | None = None

    async def list_history(
        self,
        *,
        user_id: str,
        limit: int,
    ) -> CreatorsSearchHistoryListResponse:
        if self.list_exception is not None:
            raise self.list_exception
        self.list_calls.append((user_id, limit))
        return self.list_result

    async def create_entry(
        self,
        *,
        user_id: str,
        payload: CreatorsSearchHistoryCreateRequest,
    ) -> CreatorsSearchHistoryItem:
        if self.create_exception is not None:
            raise self.create_exception
        self.create_calls.append((user_id, payload.model_dump(mode="json")))
        return self.create_result


def _current_user_id(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> str:
    response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    return str(response.json()["id"])


def test_list_creators_search_history_uses_current_user(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubCreatorsSearchHistoryService()
    current_user_id = _current_user_id(client, normal_user_token_headers)
    app.dependency_overrides[get_creators_search_history_service] = lambda: service

    try:
        response = client.get(
            f"{settings.API_V1_STR}/creators-search/history",
            headers=normal_user_token_headers,
            params={"limit": 5},
        )
    finally:
        app.dependency_overrides.pop(get_creators_search_history_service, None)

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0}
    assert service.list_calls == [(current_user_id, 5)]


def test_create_creators_search_history_entry_uses_current_user(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubCreatorsSearchHistoryService()
    current_user_id = _current_user_id(client, normal_user_token_headers)
    app.dependency_overrides[get_creators_search_history_service] = lambda: service

    try:
        response = client.post(
            f"{settings.API_V1_STR}/creators-search/history",
            headers=normal_user_token_headers,
            json={
                "source": "ig-scrape-job",
                "job_id": "job-1",
                "ready_usernames": ["Creator_One", "@creator_two"],
            },
        )
    finally:
        app.dependency_overrides.pop(get_creators_search_history_service, None)

    assert response.status_code == 200
    assert response.json()["id"] == "history-1"
    assert service.create_calls == [
        (
            current_user_id,
            {
                "source": "ig-scrape-job",
                "job_id": "job-1",
                "ready_usernames": ["creator_one", "creator_two"],
            },
        )
    ]


def test_create_creators_search_history_entry_validates_job_id_and_usernames(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/creators-search/history",
        headers=normal_user_token_headers,
        json={
            "source": "ig-scrape-job",
            "ready_usernames": [],
        },
    )

    assert response.status_code == 422
    assert "ready_usernames" in str(response.json()) or "job_id" in str(response.json())


def test_list_creators_search_history_returns_standard_503_payload(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    service = StubCreatorsSearchHistoryService()
    service.list_exception = CreatorsSearchHistoryUnavailableError(
        "Redis is unavailable for creators search history."
    )
    app.dependency_overrides[get_creators_search_history_service] = lambda: service

    try:
        response = client.get(
            f"{settings.API_V1_STR}/creators-search/history",
            headers=normal_user_token_headers,
            params={"limit": 5},
        )
    finally:
        app.dependency_overrides.pop(get_creators_search_history_service, None)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Redis is unavailable for creators search history.",
        "dependency": "redis",
        "retryable": True,
    }
