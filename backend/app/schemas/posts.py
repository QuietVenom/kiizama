from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]


class PostItem(BaseModel):
    """
    Single post payload stored inside a PostsDocument.
    """

    code: str = Field(...)
    caption_text: str | None = None
    is_paid_partnership: bool | None = None
    coauthor_producers: list[str] = Field(default_factory=list)
    comment_count: int | None = None
    like_count: int | None = None
    usertags: list[str] = Field(default_factory=list)
    media_type: int | None = None
    product_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PostsDocument(BaseModel):
    """
    Container for the latest list of posts for a profile.
    """

    id: PyObjectId | None = Field(alias="_id", default=None)
    profile_id: PyObjectId = Field(...)
    posts: list[PostItem] = Field(default_factory=list)
    updated_at: AwareDatetime = Field(...)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "65c2f0b7f6b7a8c1c3d4e5f6",
                "profile_id": "65c2f0b7f6b7a8c1c3d4e5aa",
                "updated_at": "2024-02-12T15:04:05Z",
                "posts": [
                    {
                        "code": "CVTH2dLvmkt",
                        "caption_text": "What makes you smile?",
                        "is_paid_partnership": False,
                        "coauthor_producers": [],
                        "comment_count": 860,
                        "like_count": 141588,
                        "usertags": ["nickthiessen"],
                        "media_type": 8,
                        "product_type": "carousel_container",
                    }
                ],
            }
        },
    )


class UpdatePostsDocument(BaseModel):
    """
    A set of optional updates to a PostsDocument record.
    """

    posts: list[PostItem] | None = None
    updated_at: AwareDatetime | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "updated_at": "2024-02-12T15:04:05Z",
                "posts": [
                    {
                        "code": "CVTH2dLvmkt",
                        "caption_text": "What makes you smile?",
                        "is_paid_partnership": False,
                        "coauthor_producers": [],
                        "comment_count": 860,
                        "like_count": 141588,
                        "usertags": ["nickthiessen"],
                        "media_type": 8,
                        "product_type": "carousel_container",
                    }
                ],
            }
        },
    )


class PostsDocumentCollection(BaseModel):
    """
    A container holding a list of `PostsDocument` instances.
    """

    posts: list[PostsDocument]


Post = PostsDocument
UpdatePost = UpdatePostsDocument
PostCollection = PostsDocumentCollection
