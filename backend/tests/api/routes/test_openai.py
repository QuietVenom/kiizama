from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.features.openai.types import OpenAIResponseError


def test_run_instagram_ai_returns_503_when_openai_is_unavailable(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    with patch(
        "app.api.routes.openai.OpenAIService.execute",
        side_effect=OpenAIResponseError(
            status_code=503,
            message="OpenAI backend is unavailable.",
        ),
    ):
        response = client.post(
            f"{settings.API_V1_STR}/openai/instagram",
            headers=superuser_token_headers,
            json={"profiles": [{"username": "creator_one", "posts": []}]},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "OpenAI call failed: OpenAI backend is unavailable.",
        "dependency": "openai",
        "retryable": True,
    }


def test_run_instagram_ai_returns_502_when_openai_payload_is_invalid(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    with patch(
        "app.api.routes.openai.OpenAIService.execute",
        return_value="{not-json",
    ):
        response = client.post(
            f"{settings.API_V1_STR}/openai/instagram",
            headers=superuser_token_headers,
            json={"profiles": [{"username": "creator_one", "posts": []}]},
        )

    assert response.status_code == 502
    assert response.json()["dependency"] == "openai"
    assert response.json()["retryable"] is False
    assert response.json()["detail"].startswith("Failed to parse OpenAI response:")
