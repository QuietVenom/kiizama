from datetime import UTC, datetime
from typing import Any

import pytest

from app.features.creators_search_history.repository import (
    CREATORS_SEARCH_HISTORY_TTL_SECONDS,
    JOB_HISTORY_INDEX_TTL_SECONDS,
    MAX_CREATORS_SEARCH_HISTORY_ITEMS,
    CreatorsSearchHistoryRepository,
    build_creators_search_history_job_key,
    build_creators_search_history_key,
)
from app.features.creators_search_history.schemas import CreatorsSearchHistoryItem


def _repository(redis: Any) -> CreatorsSearchHistoryRepository:
    return CreatorsSearchHistoryRepository(redis_provider=lambda: redis)


def _item(index: int, *, job_id: str | None = None) -> CreatorsSearchHistoryItem:
    return CreatorsSearchHistoryItem(
        id=f"item-{index}",
        created_at=datetime(2026, 3, 23, 12, index % 60, tzinfo=UTC),
        source="ig-scrape-job" if job_id else "direct-search",
        job_id=job_id,
        ready_usernames=[f"creator_{index}"],
    )


@pytest.mark.anyio
async def test_append_item_keeps_newest_first_and_trims_to_max_items(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)

    for index in range(MAX_CREATORS_SEARCH_HISTORY_ITEMS + 5):
        await repository.append_item(user_id="user-1", item=_item(index))

    items = await repository.list_items(user_id="user-1", limit=20)

    assert len(items) == MAX_CREATORS_SEARCH_HISTORY_ITEMS
    assert items[0].id == f"item-{MAX_CREATORS_SEARCH_HISTORY_ITEMS + 4}"
    assert items[-1].id == "item-5"
    assert await redis_client.ttl(build_creators_search_history_key("user-1")) == (
        CREATORS_SEARCH_HISTORY_TTL_SECONDS
    )


@pytest.mark.anyio
async def test_list_items_ignores_corrupted_json_entries(redis_client: Any) -> None:
    repository = _repository(redis_client)
    key = build_creators_search_history_key("user-1")

    await redis_client.lpush(key, "{not-json")
    await redis_client.lpush(key, _item(1).model_dump_json())

    items = await repository.list_items(user_id="user-1", limit=20)

    assert [item.id for item in items] == ["item-1"]


@pytest.mark.anyio
async def test_list_items_reads_past_corrupted_top_entries_until_limit(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    key = build_creators_search_history_key("user-1")

    for index in range(6):
        await redis_client.lpush(key, _item(index).model_dump_json())
    await redis_client.lpush(key, "{also-not-json")
    await redis_client.lpush(key, "{not-json")

    items = await repository.list_items(user_id="user-1", limit=5)

    assert [item.id for item in items] == [
        "item-5",
        "item-4",
        "item-3",
        "item-2",
        "item-1",
    ]


@pytest.mark.anyio
async def test_append_item_if_job_absent_is_idempotent_and_sets_ttl(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    item = _item(1, job_id="job-1")

    first_item = await repository.append_item_if_job_absent(user_id="user-1", item=item)
    second_item = await repository.append_item_if_job_absent(
        user_id="user-1",
        item=_item(2, job_id="job-1"),
    )

    items = await repository.list_items(user_id="user-1", limit=20)
    job_key = build_creators_search_history_job_key("user-1", "job-1")
    list_key = build_creators_search_history_key("user-1")

    assert first_item == item
    assert second_item == item
    assert [history_item.id for history_item in items] == ["item-1"]
    assert await redis_client.ttl(job_key) == JOB_HISTORY_INDEX_TTL_SECONDS
    assert await redis_client.ttl(list_key) == CREATORS_SEARCH_HISTORY_TTL_SECONDS


@pytest.mark.anyio
async def test_append_item_if_job_absent_repairs_corrupted_job_index(
    redis_client: Any,
) -> None:
    repository = _repository(redis_client)
    job_key = build_creators_search_history_job_key("user-1", "job-1")
    list_key = build_creators_search_history_key("user-1")
    existing_item = _item(1, job_id="job-1")
    new_item = _item(2, job_id="job-1")

    await redis_client.lpush(list_key, existing_item.model_dump_json())
    await redis_client.set(job_key, "{broken-json", ex=JOB_HISTORY_INDEX_TTL_SECONDS)

    repaired_item = await repository.append_item_if_job_absent(
        user_id="user-1", item=new_item
    )

    items = await repository.list_items(user_id="user-1", limit=20)
    assert repaired_item == existing_item
    assert [history_item.id for history_item in items] == ["item-1"]
    assert await redis_client.get(job_key) == existing_item.model_dump_json()
    assert await redis_client.ttl(list_key) == -1
