from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app import crud_admin
from app.api.deps import CurrentAdminAuth, SessionDep
from app.core import security
from app.core.config import settings
from app.models import Token, UserAdminPublic

router = APIRouter(prefix="/internal/login", tags=["internal-login"])


@router.post("/access-token", response_model=Token)
def login_internal_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    auth_result = crud_admin.authenticate_admin_user(
        session=session, email=form_data.username, password=form_data.password
    )
    if not auth_result:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    admin_user, role = auth_result
    if not admin_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin user")

    access_token_expires = timedelta(
        minutes=settings.SYSTEM_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = security.create_access_token(
        admin_user.id,
        expires_delta=access_token_expires,
        additional_claims={"principal_type": "admin", "role": role.code},
    )
    return Token(access_token=access_token)


@router.post("/test-token", response_model=UserAdminPublic)
def test_internal_token(current_admin_auth: CurrentAdminAuth) -> UserAdminPublic:
    admin_user = current_admin_auth.admin_user
    return UserAdminPublic(
        id=admin_user.id,
        email=admin_user.email,
        role=current_admin_auth.role,
        is_active=admin_user.is_active,
    )
