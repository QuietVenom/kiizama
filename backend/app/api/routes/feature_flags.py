import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import crud_admin
from app.api.deps import RequestPrincipal, SessionDep, require_superuser_or_admin_roles
from app.constants import READ_ADMIN_ROLES, WRITE_ADMIN_ROLES
from app.models import (
    FeatureFlag,
    FeatureFlagAuditPublic,
    FeatureFlagAuditsPublic,
    FeatureFlagCreate,
    FeatureFlagPublic,
    FeatureFlagsPublic,
    FeatureFlagUpdate,
    Message,
)

router = APIRouter(prefix="/internal/feature-flags", tags=["feature-flags"])


def _to_feature_flag_public(feature_flag: FeatureFlag) -> FeatureFlagPublic:
    return FeatureFlagPublic.model_validate(feature_flag, from_attributes=True)


def _actor_from_principal(
    principal: RequestPrincipal,
) -> tuple[uuid.UUID | None, uuid.UUID | None, str | None]:
    if principal.principal_type == "admin" and principal.admin_user:
        return None, principal.admin_user.id, principal.admin_user.email
    if principal.user:
        return principal.user.id, None, principal.user.email
    return None, None, None


@router.get("/", response_model=FeatureFlagsPublic)
def list_feature_flags(
    session: SessionDep,
    _: Annotated[
        RequestPrincipal, Depends(require_superuser_or_admin_roles(READ_ADMIN_ROLES))
    ],
) -> FeatureFlagsPublic:
    feature_flags = crud_admin.list_feature_flags(session=session)
    feature_flags_public = [_to_feature_flag_public(item) for item in feature_flags]
    return FeatureFlagsPublic(
        data=feature_flags_public, count=len(feature_flags_public)
    )


@router.get("/{flag_key}", response_model=FeatureFlagPublic)
def get_feature_flag(
    flag_key: str,
    session: SessionDep,
    _: Annotated[
        RequestPrincipal, Depends(require_superuser_or_admin_roles(READ_ADMIN_ROLES))
    ],
) -> FeatureFlagPublic:
    feature_flag = crud_admin.get_feature_flag_by_key(session=session, key=flag_key)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    return _to_feature_flag_public(feature_flag)


@router.post("/", response_model=FeatureFlagPublic)
def create_feature_flag(
    *,
    session: SessionDep,
    feature_flag_in: FeatureFlagCreate,
    principal: Annotated[
        RequestPrincipal, Depends(require_superuser_or_admin_roles(WRITE_ADMIN_ROLES))
    ],
) -> FeatureFlagPublic:
    existing_feature_flag = crud_admin.get_feature_flag_by_key(
        session=session, key=feature_flag_in.key
    )
    if existing_feature_flag:
        raise HTTPException(
            status_code=409, detail="Feature flag with this key already exists"
        )

    feature_flag = crud_admin.create_feature_flag(
        session=session, feature_flag_in=feature_flag_in
    )
    changed_by_user_id, changed_by_admin_id, changed_by_email = _actor_from_principal(
        principal
    )
    crud_admin.create_feature_flag_audit(
        session=session,
        feature_flag=feature_flag,
        feature_flag_key=feature_flag.key,
        action="created",
        old_is_enabled=None,
        new_is_enabled=feature_flag.is_enabled,
        old_is_public=None,
        new_is_public=feature_flag.is_public,
        changed_by_user_id=changed_by_user_id,
        changed_by_admin_id=changed_by_admin_id,
        changed_by_email=changed_by_email,
    )
    return _to_feature_flag_public(feature_flag)


@router.patch("/{flag_key}", response_model=FeatureFlagPublic)
def update_feature_flag(
    *,
    session: SessionDep,
    flag_key: str,
    feature_flag_in: FeatureFlagUpdate,
    principal: Annotated[
        RequestPrincipal, Depends(require_superuser_or_admin_roles(WRITE_ADMIN_ROLES))
    ],
) -> FeatureFlagPublic:
    feature_flag = crud_admin.get_feature_flag_by_key(session=session, key=flag_key)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    old_is_enabled = feature_flag.is_enabled
    old_is_public = feature_flag.is_public
    feature_flag = crud_admin.update_feature_flag(
        session=session, db_feature_flag=feature_flag, feature_flag_in=feature_flag_in
    )

    changed_by_user_id, changed_by_admin_id, changed_by_email = _actor_from_principal(
        principal
    )
    crud_admin.create_feature_flag_audit(
        session=session,
        feature_flag=feature_flag,
        feature_flag_key=feature_flag.key,
        action="updated",
        old_is_enabled=old_is_enabled,
        new_is_enabled=feature_flag.is_enabled,
        old_is_public=old_is_public,
        new_is_public=feature_flag.is_public,
        changed_by_user_id=changed_by_user_id,
        changed_by_admin_id=changed_by_admin_id,
        changed_by_email=changed_by_email,
    )
    return _to_feature_flag_public(feature_flag)


@router.delete("/{flag_key}", response_model=Message)
def delete_feature_flag(
    *,
    session: SessionDep,
    flag_key: str,
    principal: Annotated[
        RequestPrincipal, Depends(require_superuser_or_admin_roles(WRITE_ADMIN_ROLES))
    ],
) -> Message:
    feature_flag = crud_admin.get_feature_flag_by_key(session=session, key=flag_key)
    if not feature_flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    old_is_enabled = feature_flag.is_enabled
    old_is_public = feature_flag.is_public
    crud_admin.delete_feature_flag(session=session, db_feature_flag=feature_flag)

    changed_by_user_id, changed_by_admin_id, changed_by_email = _actor_from_principal(
        principal
    )
    crud_admin.create_feature_flag_audit(
        session=session,
        feature_flag=None,
        feature_flag_key=flag_key,
        action="deleted",
        old_is_enabled=old_is_enabled,
        new_is_enabled=None,
        old_is_public=old_is_public,
        new_is_public=None,
        changed_by_user_id=changed_by_user_id,
        changed_by_admin_id=changed_by_admin_id,
        changed_by_email=changed_by_email,
    )

    return Message(message="Feature flag deleted successfully")


@router.get("/{flag_key}/audit", response_model=FeatureFlagAuditsPublic)
def get_feature_flag_audit(
    flag_key: str,
    session: SessionDep,
    _: Annotated[
        RequestPrincipal, Depends(require_superuser_or_admin_roles(READ_ADMIN_ROLES))
    ],
) -> FeatureFlagAuditsPublic:
    audit_entries = crud_admin.list_feature_flag_audits(
        session=session, feature_flag_key=flag_key
    )
    audits_public = [
        FeatureFlagAuditPublic.model_validate(item, from_attributes=True)
        for item in audit_entries
    ]
    return FeatureFlagAuditsPublic(data=audits_public, count=len(audits_public))
