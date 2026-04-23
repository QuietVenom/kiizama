import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app import crud_users as crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.security import get_password_hash, verify_password
from app.features.account_cleanup import (
    cleanup_user_related_data_before_delete,
    delete_user_event_stream_best_effort,
)
from app.features.billing import (
    BillingAccessError,
    build_billing_summary,
    publish_billing_event,
    queue_customer_email_sync_async,
    set_access_profile_async,
    sync_superuser_billing_access_async,
)
from app.features.billing.schemas import AccessProfileUpdate
from app.features.rate_limit import POLICIES, rate_limit
from app.models import (
    AdminUserCreate,
    AdminUserPublic,
    AdminUsersPublic,
    AdminUserUpdate,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email_best_effort

router = APIRouter(prefix="/users", tags=["users"])
SUPERUSER_AMBASSADOR_CONFLICT_DETAIL = (
    "Superuser and ambassador are mutually exclusive. Move the user to standard first."
)


def _build_admin_user_public(*, session: SessionDep, user: User) -> AdminUserPublic:
    summary = build_billing_summary(session=session, user_id=user.id)
    return AdminUserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        access_profile=summary.access_profile,
        managed_access_source=summary.managed_access_source,
        billing_eligible=summary.billing_eligible,
        plan_status=summary.plan_status,
    )


def _build_admin_user_public_billing_fallback(*, user: User) -> AdminUserPublic:
    return AdminUserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        access_profile="standard",
        managed_access_source=None,
        billing_eligible=False,
        plan_status="none",
    )


def _build_admin_user_public_for_list(
    *, session: SessionDep, user: User
) -> AdminUserPublic:
    try:
        return _build_admin_user_public(session=session, user=user)
    except BillingAccessError:
        return _build_admin_user_public_billing_fallback(user=user)


def _raise_superuser_ambassador_conflict() -> None:
    raise HTTPException(
        status_code=400,
        detail=SUPERUSER_AMBASSADOR_CONFLICT_DETAIL,
    )


def _validate_admin_user_create_payload(*, user_in: AdminUserCreate) -> None:
    if user_in.is_superuser and user_in.access_profile == "ambassador":
        _raise_superuser_ambassador_conflict()


def _validate_admin_user_update_transition(
    *,
    current_is_superuser: bool,
    current_access_profile: str,
    requested_is_superuser: bool | None,
    requested_access_profile: str | None,
) -> None:
    if requested_is_superuser is True and requested_access_profile == "ambassador":
        _raise_superuser_ambassador_conflict()
    if current_is_superuser and requested_access_profile == "ambassador":
        _raise_superuser_ambassador_conflict()
    if current_access_profile == "ambassador" and requested_is_superuser is True:
        _raise_superuser_ambassador_conflict()


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=AdminUsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()
    users_public = [
        _build_admin_user_public_for_list(session=session, user=user) for user in users
    ]
    return AdminUsersPublic(data=users_public, count=count)


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=AdminUserPublic,
)
async def create_user(
    *,
    session: SessionDep,
    user_in: AdminUserCreate,
    current_user: CurrentUser,
) -> Any:
    _validate_admin_user_create_payload(user_in=user_in)
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user_create = UserCreate(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser,
    )
    user = crud.create_user(session=session, user_create=user_create)
    billing_changed = await set_access_profile_async(
        session=session,
        user_id=user.id,
        access_profile=user_in.access_profile,
        created_by_admin_id=current_user.id,
    )
    billing_changed = (
        await sync_superuser_billing_access_async(
            session=session,
            user_id=user.id,
            is_superuser=user.is_superuser,
        )
        or billing_changed
    )
    if billing_changed:
        await publish_billing_event(
            session=session,
            user_id=user.id,
            event_name="account.subscription.updated",
        )
    email_data = generate_new_account_email(
        email_to=user_in.email, username=user_in.email, password=user_in.password
    )
    send_email_best_effort(
        email_to=user_in.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return _build_admin_user_public(session=session, user=user)


@router.patch(
    "/me",
    response_model=UserPublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
async def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    previous_email = str(current_user.email)
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    await queue_customer_email_sync_async(
        session=session,
        user=current_user,
        previous_email=previous_email,
    )
    return current_user


@router.patch(
    "/me/password",
    response_model=Message,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get(
    "/me",
    response_model=UserPublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user


@router.delete(
    "/me",
    response_model=Message,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
async def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    user_id = current_user.id
    await cleanup_user_related_data_before_delete(
        session=session,
        user_id=user_id,
    )
    session.delete(current_user)
    session.commit()
    await delete_user_event_stream_best_effort(user_id=user_id)
    return Message(message="User deleted successfully")


@router.post(
    "/signup",
    response_model=UserPublic,
    dependencies=[Depends(rate_limit(POLICIES.public_auth_signup))],
)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
    )
    user = crud.create_signup_user(session=session, user_create=user_create)
    return user


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=AdminUserPublic,
)
async def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: AdminUserUpdate,
    current_user: CurrentUser,
) -> Any:
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    was_superuser = db_user.is_superuser
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    previous_email = str(db_user.email)
    access_profile = user_in.access_profile
    current_summary = build_billing_summary(session=session, user_id=db_user.id)
    _validate_admin_user_update_transition(
        current_is_superuser=was_superuser,
        current_access_profile=current_summary.access_profile,
        requested_is_superuser=user_in.is_superuser,
        requested_access_profile=access_profile,
    )
    user_update_data = user_in.model_dump(
        exclude_unset=True,
        exclude_none=True,
        exclude={"access_profile"},
    )
    user_update = UserUpdate.model_validate(user_update_data)
    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_update)
    await queue_customer_email_sync_async(
        session=session,
        user=db_user,
        previous_email=previous_email,
    )
    billing_changed = was_superuser != db_user.is_superuser
    if access_profile is not None:
        billing_changed = (
            await set_access_profile_async(
                session=session,
                user_id=db_user.id,
                access_profile=access_profile,
                created_by_admin_id=current_user.id,
            )
            or billing_changed
        )
    billing_changed = (
        await sync_superuser_billing_access_async(
            session=session,
            user_id=db_user.id,
            is_superuser=db_user.is_superuser,
        )
        or billing_changed
    )
    if billing_changed:
        await publish_billing_event(
            session=session,
            user_id=db_user.id,
            event_name="account.subscription.updated",
        )
    return _build_admin_user_public(session=session, user=db_user)


@router.put(
    "/{user_id}/access-profile",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=AdminUserPublic,
)
async def update_user_access_profile(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    body: AccessProfileUpdate,
    current_user: CurrentUser,
) -> Any:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser and body.access_profile == "ambassador":
        _raise_superuser_ambassador_conflict()
    billing_changed = await set_access_profile_async(
        session=session,
        user_id=user.id,
        access_profile=body.access_profile,
        created_by_admin_id=current_user.id,
    )
    billing_changed = (
        await sync_superuser_billing_access_async(
            session=session,
            user_id=user.id,
            is_superuser=user.is_superuser,
        )
        or billing_changed
    )
    if billing_changed:
        await publish_billing_event(
            session=session,
            user_id=user.id,
            event_name="account.subscription.updated",
        )
    return _build_admin_user_public(session=session, user=user)


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
async def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    deleted_user_id = user.id
    await cleanup_user_related_data_before_delete(
        session=session,
        user_id=deleted_user_id,
    )
    session.delete(user)
    session.commit()
    await delete_user_event_stream_best_effort(user_id=deleted_user_id)
    return Message(message="User deleted successfully")
