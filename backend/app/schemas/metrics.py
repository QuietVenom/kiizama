from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]


class PostMetrics(BaseModel):
    total_posts: int = Field(...)
    total_likes: int = Field(...)
    total_comments: int = Field(...)
    avg_likes: float = Field(...)
    avg_comments: float = Field(...)
    avg_engagement_rate: float = Field(...)
    hashtags_per_post: float = Field(...)
    mentions_per_post: float = Field(...)


class ReelMetrics(BaseModel):
    total_reels: int = Field(...)
    total_plays: int = Field(...)
    avg_plays: float = Field(...)
    avg_reel_likes: float = Field(...)
    avg_reel_comments: float = Field(...)


class Metrics(BaseModel):
    """
    Container for metrics derived from posts and reels.
    """

    id: PyObjectId | None = Field(alias="_id", default=None)
    post_metrics: PostMetrics = Field(...)
    reel_metrics: ReelMetrics = Field(...)
    overall_post_engagement_rate: float = Field(...)
    reel_engagement_rate_on_plays: float = Field(...)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "65c2f0b7f6b7a8c1c3d4e5f8",
                "post_metrics": {
                    "total_posts": 12,
                    "total_likes": 838104,
                    "total_comments": 8624,
                    "avg_likes": 69842.0,
                    "avg_comments": 718.66,
                    "avg_engagement_rate": 0.0477,
                    "hashtags_per_post": 0.16,
                    "mentions_per_post": 0.0,
                },
                "reel_metrics": {
                    "total_reels": 12,
                    "total_plays": 2662988,
                    "avg_plays": 221915.66,
                    "avg_reel_likes": 44782.58,
                    "avg_reel_comments": 390.25,
                },
                "overall_post_engagement_rate": 0.5734,
                "reel_engagement_rate_on_plays": 0.1435,
            }
        },
    )


class UpdateMetrics(BaseModel):
    """
    A set of optional updates to metrics.
    """

    post_metrics: PostMetrics | None = None
    reel_metrics: ReelMetrics | None = None
    overall_post_engagement_rate: float | None = None
    reel_engagement_rate_on_plays: float | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "overall_post_engagement_rate": 0.5734,
                "reel_engagement_rate_on_plays": 0.1435,
            }
        },
    )


class MetricsCollection(BaseModel):
    """
    A container holding a list of `Metrics` instances.
    """

    metrics: list[Metrics]
