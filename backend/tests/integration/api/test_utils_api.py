from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings


def test_test_email(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    with patch("app.api.routes.utils.send_email_or_raise", return_value=None):
        response = client.post(
            f"{settings.API_V1_STR}/utils/test-email/",
            headers=superuser_token_headers,
            params={"email_to": "test@example.com"},
        )

    assert response.status_code == 201
    assert response.json() == {"message": "Test email sent"}


def test_test_email_returns_503_when_email_is_not_configured(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    with patch("app.core.config.settings.RESEND_API_KEY", None):
        response = client.post(
            f"{settings.API_V1_STR}/utils/test-email/",
            headers=superuser_token_headers,
            params={"email_to": "test@example.com"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Email service is not configured.",
        "dependency": "resend",
        "retryable": False,
    }
