import uuid
from typing import Any, cast

from sqlmodel import Session, select

from app.models import IgPostsDocument
from app.schemas import Post, UpdatePost

Document = dict[str, Any]


def _parse_post_id(post_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(post_id)
    except ValueError:
        return None


def _serialize_post(record: IgPostsDocument) -> Document:
    return {
        "_id": str(record.id),
        "profile_id": str(record.profile_id),
        "posts": record.items,
        "updated_at": record.updated_at,
    }


async def create_post(collection: Any, post: Post) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    record = IgPostsDocument(
        profile_id=uuid.UUID(post.profile_id),
        items=[item.model_dump(mode="json") for item in post.posts],
        updated_at=post.updated_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_post(record)


async def get_post(collection: Any, post_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_post_id(post_id)
    if parsed_id is None:
        return None
    record = session.get(IgPostsDocument, parsed_id)
    return _serialize_post(record) if record else None


async def list_posts(
    collection: Any, skip: int = 0, limit: int = 100
) -> list[Document]:
    session = collection
    assert isinstance(session, Session)
    updated_at = cast(Any, IgPostsDocument.updated_at)
    statement = (
        select(IgPostsDocument).order_by(updated_at.desc()).offset(skip).limit(limit)
    )
    return [_serialize_post(record) for record in session.exec(statement).all()]


async def update_post(
    collection: Any, post_id: str, patch: UpdatePost
) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_post_id(post_id)
    if parsed_id is None:
        return None
    record = session.get(IgPostsDocument, parsed_id)
    if record is None:
        return None

    updates = patch.model_dump(exclude_unset=True, mode="json")
    if "posts" in updates and updates["posts"] is not None:
        record.items = updates["posts"]
    if "updated_at" in updates and updates["updated_at"] is not None:
        record.updated_at = updates["updated_at"]

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_post(record)


async def replace_post(collection: Any, post_id: str, post: Post) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_post_id(post_id)
    if parsed_id is None:
        return None
    record = session.get(IgPostsDocument, parsed_id)
    if record is None:
        return None

    record.profile_id = uuid.UUID(post.profile_id)
    record.items = [item.model_dump(mode="json") for item in post.posts]
    record.updated_at = post.updated_at

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_post(record)


async def delete_post(collection: Any, post_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_post_id(post_id)
    if parsed_id is None:
        return None
    record = session.get(IgPostsDocument, parsed_id)
    if record is None:
        return None

    document = _serialize_post(record)
    session.delete(record)
    session.commit()
    return document
