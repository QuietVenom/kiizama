from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kiizama_scrape_core.ig_scraper_v2 import (
    OpenAIInstagramProfileAnalysisServiceV2,
    SqlInstagramCredentialsStoreV2,
    SqlInstagramScrapePersistenceV2,
)
from sqlmodel import Session


class BackendInstagramCredentialsStoreV2(SqlInstagramCredentialsStoreV2):
    def __init__(
        self,
        session_provider: Callable[[], Session],
    ) -> None:
        super().__init__(session_provider=session_provider)


class BackendInstagramProfileAnalysisServiceV2(OpenAIInstagramProfileAnalysisServiceV2):
    pass


class BackendInstagramScrapePersistenceV2(SqlInstagramScrapePersistenceV2):
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
                "BackendInstagramScrapePersistenceV2 expects a SQLModel Session."
            )
        for dependency in (
            posts_collection,
            reels_collection,
            metrics_collection,
            snapshots_collection,
        ):
            if dependency is not session:
                raise ValueError(
                    "BackendInstagramScrapePersistenceV2 requires the same Session "
                    "instance for all Instagram repositories."
                )
        super().__init__(session=session)


__all__ = [
    "BackendInstagramCredentialsStoreV2",
    "BackendInstagramProfileAnalysisServiceV2",
    "BackendInstagramScrapePersistenceV2",
]
