from __future__ import annotations

from typing import Any, Protocol

from .classes import CredentialCandidate
from .schemas import InstagramBatchScrapeResponse


class InstagramCredentialsStore(Protocol):
    async def list_credentials(self, *, limit: int) -> list[CredentialCandidate]: ...

    def decrypt_password(self, encrypted_password: str) -> str: ...

    async def persist_session(
        self, credential_id: str, state: dict[str, Any]
    ) -> bool: ...


class InstagramScrapePersistence(Protocol):
    async def get_profiles_by_usernames(
        self, usernames: list[str]
    ) -> list[dict[str, Any]]: ...

    async def persist_scrape_results(
        self, response: InstagramBatchScrapeResponse
    ) -> InstagramBatchScrapeResponse: ...


class InstagramProfileAnalysisService(Protocol):
    async def enrich_scrape_response(
        self, response: InstagramBatchScrapeResponse
    ) -> InstagramBatchScrapeResponse: ...


__all__ = [
    "InstagramCredentialsStore",
    "InstagramProfileAnalysisService",
    "InstagramScrapePersistence",
]
