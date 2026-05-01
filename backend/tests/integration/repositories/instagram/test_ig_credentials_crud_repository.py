from collections.abc import Generator
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlmodel import Session, delete

from app.crud.ig_credentials import (
    create_ig_credential,
    delete_ig_credential,
    get_ig_credential,
    list_ig_credentials,
    replace_ig_credential,
    update_ig_credential,
    update_ig_credential_session,
)
from app.models import IgCredential
from app.schemas import IgCredential as IgCredentialSchema
from app.schemas import UpdateIgCredential
from tests.utils.utils import random_email, random_password


@pytest.fixture(autouse=True)
def configure_ig_credentials_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY_IG_CREDENTIALS", "test-secret-key-ig")


@pytest.fixture(scope="module", autouse=True)
def ensure_ig_credentials_crud_table(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgCredential).__table__.create(bind=bind, checkfirst=True)
    db.exec(delete(IgCredential))
    db.commit()
    yield
    db.exec(delete(IgCredential))
    db.commit()


def _credential(
    *,
    login_username: str | None = None,
    session_value: str = "initial",
) -> IgCredentialSchema:
    return IgCredentialSchema(
        login_username=login_username or random_email(),
        password=random_password(),
        session={"cookies": [{"name": "sessionid", "value": session_value}]},
    )


def test_ig_credentials_crud_serializes_sessions_and_encrypted_password(
    db: Session,
) -> None:
    # Arrange
    credential = _credential()

    # Act
    created = create_ig_credential(db, credential)
    credential_id = created["_id"]
    fetched = get_ig_credential(db, credential_id)
    listed = list_ig_credentials(db, skip=0, limit=20)
    updated = update_ig_credential(
        db,
        credential_id,
        UpdateIgCredential(
            login_username=f"updated-{credential.login_username}",
            password=random_password(),
        ),
    )
    session_updated = update_ig_credential_session(
        db,
        credential_id,
        {"cookies": [{"name": "sessionid", "value": "updated-session"}]},
    )
    replaced = replace_ig_credential(db, credential_id, _credential())
    deleted = delete_ig_credential(db, credential_id)

    # Assert
    assert created["login_username"] == credential.login_username
    assert created["password"] != credential.password
    assert created["session"] == credential.session
    assert fetched == created
    assert credential_id in {item["_id"] for item in listed}
    assert updated is not None
    assert updated["login_username"].startswith("updated-")
    assert session_updated is not None
    assert session_updated["session"]["cookies"][0]["value"] == "updated-session"
    assert replaced is not None
    assert replaced["login_username"] != updated["login_username"]
    assert deleted is not None
    assert deleted["_id"] == credential_id
    assert get_ig_credential(db, credential_id) is None
    assert get_ig_credential(db, "not-a-uuid") is None
    assert update_ig_credential(db, str(uuid4()), UpdateIgCredential()) is None
    assert update_ig_credential_session(db, "not-a-uuid", None) is None
    assert delete_ig_credential(db, "not-a-uuid") is None


def test_ig_credentials_duplicate_login_username_raises_conflict(db: Session) -> None:
    login_username = random_email()
    create_ig_credential(db, _credential(login_username=login_username))

    with pytest.raises(HTTPException) as exc_info:
        create_ig_credential(db, _credential(login_username=login_username))

    assert exc_info.value.status_code == 409
