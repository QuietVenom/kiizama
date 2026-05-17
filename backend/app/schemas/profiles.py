from typing import Annotated, Literal

from pydantic import (
    AnyUrl,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ProfileSearchSortBy = Literal["username", "follower_count", "updated_date"]
ProfileSearchSortOrder = Literal["asc", "desc"]


class BioLink(BaseModel):
    title: str
    url: AnyUrl


class Profile(BaseModel):
    """
    Container for a single profile record.
    """

    # The primary key for the profile is serialized as a string and exposed as `_id`.
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


class ProfileSearchFilters(BaseModel):
    query: str | None = Field(default=None, min_length=3, max_length=100)
    ai_categories: list[NonEmptyStr] = Field(default_factory=list, max_length=25)
    ai_roles: list[NonEmptyStr] = Field(default_factory=list, max_length=25)
    follower_count_min: int | None = Field(default=None, ge=0)
    follower_count_max: int | None = Field(default=None, ge=0)
    sort_by: ProfileSearchSortBy = "follower_count"
    sort_order: ProfileSearchSortOrder = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value or None

    @field_validator("ai_categories", "ai_roles", mode="before")
    @classmethod
    def normalize_filters(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, list):
            raw_items = value
        else:
            raise ValueError("Expected a list of strings.")

        normalized: list[str] = []
        seen: set[str] = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, str):
                raise ValueError("Expected a list of strings.")
            item = raw_item.strip()
            if not item:
                continue
            item_key = item.casefold()
            if item_key in seen:
                continue
            seen.add(item_key)
            normalized.append(item)
        return normalized

    @model_validator(mode="after")
    def validate_follower_range(self) -> "ProfileSearchFilters":
        if (
            self.follower_count_min is not None
            and self.follower_count_max is not None
            and self.follower_count_min > self.follower_count_max
        ):
            raise ValueError(
                "follower_count_min cannot be greater than follower_count_max."
            )
        return self


class ProfileSearchPagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ProfileSearchResponse(BaseModel):
    profiles: list[Profile]
    pagination: ProfileSearchPagination
