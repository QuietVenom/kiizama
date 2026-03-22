import asyncio
from datetime import datetime, timezone
from typing import Any

from app.features.creators_search_history.repository import (
    CreatorsSearchHistoryRepository,
)
from app.features.creators_search_history.schemas import (
    CreatorsSearchHistoryCreateRequest,
    CreatorsSearchHistoryItem,
)
from app.features.creators_search_history.service import CreatorsSearchHistoryService


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeCreatorsSearchHistoryRepository(CreatorsSearchHistoryRepository):
    def __init__(self) -> None:
        self.items: list[CreatorsSearchHistoryItem] = []
        self.append_calls: list[CreatorsSearchHistoryItem] = []
        self.job_append_calls: list[CreatorsSearchHistoryItem] = []

    async def list_items(
        self,
        *,
        user_id: str,
        limit: int,
    ) -> list[CreatorsSearchHistoryItem]:
        del user_id
        return self.items[:limit]

    async def append_item(
        self,
        *,
        user_id: str,
        item: CreatorsSearchHistoryItem,
    ) -> None:
        del user_id
        self.append_calls.append(item)
        self.items.insert(0, item)

    async def append_item_if_job_absent(
        self,
        *,
        user_id: str,
        item: CreatorsSearchHistoryItem,
    ) -> CreatorsSearchHistoryItem:
        del user_id
        self.job_append_calls.append(item)
        existing_item = next(
            (existing for existing in self.items if existing.job_id == item.job_id),
            None,
        )
        if existing_item is not None:
            return existing_item
        self.items.insert(0, item)
        return item


def test_create_entry_reuses_existing_job_history_item() -> None:
    repository = FakeCreatorsSearchHistoryRepository()
    existing_item = CreatorsSearchHistoryItem(
        id="history-1",
        created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
        source="ig-scrape-job",
        job_id="job-1",
        ready_usernames=["creator_one"],
    )
    repository.items = [existing_item]
    service = CreatorsSearchHistoryService(repository=repository)

    item = _run(
        service.create_entry(
            user_id="user-1",
            payload=CreatorsSearchHistoryCreateRequest(
                source="ig-scrape-job",
                job_id="job-1",
                ready_usernames=["creator_one"],
            ),
        )
    )

    assert item == existing_item
    assert repository.append_calls == []
    assert len(repository.job_append_calls) == 1


def test_create_entry_allows_direct_search_duplicates() -> None:
    repository = FakeCreatorsSearchHistoryRepository()
    service = CreatorsSearchHistoryService(
        repository=repository,
        clock=lambda: datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    )

    first_item = _run(
        service.create_entry(
            user_id="user-1",
            payload=CreatorsSearchHistoryCreateRequest(
                source="direct-search",
                ready_usernames=["creator_one"],
            ),
        )
    )
    second_item = _run(
        service.create_entry(
            user_id="user-1",
            payload=CreatorsSearchHistoryCreateRequest(
                source="direct-search",
                ready_usernames=["creator_one"],
            ),
        )
    )

    assert first_item.id != second_item.id
    assert len(repository.append_calls) == 2
    assert repository.job_append_calls == []
