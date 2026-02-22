from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_superuser, get_ig_credentials_collection
from app.crud.ig_credentials import (
    create_ig_credential,
    delete_ig_credential,
    get_ig_credential,
    list_ig_credentials,
    replace_ig_credential,
    update_ig_credential,
)
from app.schemas import (
    IgCredential,
    IgCredentialPublic,
    IgCredentialPublicCollection,
    UpdateIgCredential,
)

router = APIRouter(
    prefix="/ig-credentials",
    tags=["ig-credentials"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post(
    "/", response_model=IgCredentialPublic, status_code=status.HTTP_201_CREATED
)
async def create_ig_credential_endpoint(
    credential: IgCredential,
    collection: Any = Depends(get_ig_credentials_collection),
) -> IgCredentialPublic:
    return await create_ig_credential(collection, credential)


@router.get("/", response_model=IgCredentialPublicCollection)
async def read_ig_credentials(
    skip: int = 0,
    limit: int = 100,
    collection: Any = Depends(get_ig_credentials_collection),
) -> IgCredentialPublicCollection:
    credentials = await list_ig_credentials(collection, skip=skip, limit=limit)
    return IgCredentialPublicCollection(ig_credentials=credentials)


@router.get("/{credential_id}", response_model=IgCredentialPublic)
async def read_ig_credential(
    credential_id: str,
    collection: Any = Depends(get_ig_credentials_collection),
) -> IgCredentialPublic:
    credential = await get_ig_credential(collection, credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


@router.patch("/{credential_id}", response_model=IgCredentialPublic)
async def update_ig_credential_endpoint(
    credential_id: str,
    patch: UpdateIgCredential,
    collection: Any = Depends(get_ig_credentials_collection),
) -> IgCredentialPublic:
    credential = await update_ig_credential(collection, credential_id, patch)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


@router.put("/{credential_id}", response_model=IgCredentialPublic)
async def replace_ig_credential_endpoint(
    credential_id: str,
    credential_in: IgCredential,
    collection: Any = Depends(get_ig_credentials_collection),
) -> IgCredentialPublic:
    credential = await replace_ig_credential(collection, credential_id, credential_in)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


@router.delete("/{credential_id}", response_model=IgCredentialPublic)
async def delete_ig_credential_endpoint(
    credential_id: str,
    collection: Any = Depends(get_ig_credentials_collection),
) -> IgCredentialPublic:
    credential = await delete_ig_credential(collection, credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


__all__ = ["router"]
