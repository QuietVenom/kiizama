from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import WaitingList
from tests.utils.utils import random_email


def test_create_waiting_list_entry(client: TestClient, db: Session) -> None:
    email = random_email()
    payload = {
        "email": email,
        "interest": "public_relations",
    }

    response = client.post(
        f"{settings.API_V1_STR}/public/waiting-list/",
        json=payload,
    )
    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "Registro recibido. Gracias por unirte a la waiting list."
    )

    entry = db.exec(select(WaitingList).where(WaitingList.email == email)).first()
    assert entry
    assert entry.email == email
    assert entry.interest == "public_relations"


def test_create_waiting_list_entry_existing_email(
    client: TestClient, db: Session
) -> None:
    email = random_email().upper()
    payload = {
        "email": email,
        "interest": "marketing",
    }

    first_response = client.post(
        f"{settings.API_V1_STR}/public/waiting-list/",
        json=payload,
    )
    assert first_response.status_code == 200

    second_response = client.post(
        f"{settings.API_V1_STR}/public/waiting-list/",
        json=payload,
    )
    assert second_response.status_code == 200
    assert second_response.json()["message"] == "Ya te tenemos registrado."

    normalized_email = email.lower()
    entries = db.exec(
        select(WaitingList).where(WaitingList.email == normalized_email)
    ).all()
    assert len(entries) == 1
