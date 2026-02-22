import asyncio
from typing import Any

from app.crud.profile_snapshots import list_profile_snapshots_full


class _FakeCursor:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents
        self._index = 0

    def __aiter__(self) -> "_FakeCursor":
        self._index = 0
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._documents):
            raise StopAsyncIteration
        value = self._documents[self._index]
        self._index += 1
        return value


class _FakeCollection:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents
        self.pipeline: list[dict[str, Any]] | None = None

    async def aggregate(self, pipeline: list[dict[str, Any]]) -> _FakeCursor:
        self.pipeline = pipeline
        return _FakeCursor(self._documents)


def test_list_profile_snapshots_full_handles_async_aggregate() -> None:
    collection = _FakeCollection(
        documents=[{"_id": "snapshot-1", "profile": {"username": "creator_1"}}]
    )

    result = asyncio.run(
        list_profile_snapshots_full(
            collection=collection,
            skip=0,
            limit=10,
            usernames=["creator_1"],
        )
    )

    assert len(result) == 1
    assert result[0]["profile"]["username"] == "creator_1"
    assert collection.pipeline is not None
