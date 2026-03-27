import uuid
from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.core.config import settings
from app.models import IgCredential
from tests.utils.utils import random_email, random_password


@pytest.fixture(autouse=True)
def configure_ig_credentials_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY_IG_CREDENTIALS", "test-secret-key-ig")


@pytest.fixture(scope="module", autouse=True)
def ensure_ig_credentials_table(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgCredential).__table__.create(bind=bind, checkfirst=True)
    db.exec(delete(IgCredential))
    db.commit()
    yield
    db.exec(delete(IgCredential))
    db.commit()


def test_create_and_read_ig_credential(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    login_username = random_email()
    password = random_password()
    payload = {
        "login_username": login_username,
        "password": password,
        "session": {"cookies": [{"name": "sessionid", "value": "abc"}]},
    }

    response = client.post(
        f"{settings.API_V1_STR}/ig-credentials/",
        headers=superuser_token_headers,
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["login_username"] == login_username
    assert data["session"] == payload["session"]
    assert "_id" in data

    record = db.exec(
        select(IgCredential).where(IgCredential.id == uuid.UUID(data["_id"]))
    ).one()
    assert record.password_encrypted != password
    assert record.session_encrypted is not None

    read_response = client.get(
        f"{settings.API_V1_STR}/ig-credentials/{data['_id']}",
        headers=superuser_token_headers,
    )

    assert read_response.status_code == 200
    assert read_response.json() == data


def test_duplicate_ig_credential_returns_conflict(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    login_username = random_email()
    payload = {
        "login_username": login_username,
        "password": random_password(),
        "session": None,
    }

    first = client.post(
        f"{settings.API_V1_STR}/ig-credentials/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert first.status_code == 201

    second = client.post(
        f"{settings.API_V1_STR}/ig-credentials/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "login_username ya existe"


def test_update_replace_and_delete_ig_credential(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    create_payload = {
        "login_username": random_email(),
        "password": random_password(),
        "session": None,
    }
    create_response = client.post(
        f"{settings.API_V1_STR}/ig-credentials/",
        headers=superuser_token_headers,
        json=create_payload,
    )
    assert create_response.status_code == 201
    credential_id = create_response.json()["_id"]

    patch_response = client.patch(
        f"{settings.API_V1_STR}/ig-credentials/{credential_id}",
        headers=superuser_token_headers,
        json={"session": {"cookies": [{"name": "sessionid", "value": "patched"}]}},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["session"]["cookies"][0]["value"] == "patched"

    replace_payload = {
        "login_username": random_email(),
        "password": random_password(),
        "session": {"cookies": [{"name": "sessionid", "value": "replaced"}]},
    }
    replace_response = client.put(
        f"{settings.API_V1_STR}/ig-credentials/{credential_id}",
        headers=superuser_token_headers,
        json=replace_payload,
    )
    assert replace_response.status_code == 200
    assert (
        replace_response.json()["login_username"] == replace_payload["login_username"]
    )
    assert replace_response.json()["session"] == replace_payload["session"]

    delete_response = client.delete(
        f"{settings.API_V1_STR}/ig-credentials/{credential_id}",
        headers=superuser_token_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["_id"] == credential_id

    missing_response = client.get(
        f"{settings.API_V1_STR}/ig-credentials/{credential_id}",
        headers=superuser_token_headers,
    )
    assert missing_response.status_code == 404
