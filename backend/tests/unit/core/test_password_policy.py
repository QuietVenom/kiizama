import pytest
from pydantic_core import PydanticCustomError

from app.core.password_policy import validate_new_password


def test_validate_new_password_accepts_required_character_classes() -> None:
    assert validate_new_password("Valid123!") == "Valid123!"


@pytest.mark.parametrize(
    ("password", "error_type"),
    [
        ("valid123!", "password_uppercase"),
        ("Validabc!", "password_number"),
        ("Valid1234", "password_special"),
    ],
)
def test_validate_new_password_missing_requirement_raises_custom_error(
    password: str,
    error_type: str,
) -> None:
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_new_password(password)

    assert exc_info.value.type == error_type
