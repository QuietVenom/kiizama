from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class IgCredential(BaseModel):
    """
    Container for a single Instagram credential record.
    """

    id: PyObjectId | None = Field(alias="_id", default=None)
    login_username: NonEmptyStr = Field(...)
    password: str = Field(...)
    session: dict[str, Any] | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "65c2f0b7f6b7a8c1c3d4e5fa",
                "login_username": "user@example.com",
                "password": "my_plain_password",
                "session": {
                    "cookies": [
                        {
                            "name": "sessionid",
                            "value": "abcd",
                            "domain": ".instagram.com",
                        }
                    ]
                },
            }
        },
    )


class IgCredentialPublic(BaseModel):
    """
    Public view of a single Instagram credential record.
    """

    id: PyObjectId | None = Field(alias="_id", default=None)
    login_username: NonEmptyStr = Field(...)
    session: dict[str, Any] | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "65c2f0b7f6b7a8c1c3d4e5fa",
                "login_username": "user@example.com",
                "session": {
                    "cookies": [
                        {
                            "name": "sessionid",
                            "value": "abcd",
                            "domain": ".instagram.com",
                        }
                    ]
                },
            }
        },
    )


class UpdateIgCredential(BaseModel):
    """
    Optional updates to be made to an Instagram credential document.
    """

    login_username: NonEmptyStr | None = None
    password: str | None = None
    session: dict[str, Any] | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "password": "new_plain_password",
                "session": {"cookies": []},
            }
        },
    )


class IgCredentialCollection(BaseModel):
    """
    A container holding a list of `IgCredential` instances.
    """

    ig_credentials: list[IgCredential]


class IgCredentialPublicCollection(BaseModel):
    """
    A container holding a list of `IgCredentialPublic` instances.
    """

    ig_credentials: list[IgCredentialPublic]
