from __future__ import annotations

from collections.abc import Callable

from pydantic import ValidationError
from redis.exceptions import WatchError

from app.core.redis import RedisClient, get_redis_client

from .schemas import CreatorsSearchHistoryItem

MAX_CREATORS_SEARCH_HISTORY_ITEMS = 20
CREATORS_SEARCH_HISTORY_TTL_SECONDS = 20 * 24 * 60 * 60
JOB_HISTORY_INDEX_TTL_SECONDS = 15 * 24 * 60 * 60


class CreatorsSearchHistoryUnavailableError(RuntimeError):
    pass


def build_creators_search_history_key(user_id: str) -> str:
    return f"creators-search:history:user:{user_id}"


def build_creators_search_history_job_key(user_id: str, job_id: str) -> str:
    return f"{build_creators_search_history_key(user_id)}:job:{job_id}"


class CreatorsSearchHistoryRepository:
    def __init__(
        self,
        *,
        redis_provider: Callable[[], RedisClient] = get_redis_client,
    ) -> None:
        self._redis_provider = redis_provider

    def _get_redis(self) -> RedisClient:
        try:
            return self._redis_provider()
        except RuntimeError as exc:
            raise CreatorsSearchHistoryUnavailableError(str(exc)) from exc

    async def list_items(
        self,
        *,
        user_id: str,
        limit: int,
    ) -> list[CreatorsSearchHistoryItem]:
        redis = self._get_redis()
        raw_items = await redis.lrange(
            build_creators_search_history_key(user_id),
            0,
            MAX_CREATORS_SEARCH_HISTORY_ITEMS - 1,
        )

        items: list[CreatorsSearchHistoryItem] = []
        for raw_item in raw_items:
            try:
                items.append(CreatorsSearchHistoryItem.model_validate_json(raw_item))
            except ValidationError:
                continue
            if len(items) >= limit:
                break

        return items

    async def append_item(
        self,
        *,
        user_id: str,
        item: CreatorsSearchHistoryItem,
    ) -> None:
        redis = self._get_redis()
        key = build_creators_search_history_key(user_id)
        await redis.lpush(key, item.model_dump_json())
        await redis.ltrim(key, 0, MAX_CREATORS_SEARCH_HISTORY_ITEMS - 1)
        await redis.expire(key, CREATORS_SEARCH_HISTORY_TTL_SECONDS)

    async def append_item_if_job_absent(
        self,
        *,
        user_id: str,
        item: CreatorsSearchHistoryItem,
    ) -> CreatorsSearchHistoryItem:
        if item.job_id is None:
            raise ValueError("append_item_if_job_absent requires item.job_id.")

        redis = self._get_redis()
        list_key = build_creators_search_history_key(user_id)
        job_key = build_creators_search_history_job_key(user_id, item.job_id)
        item_json = item.model_dump_json()

        while True:
            corrupted_json: str | None = None
            async with redis.pipeline() as pipe:
                try:
                    await pipe.watch(job_key)
                    existing_json = await pipe.get(job_key)
                    if existing_json is None:
                        pipe.multi()
                        pipe.set(job_key, item_json, ex=JOB_HISTORY_INDEX_TTL_SECONDS)
                        pipe.lpush(list_key, item_json)
                        pipe.ltrim(list_key, 0, MAX_CREATORS_SEARCH_HISTORY_ITEMS - 1)
                        pipe.expire(
                            list_key,
                            CREATORS_SEARCH_HISTORY_TTL_SECONDS,
                        )
                        await pipe.execute()
                        return item

                    try:
                        return CreatorsSearchHistoryItem.model_validate_json(
                            existing_json
                        )
                    except ValidationError:
                        corrupted_json = existing_json
                except WatchError:
                    continue
            if corrupted_json is not None:
                return await self._repair_corrupted_job_index(
                    user_id=user_id,
                    item=item,
                    corrupted_json=corrupted_json,
                )

    async def _repair_corrupted_job_index(
        self,
        *,
        user_id: str,
        item: CreatorsSearchHistoryItem,
        corrupted_json: str,
    ) -> CreatorsSearchHistoryItem:
        if item.job_id is None:
            raise ValueError("_repair_corrupted_job_index requires item.job_id.")

        redis = self._get_redis()
        list_key = build_creators_search_history_key(user_id)
        job_key = build_creators_search_history_job_key(user_id, item.job_id)
        current_item = None
        items = await self.list_items(
            user_id=user_id,
            limit=MAX_CREATORS_SEARCH_HISTORY_ITEMS,
        )
        for candidate in items:
            if candidate.job_id == item.job_id:
                current_item = candidate
                break
        repaired_item = current_item or item
        repaired_json = repaired_item.model_dump_json()

        while True:
            async with redis.pipeline() as pipe:
                try:
                    await pipe.watch(job_key)
                    current_json = await pipe.get(job_key)
                    if current_json != corrupted_json:
                        if current_json is None:
                            continue
                        try:
                            return CreatorsSearchHistoryItem.model_validate_json(
                                current_json
                            )
                        except ValidationError:
                            corrupted_json = current_json
                            continue

                    pipe.multi()
                    pipe.set(job_key, repaired_json, ex=JOB_HISTORY_INDEX_TTL_SECONDS)
                    if current_item is None:
                        pipe.lpush(list_key, repaired_json)
                        pipe.ltrim(list_key, 0, MAX_CREATORS_SEARCH_HISTORY_ITEMS - 1)
                        pipe.expire(
                            list_key,
                            CREATORS_SEARCH_HISTORY_TTL_SECONDS,
                        )
                    await pipe.execute()
                    return repaired_item
                except WatchError:
                    continue


def get_creators_search_history_repository() -> CreatorsSearchHistoryRepository:
    return CreatorsSearchHistoryRepository()


__all__ = [
    "CreatorsSearchHistoryRepository",
    "CreatorsSearchHistoryUnavailableError",
    "CREATORS_SEARCH_HISTORY_TTL_SECONDS",
    "JOB_HISTORY_INDEX_TTL_SECONDS",
    "MAX_CREATORS_SEARCH_HISTORY_ITEMS",
    "build_creators_search_history_job_key",
    "build_creators_search_history_key",
    "get_creators_search_history_repository",
]
