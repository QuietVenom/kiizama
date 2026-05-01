from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud_admin
from app.core.config import settings
from tests.utils.utils import random_email, random_lower_string


def test_get_internal_access_token(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    role = crud_admin.get_admin_role_by_code(session=db, code="platform_owner")
    assert role
    crud_admin.create_admin_user(session=db, email=email, password=password, role=role)

    login_data = {"username": email, "password": password}
    r = client.post(
        f"{settings.API_V1_STR}/internal/login/access-token", data=login_data
    )
    tokens = r.json()

    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    test_token_response = client.post(
        f"{settings.API_V1_STR}/internal/login/test-token", headers=headers
    )
    assert test_token_response.status_code == 200
    parsed_response = test_token_response.json()
    assert parsed_response["email"] == email
    assert parsed_response["role"] == "platform_owner"


def test_get_internal_access_token_incorrect_password(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    role = crud_admin.get_admin_role_by_code(session=db, code="ops")
    assert role
    crud_admin.create_admin_user(session=db, email=email, password=password, role=role)

    login_data = {"username": email, "password": "incorrect"}
    r = client.post(
        f"{settings.API_V1_STR}/internal/login/access-token", data=login_data
    )
    assert r.status_code == 400
