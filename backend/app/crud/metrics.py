import uuid
from typing import Any, cast

from sqlmodel import Session, select

from app.models import IgMetrics
from app.schemas import Metrics, UpdateMetrics

Document = dict[str, Any]


def _parse_metrics_id(metrics_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(metrics_id)
    except ValueError:
        return None


def _serialize_metrics(record: IgMetrics) -> Document:
    return {
        "_id": str(record.id),
        "post_metrics": {
            "total_posts": record.total_posts,
            "total_likes": record.total_likes,
            "total_comments": record.total_comments,
            "avg_likes": record.avg_likes,
            "avg_comments": record.avg_comments,
            "avg_engagement_rate": record.avg_engagement_rate,
            "hashtags_per_post": record.hashtags_per_post,
            "mentions_per_post": record.mentions_per_post,
        },
        "reel_metrics": {
            "total_reels": record.total_reels,
            "total_plays": record.total_plays,
            "avg_plays": record.avg_plays,
            "avg_reel_likes": record.avg_reel_likes,
            "avg_reel_comments": record.avg_reel_comments,
        },
        "overall_post_engagement_rate": record.overall_post_engagement_rate,
        "reel_engagement_rate_on_plays": record.reel_engagement_rate_on_plays,
    }


def _apply_metrics_payload(record: IgMetrics, metrics: Metrics) -> None:
    record.total_posts = metrics.post_metrics.total_posts
    record.total_likes = metrics.post_metrics.total_likes
    record.total_comments = metrics.post_metrics.total_comments
    record.avg_likes = metrics.post_metrics.avg_likes
    record.avg_comments = metrics.post_metrics.avg_comments
    record.avg_engagement_rate = metrics.post_metrics.avg_engagement_rate
    record.hashtags_per_post = metrics.post_metrics.hashtags_per_post
    record.mentions_per_post = metrics.post_metrics.mentions_per_post
    record.total_reels = metrics.reel_metrics.total_reels
    record.total_plays = metrics.reel_metrics.total_plays
    record.avg_plays = metrics.reel_metrics.avg_plays
    record.avg_reel_likes = metrics.reel_metrics.avg_reel_likes
    record.avg_reel_comments = metrics.reel_metrics.avg_reel_comments
    record.overall_post_engagement_rate = metrics.overall_post_engagement_rate
    record.reel_engagement_rate_on_plays = metrics.reel_engagement_rate_on_plays


async def create_metrics(collection: Any, metrics: Metrics) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    record = IgMetrics()
    _apply_metrics_payload(record, metrics)
    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_metrics(record)


async def get_metrics(collection: Any, metrics_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_metrics_id(metrics_id)
    if parsed_id is None:
        return None
    record = session.get(IgMetrics, parsed_id)
    return _serialize_metrics(record) if record else None


async def list_metrics(
    collection: Any, skip: int = 0, limit: int = 100
) -> list[Document]:
    session = collection
    assert isinstance(session, Session)
    updated_at = cast(Any, IgMetrics.updated_at)
    statement = select(IgMetrics).order_by(updated_at.desc()).offset(skip).limit(limit)
    return [_serialize_metrics(record) for record in session.exec(statement).all()]


async def update_metrics(
    collection: Any, metrics_id: str, patch: UpdateMetrics
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_metrics_id(metrics_id)
    if parsed_id is None:
        return None
    record = session.get(IgMetrics, parsed_id)
    if record is None:
        return None

    updates = patch.model_dump(exclude_unset=True, mode="json")
    post_metrics = updates.get("post_metrics")
    if isinstance(post_metrics, dict):
        for key, value in post_metrics.items():
            setattr(record, key, value)

    reel_metrics = updates.get("reel_metrics")
    if isinstance(reel_metrics, dict):
        for key, value in reel_metrics.items():
            setattr(record, key, value)

    if (
        "overall_post_engagement_rate" in updates
        and updates["overall_post_engagement_rate"] is not None
    ):
        record.overall_post_engagement_rate = updates["overall_post_engagement_rate"]

    if (
        "reel_engagement_rate_on_plays" in updates
        and updates["reel_engagement_rate_on_plays"] is not None
    ):
        record.reel_engagement_rate_on_plays = updates["reel_engagement_rate_on_plays"]

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_metrics(record)


async def replace_metrics(
    collection: Any, metrics_id: str, metrics: Metrics
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_metrics_id(metrics_id)
    if parsed_id is None:
        return None
    record = session.get(IgMetrics, parsed_id)
    if record is None:
        return None

    _apply_metrics_payload(record, metrics)
    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_metrics(record)


async def delete_metrics(collection: Any, metrics_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_metrics_id(metrics_id)
    if parsed_id is None:
        return None
    record = session.get(IgMetrics, parsed_id)
    if record is None:
        return None

    document = _serialize_metrics(record)
    session.delete(record)
    session.commit()
    return document
