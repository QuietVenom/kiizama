from typing import Annotated

from bson import ObjectId
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

from .metrics import Metrics
from .posts import PostsDocument
from .profiles import Profile
from .reels import ReelsDocument

PyObjectId = Annotated[str, BeforeValidator(str)]


class ProfileSnapshot(BaseModel):
    """
    Relates a profile to scraped posts, reels, and metrics at a point in time.
    """

    id: PyObjectId | None = Field(alias="_id", default=None)
    profile_id: PyObjectId = Field(...)
    post_ids: list[PyObjectId] = Field(default_factory=list)
    reel_ids: list[PyObjectId] = Field(default_factory=list)
    metrics_id: PyObjectId | None = None
    scraped_at: AwareDatetime = Field(...)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "65c2f0b7f6b7a8c1c3d4e5f9",
                "profile_id": "65c2f0b7f6b7a8c1c3d4e5f6",
                "post_ids": [
                    "65c2f0b7f6b7a8c1c3d4e6a1",
                    "65c2f0b7f6b7a8c1c3d4e6a2",
                ],
                "reel_ids": [
                    "65c2f0b7f6b7a8c1c3d4e7b1",
                    "65c2f0b7f6b7a8c1c3d4e7b2",
                ],
                "metrics_id": "65c2f0b7f6b7a8c1c3d4e8c1",
                "scraped_at": "2024-02-12T15:04:05Z",
            }
        },
    )


class UpdateProfileSnapshot(BaseModel):
    """
    A set of optional updates to a ProfileSnapshot document.
    """

    profile_id: PyObjectId | None = None
    post_ids: list[PyObjectId] | None = None
    reel_ids: list[PyObjectId] | None = None
    metrics_id: PyObjectId | None = None
    scraped_at: AwareDatetime | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "metrics_id": "65c2f0b7f6b7a8c1c3d4e8c1",
            }
        },
    )


class ProfileSnapshotCollection(BaseModel):
    """
    A container holding a list of `ProfileSnapshot` instances.
    """

    snapshots: list[ProfileSnapshot]


class ProfileSnapshotExpanded(ProfileSnapshot):
    """
    Profile snapshot with full related data resolved via lookup.
    """

    profile: Profile | None = None
    posts: list[PostsDocument] = Field(default_factory=list)
    reels: list[ReelsDocument] = Field(default_factory=list)
    metrics: Metrics | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class ProfileSnapshotExpandedCollection(BaseModel):
    """
    A container holding a list of `ProfileSnapshotExpanded` instances.
    """

    snapshots: list[ProfileSnapshotExpanded]
