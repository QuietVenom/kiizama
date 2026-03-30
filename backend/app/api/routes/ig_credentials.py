from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, get_current_active_superuser
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

Document = dict[str, Any]


def _require_credential(credential_doc: Document | None) -> IgCredentialPublic:
    if not credential_doc:
        raise HTTPException(status_code=404, detail="Credential not found")
    return IgCredentialPublic.model_validate(credential_doc)


@router.post(
    "/", response_model=IgCredentialPublic, status_code=status.HTTP_201_CREATED
)
def create_ig_credential_endpoint(
    credential: IgCredential,
    session: SessionDep,
) -> IgCredentialPublic:
    created = create_ig_credential(session, credential)
    return _require_credential(created)


@router.get("/", response_model=IgCredentialPublicCollection)
def read_ig_credentials(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> IgCredentialPublicCollection:
    credentials = list_ig_credentials(session, skip=skip, limit=limit)
    return IgCredentialPublicCollection(
        ig_credentials=[
            IgCredentialPublic.model_validate(credential) for credential in credentials
        ]
    )


@router.get("/{credential_id}", response_model=IgCredentialPublic)
def read_ig_credential(
    credential_id: str,
    session: SessionDep,
) -> IgCredentialPublic:
    return _require_credential(get_ig_credential(session, credential_id))


@router.patch("/{credential_id}", response_model=IgCredentialPublic)
def update_ig_credential_endpoint(
    credential_id: str,
    patch: UpdateIgCredential,
    session: SessionDep,
) -> IgCredentialPublic:
    return _require_credential(update_ig_credential(session, credential_id, patch))


@router.put("/{credential_id}", response_model=IgCredentialPublic)
def replace_ig_credential_endpoint(
    credential_id: str,
    credential_in: IgCredential,
    session: SessionDep,
) -> IgCredentialPublic:
    return _require_credential(
        replace_ig_credential(session, credential_id, credential_in)
    )


@router.delete("/{credential_id}", response_model=IgCredentialPublic)
def delete_ig_credential_endpoint(
    credential_id: str,
    session: SessionDep,
) -> IgCredentialPublic:
    return _require_credential(delete_ig_credential(session, credential_id))


__all__ = ["router"]
