from app.models import LegalAcceptances, UserCreate, UserRegister
from tests.utils.utils import random_email, random_password


def legal_acceptances_payload() -> dict[str, bool]:
    return {"privacy_notice": True, "terms_conditions": True}


def user_create_payload(
    *,
    email: str | None = None,
    password: str | None = None,
    full_name: str = "Test User",
) -> dict[str, object]:
    return UserCreate(
        email=email or random_email(),
        password=password or random_password(),
        full_name=full_name,
    ).model_dump(mode="json")


def signup_user_payload(
    *,
    email: str | None = None,
    password: str | None = None,
    full_name: str = "Test User",
) -> dict[str, object]:
    return UserRegister(
        email=email or random_email(),
        password=password or random_password(),
        full_name=full_name,
        legal_acceptances=LegalAcceptances(**legal_acceptances_payload()),
    ).model_dump(mode="json")
