from fastapi import APIRouter, HTTPException

from app import crud_admin
from app.api.deps import SessionDep
from app.models import FeatureFlagPublic, FeatureFlagsPublic

router = APIRouter(prefix="/public/feature-flags", tags=["public-feature-flags"])


@router.get("/", response_model=FeatureFlagsPublic)
def list_public_feature_flags(session: SessionDep) -> FeatureFlagsPublic:
    feature_flags = crud_admin.list_feature_flags(session=session, only_public=True)
    data = [
        FeatureFlagPublic.model_validate(feature_flag, from_attributes=True)
        for feature_flag in feature_flags
    ]
    return FeatureFlagsPublic(data=data, count=len(data))


@router.get("/{flag_key}", response_model=FeatureFlagPublic)
def get_public_feature_flag(flag_key: str, session: SessionDep) -> FeatureFlagPublic:
    feature_flag = crud_admin.get_feature_flag_by_key(session=session, key=flag_key)
    if not feature_flag or not feature_flag.is_public:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    return FeatureFlagPublic.model_validate(feature_flag, from_attributes=True)
