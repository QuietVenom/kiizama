import asyncio
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.core.mongodb import close_mongo_client
from app.core.testing_safety import assert_safe_test_database_url
from app.main import app
from app.models import User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers

assert_safe_test_database_url(str(settings.SQLALCHEMY_DATABASE_URI))


@pytest.fixture(scope="session", autouse=True)
def disable_mongodb_for_tests() -> Generator[None, None, None]:
    original_mongodb_url = settings.MONGODB_URL
    settings.MONGODB_URL = None
    asyncio.run(close_mongo_client())
    yield
    asyncio.run(close_mongo_client())
    settings.MONGODB_URL = original_mongodb_url


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
