from typing import Any, cast

from bson import ObjectId
from pymongo import ReturnDocument

from app.schemas import Metrics, UpdateMetrics

Document = dict[str, Any]


async def create_metrics(collection: Any, metrics: Metrics) -> Document | None:
    doc = metrics.model_dump(by_alias=True, exclude_none=True)
    result = await collection.insert_one(doc)
    return cast(Document | None, await collection.find_one({"_id": result.inserted_id}))


async def get_metrics(collection: Any, metrics_id: str) -> Document | None:
    return cast(
        Document | None, await collection.find_one({"_id": ObjectId(metrics_id)})
    )


async def list_metrics(
    collection: Any, skip: int = 0, limit: int = 100
) -> list[Document]:
    cursor = collection.find().skip(skip).limit(limit)
    return [cast(Document, doc) async for doc in cursor]


async def update_metrics(
    collection: Any, metrics_id: str, patch: UpdateMetrics
) -> Document | None:
    updates = patch.model_dump(exclude_unset=True)
    if not updates:
        return cast(
            Document | None, await collection.find_one({"_id": ObjectId(metrics_id)})
        )

    return cast(
        Document | None,
        await collection.find_one_and_update(
            {"_id": ObjectId(metrics_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        ),
    )


async def replace_metrics(
    collection: Any, metrics_id: str, metrics: Metrics
) -> Document | None:
    doc = metrics.model_dump(by_alias=True, exclude_none=False)
    doc["_id"] = ObjectId(metrics_id)
    return cast(
        Document | None,
        await collection.find_one_and_replace(
            {"_id": ObjectId(metrics_id)},
            doc,
            return_document=ReturnDocument.AFTER,
        ),
    )


async def delete_metrics(collection: Any, metrics_id: str) -> Document | None:
    return cast(
        Document | None,
        await collection.find_one_and_delete({"_id": ObjectId(metrics_id)}),
    )
