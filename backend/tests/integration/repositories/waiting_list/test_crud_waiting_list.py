from collections.abc import Generator
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete

from app import crud_waiting_list
from app.models import WaitingList, WaitingListCreate
from tests.utils.utils import random_email


@pytest.fixture(scope="module", autouse=True)
def ensure_waiting_list_crud_table(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, WaitingList).__table__.create(bind=bind, checkfirst=True)
    db.exec(delete(WaitingList))
    db.commit()
    yield
    db.exec(delete(WaitingList))
    db.commit()


def test_waiting_list_create_lookup_and_duplicate_email_persist_in_postgres(
    db: Session,
) -> None:
    # Arrange
    email = random_email()

    # Act
    created = crud_waiting_list.create_waiting_list_entry(
        session=db,
        waiting_list_in=WaitingListCreate(email=email, interest="marketing"),
    )
    fetched = crud_waiting_list.get_waiting_list_by_email(session=db, email=email)
    missing = crud_waiting_list.get_waiting_list_by_email(
        session=db,
        email=random_email(),
    )

    # Assert
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.interest == "marketing"
    assert missing is None

    with pytest.raises(IntegrityError):
        crud_waiting_list.create_waiting_list_entry(
            session=db,
            waiting_list_in=WaitingListCreate(email=email, interest="creator"),
        )
    db.rollback()
