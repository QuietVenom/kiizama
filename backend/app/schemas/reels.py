from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]


class ReelItem(BaseModel):
    """
    Single reel payload stored inside a ReelsDocument.
    """

    code: str = Field(...)
    play_count: int | None = None
    comment_count: int | None = None
    like_count: int | None = None
    media_type: int | None = None
    product_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReelsDocument(BaseModel):
    """
    Container for the latest list of reels for a profile.
    """

    id: PyObjectId | None = Field(alias="_id", default=None)
    profile_id: PyObjectId = Field(...)
    reels: list[ReelItem] = Field(default_factory=list)
    updated_at: AwareDatetime = Field(...)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "65c2f0b7f6b7a8c1c3d4e5f7",
                "profile_id": "65c2f0b7f6b7a8c1c3d4e5aa",
                "updated_at": "2024-02-12T15:04:05Z",
                "reels": [
                    {
                        "code": "Coc1nRTAL7v",
                        "play_count": 647430,
                        "comment_count": 47,
                        "like_count": 6649,
                        "media_type": 2,
                        "product_type": "clips",
                    }
                ],
            }
        },
    )


class UpdateReelsDocument(BaseModel):
    """
    A set of optional updates to a ReelsDocument record.
    """

    reels: list[ReelItem] | None = None
    updated_at: AwareDatetime | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "updated_at": "2024-02-12T15:04:05Z",
                "reels": [
                    {
                        "code": "Coc1nRTAL7v",
                        "play_count": 647430,
                        "comment_count": 47,
                        "like_count": 6649,
                        "media_type": 2,
                        "product_type": "clips",
                    }
                ],
            }
        },
    )


class ReelsDocumentCollection(BaseModel):
    """
    A container holding a list of `ReelsDocument` instances.
    """

    reels: list[ReelsDocument]


Reel = ReelsDocument
UpdateReel = UpdateReelsDocument
ReelCollection = ReelsDocumentCollection
