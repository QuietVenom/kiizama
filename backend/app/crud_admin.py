import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import desc
from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    FeatureFlag,
    FeatureFlagAudit,
    FeatureFlagCreate,
    FeatureFlagUpdate,
    LuAdminRole,
    UserAdmin,
)

ADMIN_ROLE_SEED_DATA: list[tuple[int, str, str]] = [
    (1, "platform_owner", "Full control over platform-level internal operations."),
    (2, "ops", "Operational access to maintain and configure internal features."),
    (3, "viewer", "Read-only access to internal dashboards and feature flags."),
    (4, "system", "Machine/system actor for automated internal operations."),
]


def seed_admin_roles(*, session: Session) -> None:
    existing_roles = session.exec(select(LuAdminRole)).all()
    roles_by_code = {role.code: role for role in existing_roles}
    dirty = False

    for role_id, code, description in ADMIN_ROLE_SEED_DATA:
        role = roles_by_code.get(code)
        if not role:
            session.add(LuAdminRole(id=role_id, code=code, description=description))
            dirty = True
            continue
        if role.description != description:
            role.description = description
            session.add(role)
            dirty = True

    if dirty:
        session.commit()


def get_admin_role_by_code(*, session: Session, code: str) -> LuAdminRole | None:
    statement = select(LuAdminRole).where(LuAdminRole.code == code)
    return session.exec(statement).first()


def get_admin_user_by_email(*, session: Session, email: str) -> UserAdmin | None:
    statement = select(UserAdmin).where(UserAdmin.email == email)
    return session.exec(statement).first()


def create_admin_user(
    *, session: Session, email: str, password: str, role: LuAdminRole
) -> UserAdmin:
    db_obj = UserAdmin(
        email=email,
        hashed_password=get_password_hash(password),
        role_id=role.id,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def authenticate_admin_user(
    *, session: Session, email: str, password: str
) -> tuple[UserAdmin, LuAdminRole] | None:
    admin_user = get_admin_user_by_email(session=session, email=email)
    if not admin_user:
        return None
    if not verify_password(password, admin_user.hashed_password):
        return None
    role = session.get(LuAdminRole, admin_user.role_id)
    if not role:
        return None
    return admin_user, role


def get_feature_flag_by_key(*, session: Session, key: str) -> FeatureFlag | None:
    statement = select(FeatureFlag).where(FeatureFlag.key == key)
    return session.exec(statement).first()


def list_feature_flags(
    *, session: Session, only_public: bool = False
) -> list[FeatureFlag]:
    statement = select(FeatureFlag).order_by(FeatureFlag.key)
    if only_public:
        statement = statement.where(FeatureFlag.is_public)
    return list(session.exec(statement).all())


def create_feature_flag(
    *, session: Session, feature_flag_in: FeatureFlagCreate
) -> FeatureFlag:
    db_obj = FeatureFlag.model_validate(feature_flag_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_feature_flag(
    *,
    session: Session,
    db_feature_flag: FeatureFlag,
    feature_flag_in: FeatureFlagUpdate,
) -> FeatureFlag:
    update_data = feature_flag_in.model_dump(exclude_unset=True)
    db_feature_flag.sqlmodel_update(update_data)
    db_feature_flag.updated_at = datetime.now(timezone.utc)
    session.add(db_feature_flag)
    session.commit()
    session.refresh(db_feature_flag)
    return db_feature_flag


def delete_feature_flag(*, session: Session, db_feature_flag: FeatureFlag) -> None:
    session.delete(db_feature_flag)
    session.commit()


def create_feature_flag_audit(
    *,
    session: Session,
    feature_flag: FeatureFlag | None,
    feature_flag_key: str,
    action: Literal["created", "updated", "deleted"],
    old_is_enabled: bool | None,
    new_is_enabled: bool | None,
    old_is_public: bool | None,
    new_is_public: bool | None,
    changed_by_user_id: uuid.UUID | None,
    changed_by_admin_id: uuid.UUID | None,
    changed_by_email: str | None,
) -> FeatureFlagAudit:
    audit = FeatureFlagAudit(
        feature_flag_id=feature_flag.id if feature_flag else None,
        feature_flag_key=feature_flag_key,
        action=action,
        old_is_enabled=old_is_enabled,
        new_is_enabled=new_is_enabled,
        old_is_public=old_is_public,
        new_is_public=new_is_public,
        changed_by_user_id=changed_by_user_id,
        changed_by_admin_id=changed_by_admin_id,
        changed_by_email=changed_by_email,
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    return audit


def list_feature_flag_audits(
    *, session: Session, feature_flag_key: str
) -> list[FeatureFlagAudit]:
    statement = (
        select(FeatureFlagAudit)
        .where(FeatureFlagAudit.feature_flag_key == feature_flag_key)
        .order_by(desc("changed_at"))
    )
    return list(session.exec(statement).all())
