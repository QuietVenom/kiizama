from typing import Annotated

from bson import ObjectId
from pydantic import (
    AnyUrl,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BioLink(BaseModel):
    title: str
    url: AnyUrl


class Profile(BaseModel):
    """
    Container for a single profile record.
    """

    # The primary key for the Profile, stored as a `str` on the instance.
    # This will be aliased to ``_id`` when sent to MongoDB,
    # but provided as ``id`` in the API requests and responses.
    id: PyObjectId | None = Field(alias="_id", default=None)
    ig_id: str = Field(...)
    username: NonEmptyStr = Field(...)
    full_name: str = Field(...)
    biography: str = Field(...)
    is_private: bool = Field(...)
    is_verified: bool = Field(...)
    profile_pic_url: AnyUrl = Field(...)
    profile_pic_src: str | None = None
    external_url: AnyUrl | None = None
    updated_date: AwareDatetime = Field(...)

    follower_count: int = Field(...)
    following_count: int = Field(...)
    media_count: int = Field(...)

    bio_links: list[BioLink] | None = Field(default_factory=list)
    ai_categories: list[str] | None = Field(default_factory=list)
    ai_roles: list[str] | None = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "65c2f0b7f6b7a8c1c3d4e5f6",
                "ig_id": "1234567890",
                "username": "stpeach",
                "full_name": "STPeach",
                "biography": "Fitness & lifestyle creator. Links below 👇",
                "is_private": "false",
                "is_verified": "true",
                "profile_pic_url": "https://cdn.example.com/stpeach.jpg",
                "external_url": "https://twitch.tv/stpeach",
                "updated_date": "2024-02-12T15:04:05Z",
                "follower_count": 1200000,
                "following_count": 350,
                "media_count": 2500,
                "bio_links": [
                    {"title": "Twitch", "url": "http://twitch.tv/stpeach"},
                    {"title": "YouTube", "url": "http://youtube.com/stpeach"},
                ],
                "ai_categories": [
                    "Motherhood / Family / Parenting",
                    "Gaming / Esports / Streaming",
                ],
                "ai_roles": ["Aspirational / Lifestyle", "Entertainment"],
            }
        },
    )


class UpdateProfile(BaseModel):
    """
    A set of optional updates to be made to a Profile document in the database.
    (All fields optional; `id` cannot be modified.)
    """

    ig_id: str | None = None
    username: NonEmptyStr | None = None
    full_name: str | None = None
    biography: str | None = None
    is_private: bool | None = None
    is_verified: bool | None = None
    profile_pic_url: AnyUrl | None = None
    external_url: AnyUrl | None = None
    updated_date: AwareDatetime | None = None

    follower_count: int | None = None
    following_count: int | None = None
    media_count: int | None = None

    bio_links: list[BioLink] | None = None
    ai_categories: list[str] | None = None
    ai_roles: list[str] | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "biography": "Fitness & lifestyle creator. Links below 👇",
                "is_private": False,
                "external_url": "https://twitch.tv/stpeach",
                "bio_links": [
                    {"title": "Twitch", "url": "http://twitch.tv/stpeach"},
                    {"title": "YouTube", "url": "http://youtube.com/stpeach"},
                ],
                "ai_categories": [
                    "Motherhood / Family / Parenting",
                    "Gaming / Esports / Streaming",
                ],
                "ai_roles": [
                    "Aspirational / Lifestyle",
                    "Entertainment",
                ],
            }
        },
    )


class ProfileCollection(BaseModel):
    """
    A container holding a list of `Profile` instances
    """

    profiles: list[Profile]
