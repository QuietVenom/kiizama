from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends

from app.core.ids import generate_uuid7

from .repository import (
    CreatorsSearchHistoryRepository,
    CreatorsSearchHistoryUnavailableError,
    get_creators_search_history_repository,
)
from .schemas import (
    CreatorsSearchHistoryCreateRequest,
    CreatorsSearchHistoryItem,
    CreatorsSearchHistoryListResponse,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CreatorsSearchHistoryService:
    def __init__(
        self,
        *,
        repository: CreatorsSearchHistoryRepository | None = None,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._repository = repository or get_creators_search_history_repository()
        self._clock = clock

    async def list_history(
        self,
        *,
        user_id: str,
        limit: int,
    ) -> CreatorsSearchHistoryListResponse:
        items = await self._repository.list_items(user_id=user_id, limit=limit)
        return CreatorsSearchHistoryListResponse(items=items, count=len(items))

    async def create_entry(
        self,
        *,
        user_id: str,
        payload: CreatorsSearchHistoryCreateRequest,
    ) -> CreatorsSearchHistoryItem:
        item = CreatorsSearchHistoryItem(
            id=str(generate_uuid7()),
            created_at=self._clock(),
            source=payload.source,
            job_id=payload.job_id,
            ready_usernames=payload.ready_usernames,
        )
        if payload.source == "ig-scrape-job":
            return await self._repository.append_item_if_job_absent(
                user_id=user_id,
                item=item,
            )

        await self._repository.append_item(user_id=user_id, item=item)
        return item


def get_creators_search_history_service() -> CreatorsSearchHistoryService:
    return CreatorsSearchHistoryService()


CreatorsSearchHistoryServiceDep = Annotated[
    CreatorsSearchHistoryService,
    Depends(get_creators_search_history_service),
]


__all__ = [
    "CreatorsSearchHistoryService",
    "CreatorsSearchHistoryServiceDep",
    "CreatorsSearchHistoryUnavailableError",
    "get_creators_search_history_service",
]
