import uuid
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import IgProfile
from app.schemas import Profile, UpdateProfile

Document = dict[str, Any]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_profile_id(profile_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(profile_id)
    except ValueError:
        return None


def _serialize_profile(record: IgProfile) -> Document:
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


def _raise_duplicate_profile(exc: IntegrityError) -> None:
    raise HTTPException(status_code=409, detail="ig_id ya existe") from exc


async def create_profile(collection: Any, profile: Profile) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    record = IgProfile(
        ig_id=profile.ig_id,
        username=profile.username,
        full_name=profile.full_name,
        biography=profile.biography,
        is_private=profile.is_private,
        is_verified=profile.is_verified,
        profile_pic_url=str(profile.profile_pic_url),
        external_url=str(profile.external_url) if profile.external_url else None,
        follower_count=profile.follower_count,
        following_count=profile.following_count,
        media_count=profile.media_count,
        bio_links=[item.model_dump(mode="json") for item in profile.bio_links or []],
        ai_categories=profile.ai_categories or [],
        ai_roles=profile.ai_roles or [],
        updated_at=profile.updated_date,
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_duplicate_profile(exc)
    session.refresh(record)
    return _serialize_profile(record)


async def get_profile(collection: Any, profile_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_profile_id(profile_id)
    if parsed_id is None:
        return None
    record = session.get(IgProfile, parsed_id)
    return _serialize_profile(record) if record else None


async def get_profile_by_username(collection: Any, username: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    statement = select(IgProfile).where(IgProfile.username == username)
    record = session.exec(statement).first()
    return _serialize_profile(record) if record else None


async def get_profile_by_ig_id(collection: Any, ig_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    statement = select(IgProfile).where(IgProfile.ig_id == ig_id)
    record = session.exec(statement).first()
    return _serialize_profile(record) if record else None


async def list_profiles(
    collection: Any, skip: int = 0, limit: int = 100
) -> list[Document]:
    session = collection
    assert isinstance(session, Session)
    updated_at = cast(Any, IgProfile.updated_at)
    statement = select(IgProfile).order_by(updated_at.desc()).offset(skip).limit(limit)
    return [_serialize_profile(record) for record in session.exec(statement).all()]


async def get_profiles_by_usernames(
    collection: Any, usernames: list[str]
) -> list[Document]:
    session = collection
    assert isinstance(session, Session)
    if not usernames:
        return []
    username_column = cast(Any, IgProfile.username)
    statement = select(IgProfile).where(username_column.in_(usernames))
    return [_serialize_profile(record) for record in session.exec(statement).all()]


async def get_existing_profile_usernames(
    collection: Any, usernames: list[str]
) -> list[str]:
    session = collection
    assert isinstance(session, Session)
    if not usernames:
        return []
    username_column = cast(Any, IgProfile.username)
    statement = select(IgProfile.username).where(username_column.in_(usernames))
    return list(session.exec(statement).all())


async def update_profile(
    collection: Any, profile_id: str, patch: UpdateProfile
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_profile_id(profile_id)
    if parsed_id is None:
        return None

    record = session.get(IgProfile, parsed_id)
    if record is None:
        return None

    updates = patch.model_dump(exclude_unset=True, mode="json")
    if "ig_id" in updates and updates["ig_id"] is not None:
        record.ig_id = updates["ig_id"]
    if "username" in updates and updates["username"] is not None:
        record.username = updates["username"]
    if "full_name" in updates and updates["full_name"] is not None:
        record.full_name = updates["full_name"]
    if "biography" in updates and updates["biography"] is not None:
        record.biography = updates["biography"]
    if "is_private" in updates and updates["is_private"] is not None:
        record.is_private = updates["is_private"]
    if "is_verified" in updates and updates["is_verified"] is not None:
        record.is_verified = updates["is_verified"]
    if "profile_pic_url" in updates and updates["profile_pic_url"] is not None:
        record.profile_pic_url = updates["profile_pic_url"]
    if "external_url" in updates:
        record.external_url = updates["external_url"]
    if "updated_date" in updates and updates["updated_date"] is not None:
        record.updated_at = updates["updated_date"]
    else:
        record.updated_at = _utcnow()
    if "follower_count" in updates and updates["follower_count"] is not None:
        record.follower_count = updates["follower_count"]
    if "following_count" in updates and updates["following_count"] is not None:
        record.following_count = updates["following_count"]
    if "media_count" in updates and updates["media_count"] is not None:
        record.media_count = updates["media_count"]
    if "bio_links" in updates and updates["bio_links"] is not None:
        record.bio_links = updates["bio_links"]
    if "ai_categories" in updates and updates["ai_categories"] is not None:
        record.ai_categories = updates["ai_categories"]
    if "ai_roles" in updates and updates["ai_roles"] is not None:
        record.ai_roles = updates["ai_roles"]

    session.add(record)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_duplicate_profile(exc)
    session.refresh(record)
    return _serialize_profile(record)


async def replace_profile(
    collection: Any, profile_id: str, profile: Profile
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_profile_id(profile_id)
    if parsed_id is None:
        return None

    record = session.get(IgProfile, parsed_id)
    if record is None:
        return None

    record.ig_id = profile.ig_id
    record.username = profile.username
    record.full_name = profile.full_name
    record.biography = profile.biography
    record.is_private = profile.is_private
    record.is_verified = profile.is_verified
    record.profile_pic_url = str(profile.profile_pic_url)
    record.external_url = str(profile.external_url) if profile.external_url else None
    record.updated_at = profile.updated_date or _utcnow()
    record.follower_count = profile.follower_count
    record.following_count = profile.following_count
    record.media_count = profile.media_count
    record.bio_links = [
        item.model_dump(mode="json") for item in profile.bio_links or []
    ]
    record.ai_categories = profile.ai_categories or []
    record.ai_roles = profile.ai_roles or []

    session.add(record)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_duplicate_profile(exc)
    session.refresh(record)
    return _serialize_profile(record)


async def delete_profile(collection: Any, profile_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_profile_id(profile_id)
    if parsed_id is None:
        return None

    record = session.get(IgProfile, parsed_id)
    if record is None:
        return None

    document = _serialize_profile(record)
    session.delete(record)
    session.commit()
    return document
