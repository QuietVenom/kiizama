import re
from typing import Annotated

from pydantic import AfterValidator
from pydantic_core import PydanticCustomError

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 25
PASSWORD_SPECIAL_CHARACTERS = "!@#$%"

_UPPERCASE_RE = re.compile(r"[A-Z]")
_NUMBER_RE = re.compile(r"\d")
_SPECIAL_CHARACTER_RE = re.compile(rf"[{re.escape(PASSWORD_SPECIAL_CHARACTERS)}]")


def validate_new_password(value: str) -> str:
    if not _UPPERCASE_RE.search(value):
        raise PydanticCustomError(
            "password_uppercase",
            "Password must include at least 1 uppercase letter",
        )
    if not _NUMBER_RE.search(value):
        raise PydanticCustomError(
            "password_number",
            "Password must include at least 1 number",
        )
    if not _SPECIAL_CHARACTER_RE.search(value):
        raise PydanticCustomError(
            "password_special",
            "Password must include at least 1 special character (!, @, #, $, %)",
        )
    return value


NewPasswordStr = Annotated[str, AfterValidator(validate_new_password)]
