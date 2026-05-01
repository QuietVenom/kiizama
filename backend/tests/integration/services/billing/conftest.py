from collections.abc import Generator

import pytest
from sqlmodel import Session

from app.core.db import engine
from tests.fixtures.billing import cleanup_invalid_billing_subscriptions


@pytest.fixture(scope="module", autouse=True)
def cleanup_invalid_billing_state() -> Generator[None, None, None]:
    yield

    with Session(engine) as session:
        cleanup_invalid_billing_subscriptions(session=session)
