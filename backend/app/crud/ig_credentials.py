from typing import Any, cast

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.ig_credentials_crypto import encrypt_ig_password
from app.schemas import IgCredential, UpdateIgCredential

Document = dict[str, Any]


async def create_ig_credential(
    collection: Any, credential: IgCredential
) -> Document | None:
    doc = credential.model_dump(by_alias=True, exclude_none=True, mode="json")
    doc["password"] = encrypt_ig_password(doc["password"])
    try:
        result = await collection.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="login_username ya existe") from exc
    return cast(Document | None, await collection.find_one({"_id": result.inserted_id}))


async def get_ig_credential(collection: Any, credential_id: str) -> Document | None:
    return cast(
        Document | None, await collection.find_one({"_id": ObjectId(credential_id)})
    )


async def list_ig_credentials(
    collection: Any, skip: int = 0, limit: int = 100
) -> list[Document]:
    cursor = collection.find().skip(skip).limit(limit)
    return [cast(Document, doc) async for doc in cursor]


async def update_ig_credential(
    collection: Any, credential_id: str, patch: UpdateIgCredential
) -> Document | None:
    updates = patch.model_dump(exclude_unset=True, mode="json")
    if not updates:
        return cast(
            Document | None, await collection.find_one({"_id": ObjectId(credential_id)})
        )

    if "password" in updates and updates["password"] is not None:
        updates["password"] = encrypt_ig_password(updates["password"])

    try:
        return cast(
            Document | None,
            await collection.find_one_and_update(
                {"_id": ObjectId(credential_id)},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            ),
        )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="login_username ya existe") from exc


async def update_ig_credential_session(
    collection: Any, credential_id: str, session: dict[str, Any] | None
) -> Document | None:
    return cast(
        Document | None,
        await collection.find_one_and_update(
            {"_id": ObjectId(credential_id)},
            {"$set": {"session": session}},
            return_document=ReturnDocument.AFTER,
        ),
    )


async def replace_ig_credential(
    collection: Any, credential_id: str, credential: IgCredential
) -> Document | None:
    doc = credential.model_dump(by_alias=True, exclude_none=False, mode="json")
    doc["_id"] = ObjectId(credential_id)

    if doc.get("password") is not None:
        doc["password"] = encrypt_ig_password(doc["password"])

    try:
        return cast(
            Document | None,
            await collection.find_one_and_replace(
                {"_id": ObjectId(credential_id)},
                doc,
                return_document=ReturnDocument.AFTER,
            ),
        )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="login_username ya existe") from exc


async def delete_ig_credential(collection: Any, credential_id: str) -> Document | None:
    return cast(
        Document | None,
        await collection.find_one_and_delete({"_id": ObjectId(credential_id)}),
    )
