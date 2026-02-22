from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Annotated, Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.mongodb import get_mongo_kiizama_ig
from app.models import LuAdminRole, TokenPayload, User, UserAdmin

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)
reusable_oauth2_internal = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/internal/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]
InternalTokenDep = Annotated[str, Depends(reusable_oauth2_internal)]


@dataclass
class RequestPrincipal:
    principal_type: Literal["user", "admin"]
    user: User | None = None
    admin_user: UserAdmin | None = None
    role: str | None = None


@dataclass
class AdminAuthContext:
    admin_user: UserAdmin
    role: str


def _decode_token_payload(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    if not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return token_data


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    token_data = _decode_token_payload(token)
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_admin_auth(
    session: SessionDep, token: InternalTokenDep
) -> AdminAuthContext:
    token_data = _decode_token_payload(token)
    if token_data.principal_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    admin_user = session.get(UserAdmin, token_data.sub)
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")
    if not admin_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin user")

    role = session.get(LuAdminRole, admin_user.role_id)
    if not role:
        raise HTTPException(status_code=403, detail="Invalid admin role")

    return AdminAuthContext(admin_user=admin_user, role=role.code)


CurrentAdminAuth = Annotated[AdminAuthContext, Depends(get_current_admin_auth)]


def require_superuser_or_admin_roles(
    allowed_admin_roles: set[str] | None = None,
) -> Callable[[SessionDep, TokenDep], RequestPrincipal]:
    def dependency(session: SessionDep, token: TokenDep) -> RequestPrincipal:
        token_data = _decode_token_payload(token)

        if token_data.principal_type == "admin":
            admin_user = session.get(UserAdmin, token_data.sub)
            if not admin_user:
                raise HTTPException(status_code=404, detail="Admin user not found")
            if not admin_user.is_active:
                raise HTTPException(status_code=400, detail="Inactive admin user")

            role = session.get(LuAdminRole, admin_user.role_id)
            if not role:
                raise HTTPException(status_code=403, detail="Invalid admin role")

            if allowed_admin_roles and role.code not in allowed_admin_roles:
                raise HTTPException(
                    status_code=403,
                    detail="The admin user doesn't have enough privileges",
                )

            return RequestPrincipal(
                principal_type="admin", admin_user=admin_user, role=role.code
            )

        user = session.get(User, token_data.sub)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        if not user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )

        return RequestPrincipal(principal_type="user", user=user, role="superuser")

    return dependency


def get_profiles_collection():
    db = get_mongo_kiizama_ig()
    return db.get_collection("profiles")


def get_posts_collection():
    db = get_mongo_kiizama_ig()
    return db.get_collection("posts")


def get_reels_collection():
    db = get_mongo_kiizama_ig()
    return db.get_collection("reels")


def get_metrics_collection():
    db = get_mongo_kiizama_ig()
    return db.get_collection("metrics")


def get_profile_snapshots_collection():
    db = get_mongo_kiizama_ig()
    return db.get_collection("profile_snapshots")


def get_ig_credentials_collection():
    db = get_mongo_kiizama_ig()
    return db.get_collection("ig_credentials")
