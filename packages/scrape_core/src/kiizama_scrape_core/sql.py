from __future__ import annotations

from typing import overload

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine, select


def normalize_postgres_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = f"postgresql://{url[len('postgres://') :]}"
    if url.startswith("postgresql://"):
        url = f"postgresql+psycopg://{url[len('postgresql://') :]}"
    return url


def create_sqlmodel_engine(database_url: str) -> Engine:
    return create_engine(normalize_postgres_url(database_url), pool_pre_ping=True)


@overload
def ping_postgres(engine_or_url: Engine) -> None: ...


@overload
def ping_postgres(engine_or_url: str) -> None: ...


def ping_postgres(engine_or_url: Engine | str) -> None:
    engine = (
        engine_or_url
        if isinstance(engine_or_url, Engine)
        else create_sqlmodel_engine(engine_or_url)
    )
    with Session(engine) as session:
        session.exec(select(1))


__all__ = ["create_sqlmodel_engine", "normalize_postgres_url", "ping_postgres"]
