import asyncio
from collections.abc import Generator
from typing import Any, cast

import pytest
from sqlmodel import Session, delete, select

from app.core.db import engine
from app.crud.ig_credentials import create_ig_credential
from app.features.ig_scraper_runtime import BackendInstagramCredentialsStore
from app.models import IgCredential
from app.schemas import IgCredential as IgCredentialSchema
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


def test_backend_instagram_credentials_store_lists_and_persists_sessions(
    db: Session,
) -> None:
    created = create_ig_credential(
        db,
        IgCredentialSchema(
            login_username=random_email(),
            password=random_password(),
            session={"cookies": [{"name": "sessionid", "value": "initial"}]},
        ),
    )
    credential_id = created["_id"]

    store = BackendInstagramCredentialsStore(lambda: Session(engine))
    credentials = asyncio.run(store.list_credentials(limit=10))

    candidate = next(item for item in credentials if item.id == credential_id)
    assert candidate.login_username == created["login_username"]
    assert candidate.encrypted_password
    assert candidate.session == {"cookies": [{"name": "sessionid", "value": "initial"}]}

    persisted = asyncio.run(
        store.persist_session(
            credential_id,
            {"cookies": [{"name": "sessionid", "value": "updated"}]},
        )
    )
    assert persisted is True

    refreshed = db.exec(
        select(IgCredential).where(
            IgCredential.login_username == created["login_username"]
        )
    ).one()
    assert refreshed.session_encrypted is not None
