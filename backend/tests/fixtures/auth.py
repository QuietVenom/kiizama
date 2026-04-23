from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def superuser_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


def user_headers(
    client: TestClient, db: Session, email: str | None = None
) -> dict[str, str]:
    return authentication_token_from_email(
        client=client,
        email=email or settings.EMAIL_TEST_USER,
        db=db,
    )
