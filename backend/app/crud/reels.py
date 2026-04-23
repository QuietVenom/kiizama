import uuid
from typing import Any, cast

from sqlmodel import Session, select

from app.models import IgReelsDocument
from app.schemas import Reel, UpdateReel

Document = dict[str, Any]


def _parse_reel_id(reel_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(reel_id)
    except ValueError:
        return None


def _serialize_reel(record: IgReelsDocument) -> Document:
    return {
        "_id": str(record.id),
        "profile_id": str(record.profile_id),
        "reels": record.items,
        "updated_at": record.updated_at,
    }


def create_reel(collection: Any, reel: Reel) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    record = IgReelsDocument(
        profile_id=uuid.UUID(reel.profile_id),
        items=[item.model_dump(mode="json") for item in reel.reels],
        updated_at=reel.updated_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_reel(record)


def get_reel(collection: Any, reel_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_reel_id(reel_id)
    if parsed_id is None:
        return None
    record = session.get(IgReelsDocument, parsed_id)
    return _serialize_reel(record) if record else None


def list_reels(collection: Any, skip: int = 0, limit: int = 100) -> list[Document]:
    session = collection
    assert isinstance(session, Session)
    updated_at = cast(Any, IgReelsDocument.updated_at)
    statement = (
        select(IgReelsDocument).order_by(updated_at.desc()).offset(skip).limit(limit)
    )
    return [_serialize_reel(record) for record in session.exec(statement).all()]


def update_reel(collection: Any, reel_id: str, patch: UpdateReel) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_reel_id(reel_id)
    if parsed_id is None:
        return None
    record = session.get(IgReelsDocument, parsed_id)
    if record is None:
        return None

    updates = patch.model_dump(exclude_unset=True, mode="json")
    if "reels" in updates and updates["reels"] is not None:
        record.items = updates["reels"]
    if "updated_at" in updates and updates["updated_at"] is not None:
        record.updated_at = updates["updated_at"]

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_reel(record)


def replace_reel(collection: Any, reel_id: str, reel: Reel) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_reel_id(reel_id)
    if parsed_id is None:
        return None
    record = session.get(IgReelsDocument, parsed_id)
    if record is None:
        return None

    record.profile_id = uuid.UUID(reel.profile_id)
    record.items = [item.model_dump(mode="json") for item in reel.reels]
    record.updated_at = reel.updated_at

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_reel(record)


def delete_reel(collection: Any, reel_id: str) -> Document | None:
    session = collection
    assert isinstance(session, Session)
    parsed_id = _parse_reel_id(reel_id)
    if parsed_id is None:
        return None
    record = session.get(IgReelsDocument, parsed_id)
    if record is None:
        return None

    document = _serialize_reel(record)
    session.delete(record)
    session.commit()
    return document
