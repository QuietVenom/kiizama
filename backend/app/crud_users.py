from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.features.legal_documents import (
    PUBLIC_SIGNUP_LEGAL_ACCEPTANCE_SOURCE,
    PUBLIC_SIGNUP_LEGAL_DOCUMENTS,
)
from app.models import User, UserCreate, UserLegalAcceptance, UserUpdate


def _build_user_db_obj(*, user_create: UserCreate) -> User:
    return User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = _build_user_db_obj(user_create=user_create)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_signup_legal_acceptances(
    *, session: Session, user: User
) -> list[UserLegalAcceptance]:
    acceptances = [
        UserLegalAcceptance(
            user_id=user.id,
            document_type=document.type,
            document_version=document.version,
            source=PUBLIC_SIGNUP_LEGAL_ACCEPTANCE_SOURCE,
        )
        for document in PUBLIC_SIGNUP_LEGAL_DOCUMENTS
    ]
    for acceptance in acceptances:
        session.add(acceptance)
    return acceptances


def create_signup_user(*, session: Session, user_create: UserCreate) -> User:
    user = _build_user_db_obj(user_create=user_create)
    session.add(user)
    create_signup_legal_acceptances(session=session, user=user)
    session.commit()
    session.refresh(user)
    return user


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user
