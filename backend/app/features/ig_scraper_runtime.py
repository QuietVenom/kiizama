from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kiizama_scrape_core.ig_scraper.analysis import (
    OpenAIInstagramProfileAnalysisService,
)
from kiizama_scrape_core.ig_scraper.persistence import (
    SqlInstagramCredentialsStore,
    SqlInstagramScrapePersistence,
)
from kiizama_scrape_core.ig_scraper.types.session_validator import (
    configure_credentials_store_resolver,
)
from sqlmodel import Session

from app.core.db import engine


class BackendInstagramCredentialsStore(SqlInstagramCredentialsStore):
    def __init__(
        self,
        session_provider: Callable[[], Session],
    ) -> None:
        super().__init__(session_provider=session_provider)


class BackendInstagramProfileAnalysisService(OpenAIInstagramProfileAnalysisService):
    pass


class BackendInstagramScrapePersistence(SqlInstagramScrapePersistence):
    def __init__(
        self,
        *,
        profiles_collection: Any,
        posts_collection: Any,
        reels_collection: Any,
        metrics_collection: Any,
        snapshots_collection: Any,
    ) -> None:
        session = profiles_collection
        if not isinstance(session, Session):
            raise TypeError(
                "BackendInstagramScrapePersistence expects a SQLModel Session."
            )
        for dependency in (
            posts_collection,
            reels_collection,
            metrics_collection,
            snapshots_collection,
        ):
            if dependency is not session:
                raise ValueError(
                    "BackendInstagramScrapePersistence requires the same Session "
                    "instance for all Instagram repositories."
                )
        super().__init__(session=session)


def configure_backend_instagram_scraper_runtime() -> None:
    configure_credentials_store_resolver(
        lambda: BackendInstagramCredentialsStore(lambda: Session(engine))
    )


__all__ = [
    "BackendInstagramCredentialsStore",
    "BackendInstagramProfileAnalysisService",
    "BackendInstagramScrapePersistence",
    "configure_backend_instagram_scraper_runtime",
]
