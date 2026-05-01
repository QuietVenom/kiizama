import uuid
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.ig_credentials_crypto import (
    decrypt_ig_session,
    encrypt_ig_password,
    encrypt_ig_session,
)
from app.models import IgCredential as IgCredentialRecord
from app.schemas import IgCredential, UpdateIgCredential

Document = dict[str, Any]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_credential_id(credential_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(credential_id)
    except ValueError:
        return None


def _serialize_credential(record: IgCredentialRecord) -> Document:
    try:
        session = decrypt_ig_session(record.session_encrypted)
    except ValueError:
        session = None

    return {
        "_id": str(record.id),
        "login_username": record.login_username,
        "password": record.password_encrypted,
        "session": session,
    }


def _raise_duplicate_login_username(exc: IntegrityError) -> None:
    raise HTTPException(status_code=409, detail="login_username ya existe") from exc


def create_ig_credential(session: Session, credential: IgCredential) -> Document:
    record = IgCredentialRecord(
        login_username=credential.login_username,
        password_encrypted=encrypt_ig_password(credential.password),
        session_encrypted=encrypt_ig_session(credential.session),
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_duplicate_login_username(exc)
    session.refresh(record)
    return _serialize_credential(record)


def get_ig_credential(session: Session, credential_id: str) -> Document | None:
    parsed_id = _parse_credential_id(credential_id)
    if parsed_id is None:
        return None

    record = session.get(IgCredentialRecord, parsed_id)
    if record is None:
        return None
    return _serialize_credential(record)


def list_ig_credentials(
    session: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[Document]:
    statement = (
        select(IgCredentialRecord)
        .order_by(cast(Any, IgCredentialRecord).created_at)
        .offset(skip)
        .limit(limit)
    )
    records = session.exec(statement).all()
    return [_serialize_credential(record) for record in records]


def update_ig_credential(
    session: Session,
    credential_id: str,
    patch: UpdateIgCredential,
) -> Document | None:
    parsed_id = _parse_credential_id(credential_id)
    if parsed_id is None:
        return None

    record = session.get(IgCredentialRecord, parsed_id)
    if record is None:
        return None

    updates = patch.model_dump(exclude_unset=True, mode="json")
    if not updates:
        return _serialize_credential(record)

    if "login_username" in updates and updates["login_username"] is not None:
        record.login_username = updates["login_username"]
    if "password" in updates and updates["password"] is not None:
        record.password_encrypted = encrypt_ig_password(updates["password"])
    if "session" in updates:
        record.session_encrypted = encrypt_ig_session(updates["session"])

    record.updated_at = _utcnow()
    session.add(record)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_duplicate_login_username(exc)
    session.refresh(record)
    return _serialize_credential(record)


def update_ig_credential_session(
    session: Session,
    credential_id: str,
    credential_session: dict[str, Any] | None,
) -> Document | None:
    parsed_id = _parse_credential_id(credential_id)
    if parsed_id is None:
        return None

    record = session.get(IgCredentialRecord, parsed_id)
    if record is None:
        return None

    record.session_encrypted = encrypt_ig_session(credential_session)
    record.updated_at = _utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_credential(record)


def replace_ig_credential(
    session: Session,
    credential_id: str,
    credential: IgCredential,
) -> Document | None:
    parsed_id = _parse_credential_id(credential_id)
    if parsed_id is None:
        return None

    record = session.get(IgCredentialRecord, parsed_id)
    if record is None:
        return None

    record.login_username = credential.login_username
    record.password_encrypted = encrypt_ig_password(credential.password)
    record.session_encrypted = encrypt_ig_session(credential.session)
    record.updated_at = _utcnow()

    session.add(record)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_duplicate_login_username(exc)
    session.refresh(record)
    return _serialize_credential(record)


def delete_ig_credential(session: Session, credential_id: str) -> Document | None:
    parsed_id = _parse_credential_id(credential_id)
    if parsed_id is None:
        return None

    record = session.get(IgCredentialRecord, parsed_id)
    if record is None:
        return None

    document = _serialize_credential(record)
    session.delete(record)
    session.commit()
    return document
