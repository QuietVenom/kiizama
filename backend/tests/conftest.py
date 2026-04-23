from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.core.testing_safety import assert_safe_test_database_url
from app.features.billing.models import BillingCustomerSyncTask, BillingNotice
from app.main import app
from app.models import (
    BillingSubscription,
    BillingWebhookEvent,
    UsageCycle,
    UsageCycleFeature,
    UsageEvent,
    UsageReservation,
    User,
    UserAccessOverride,
    UserBillingAccount,
    UserLegalAcceptance,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers

assert_safe_test_database_url(str(settings.SQLALCHEMY_DATABASE_URI))

pytest_plugins = (
    "tests.fixtures.db",
    "tests.fixtures.redis",
)


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        session.execute(delete(UsageEvent))
        session.execute(delete(UsageReservation))
        session.execute(delete(UsageCycleFeature))
        session.execute(delete(UsageCycle))
        session.execute(delete(UserAccessOverride))
        session.execute(delete(BillingNotice))
        session.execute(delete(BillingCustomerSyncTask))
        session.execute(delete(BillingWebhookEvent))
        session.execute(delete(BillingSubscription))
        session.execute(delete(UserBillingAccount))
        session.execute(delete(UserLegalAcceptance))
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
