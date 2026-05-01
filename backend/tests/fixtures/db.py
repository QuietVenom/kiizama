from collections.abc import Generator

import pytest
from sqlmodel import Session


@pytest.fixture
def db_session(db: Session) -> Generator[Session, None, None]:
    """Function-scoped alias for tests that should prefer isolated DB intent."""
    yield db
