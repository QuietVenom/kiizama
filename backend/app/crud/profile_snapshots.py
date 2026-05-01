import uuid
from typing import Any, cast

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models import (
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
)
from app.schemas import ProfileSnapshot, UpdateProfileSnapshot

Document = dict[str, Any]


def _parse_snapshot_id(snapshot_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(snapshot_id)
    except ValueError:
        return None


def _parse_optional_uuid(raw_value: str | None) -> uuid.UUID | None:
    if not raw_value:
        return None
    try:
        return uuid.UUID(raw_value)
    except ValueError:
        return None


def _serialize_profile(record: IgProfile) -> dict[str, Any]:
    return {
        "_id": str(record.id),
        "ig_id": record.ig_id,
        "username": record.username,
        "full_name": record.full_name or "",
        "biography": record.biography or "",
        "is_private": record.is_private,
        "is_verified": record.is_verified,
        "profile_pic_url": record.profile_pic_url,
        "profile_pic_src": None,
        "external_url": record.external_url,
        "updated_date": record.updated_at,
        "follower_count": record.follower_count,
        "following_count": record.following_count,
        "media_count": record.media_count,
        "bio_links": record.bio_links,
        "ai_categories": record.ai_categories,
        "ai_roles": record.ai_roles,
    }


def _serialize_posts(record: IgPostsDocument) -> dict[str, Any]:
    return {
        "_id": str(record.id),
        "profile_id": str(record.profile_id),
        "posts": record.items,
        "updated_at": record.updated_at,
    }


def _serialize_reels(record: IgReelsDocument) -> dict[str, Any]:
    return {
        "_id": str(record.id),
        "profile_id": str(record.profile_id),
        "reels": record.items,
        "updated_at": record.updated_at,
    }


def _serialize_metrics(record: IgMetrics) -> dict[str, Any]:
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


def _serialize_snapshot(record: IgProfileSnapshot) -> Document:
    return {
        "_id": str(record.id),
        "profile_id": str(record.profile_id),
        "post_ids": [str(record.posts_document_id)] if record.posts_document_id else [],
        "reel_ids": [str(record.reels_document_id)] if record.reels_document_id else [],
        "metrics_id": str(record.metrics_id) if record.metrics_id else None,
        "scraped_at": record.scraped_at,
    }


def _serialize_snapshot_full(
    record: IgProfileSnapshot,
    *,
    profile: IgProfile | None,
    posts_document: IgPostsDocument | None,
    reels_document: IgReelsDocument | None,
    metrics: IgMetrics | None,
) -> Document:
    snapshot = _serialize_snapshot(record)
    snapshot["profile"] = _serialize_profile(profile) if profile else None
    snapshot["posts"] = [_serialize_posts(posts_document)] if posts_document else []
    snapshot["reels"] = [_serialize_reels(reels_document)] if reels_document else []
    snapshot["metrics"] = _serialize_metrics(metrics) if metrics else None
    return snapshot


def _resolve_profile_ids_by_usernames(
    session: Session,
    usernames: list[str],
) -> list[uuid.UUID]:
    username_column = cast(Any, IgProfile.username)
    profiles = session.exec(
        select(IgProfile).where(username_column.in_(list(dict.fromkeys(usernames))))
    ).all()
    return [profile.id for profile in profiles]


def _build_profile_snapshots_full_statement(
    *,
    skip: int,
    limit: int,
    profile_ids: list[uuid.UUID] | None,
) -> Any:
    scraped_at = cast(Any, IgProfileSnapshot.scraped_at)
    snapshot_id_column = cast(Any, IgProfileSnapshot.id)
    profile_relationship = cast(Any, IgProfileSnapshot.profile)
    posts_document_relationship = cast(Any, IgProfileSnapshot.posts_document)
    reels_document_relationship = cast(Any, IgProfileSnapshot.reels_document)
    metrics_relationship = cast(Any, IgProfileSnapshot.metrics)
    statement = select(IgProfileSnapshot).options(
        selectinload(profile_relationship),
        selectinload(posts_document_relationship),
        selectinload(reels_document_relationship),
        selectinload(metrics_relationship),
    )
    if profile_ids is None:
        return statement.order_by(scraped_at.desc()).offset(skip).limit(limit)

    profile_id_column = cast(Any, IgProfileSnapshot.profile_id)
    ranked_snapshots = (
        select(
            snapshot_id_column.label("snapshot_id"),
            func.row_number()
            .over(
                partition_by=profile_id_column,
                order_by=(scraped_at.desc(), snapshot_id_column.desc()),
            )
            .label("snapshot_rank"),
        )
        .where(profile_id_column.in_(profile_ids))
        .subquery()
    )
    ranked_snapshot_id_column = cast(Any, ranked_snapshots.c.snapshot_id)
    snapshot_rank_column = cast(Any, ranked_snapshots.c.snapshot_rank)
    return (
        statement.join(
            ranked_snapshots,
            snapshot_id_column == ranked_snapshot_id_column,
        )
        .where(snapshot_rank_column > skip)
        .where(snapshot_rank_column <= skip + limit)
        .order_by(scraped_at.desc(), snapshot_id_column.desc())
    )


def create_profile_snapshot(
    collection: Any, snapshot: ProfileSnapshot
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    record = IgProfileSnapshot(
        profile_id=uuid.UUID(snapshot.profile_id),
        posts_document_id=_parse_optional_uuid(snapshot.post_ids[0])
        if snapshot.post_ids
        else None,
        reels_document_id=_parse_optional_uuid(snapshot.reel_ids[0])
        if snapshot.reel_ids
        else None,
        metrics_id=_parse_optional_uuid(snapshot.metrics_id),
        scraped_at=snapshot.scraped_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_snapshot(record)


def get_profile_snapshot(collection: Any, snapshot_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_snapshot_id(snapshot_id)
    if parsed_id is None:
        return None
    record = session.get(IgProfileSnapshot, parsed_id)
    return _serialize_snapshot(record) if record else None


def get_profile_snapshot_by_profile_id(
    collection: Any, profile_id: str
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_profile_id = _parse_optional_uuid(profile_id)
    if parsed_profile_id is None:
        return None
    scraped_at = cast(Any, IgProfileSnapshot.scraped_at)
    statement = (
        select(IgProfileSnapshot)
        .where(IgProfileSnapshot.profile_id == parsed_profile_id)
        .order_by(scraped_at.desc())
    )
    record = session.exec(statement).first()
    return _serialize_snapshot(record) if record else None


def list_profile_snapshots(
    collection: Any,
    skip: int = 0,
    limit: int = 100,
    snapshot_ids: list[str] | None = None,
) -> list[Document]:
    session = collection
    assert isinstance(session, Session)
    scraped_at = cast(Any, IgProfileSnapshot.scraped_at)
    snapshot_id_column = cast(Any, IgProfileSnapshot.id)
    statement = select(IgProfileSnapshot).order_by(scraped_at.desc())
    if snapshot_ids is not None:
        parsed_ids = [
            parsed for raw_id in snapshot_ids if (parsed := _parse_snapshot_id(raw_id))
        ]
        if not parsed_ids:
            return []
        statement = statement.where(snapshot_id_column.in_(parsed_ids))
    statement = statement.offset(skip).limit(limit)
    return [_serialize_snapshot(record) for record in session.exec(statement).all()]


def list_profile_snapshots_full(
    collection: Any,
    skip: int = 0,
    limit: int = 100,
    usernames: list[str] | None = None,
) -> list[Document]:
    session = collection
    assert isinstance(session, Session)
    if usernames is not None and not usernames:
        return []
    profile_ids: list[uuid.UUID] | None = None
    if usernames:
        profile_ids = _resolve_profile_ids_by_usernames(session, usernames)
        if not profile_ids:
            return []

    statement = _build_profile_snapshots_full_statement(
        skip=skip,
        limit=limit,
        profile_ids=profile_ids,
    )
    snapshots = session.exec(statement).all()

    full_snapshots: list[Document] = []
    for snapshot in snapshots:
        full_snapshots.append(
            _serialize_snapshot_full(
                snapshot,
                profile=snapshot.profile,
                posts_document=snapshot.posts_document,
                reels_document=snapshot.reels_document,
                metrics=snapshot.metrics,
            )
        )
    return full_snapshots


def update_profile_snapshot(
    collection: Any, snapshot_id: str, patch: UpdateProfileSnapshot
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_snapshot_id(snapshot_id)
    if parsed_id is None:
        return None
    record = session.get(IgProfileSnapshot, parsed_id)
    if record is None:
        return None

    updates = patch.model_dump(exclude_unset=True, mode="json")
    if "profile_id" in updates and updates["profile_id"] is not None:
        record.profile_id = uuid.UUID(updates["profile_id"])
    if "post_ids" in updates:
        record.posts_document_id = (
            _parse_optional_uuid(updates["post_ids"][0])
            if updates["post_ids"]
            else None
        )
    if "reel_ids" in updates:
        record.reels_document_id = (
            _parse_optional_uuid(updates["reel_ids"][0])
            if updates["reel_ids"]
            else None
        )
    if "metrics_id" in updates:
        record.metrics_id = _parse_optional_uuid(updates["metrics_id"])
    if "scraped_at" in updates and updates["scraped_at"] is not None:
        record.scraped_at = updates["scraped_at"]

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_snapshot(record)


def replace_profile_snapshot(
    collection: Any, snapshot_id: str, snapshot: ProfileSnapshot
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_snapshot_id(snapshot_id)
    if parsed_id is None:
        return None
    record = session.get(IgProfileSnapshot, parsed_id)
    if record is None:
        return None

    record.profile_id = uuid.UUID(snapshot.profile_id)
    record.posts_document_id = (
        _parse_optional_uuid(snapshot.post_ids[0]) if snapshot.post_ids else None
    )
    record.reels_document_id = (
        _parse_optional_uuid(snapshot.reel_ids[0]) if snapshot.reel_ids else None
    )
    record.metrics_id = _parse_optional_uuid(snapshot.metrics_id)
    record.scraped_at = snapshot.scraped_at

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_snapshot(record)


def delete_profile_snapshot(collection: Any, snapshot_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_snapshot_id(snapshot_id)
    if parsed_id is None:
        return None
    record = session.get(IgProfileSnapshot, parsed_id)
    if record is None:
        return None

    document = _serialize_snapshot(record)
    session.delete(record)
    session.commit()
    return document
