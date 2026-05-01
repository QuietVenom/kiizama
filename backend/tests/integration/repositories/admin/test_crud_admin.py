from collections.abc import Generator
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlmodel import Session, delete

from app import crud_admin
from app.models import (
    FeatureFlag,
    FeatureFlagAudit,
    FeatureFlagCreate,
    FeatureFlagUpdate,
    LuAdminRole,
    UserAdmin,
)
from tests.utils.utils import random_email, random_password


@pytest.fixture(scope="module", autouse=True)
def ensure_admin_crud_tables(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, LuAdminRole).__table__.create(bind=bind, checkfirst=True)
    cast(Any, UserAdmin).__table__.create(bind=bind, checkfirst=True)
    cast(Any, FeatureFlag).__table__.create(bind=bind, checkfirst=True)
    cast(Any, FeatureFlagAudit).__table__.create(bind=bind, checkfirst=True)
    _clear_admin_rows(db)
    yield
    _clear_admin_rows(db)


def _clear_admin_rows(db: Session) -> None:
    db.exec(delete(FeatureFlagAudit))
    db.exec(delete(FeatureFlag))
    db.exec(delete(UserAdmin))
    db.commit()


def test_admin_roles_users_feature_flags_and_audits_persist_in_postgres(
    db: Session,
) -> None:
    # Arrange
    crud_admin.seed_admin_roles(session=db)
    role = crud_admin.get_admin_role_by_code(session=db, code="ops")
    assert role is not None
    email = random_email()
    password = random_password()
    flag_key = f"p1_{uuid4().hex}"

    # Act
    admin_user = crud_admin.create_admin_user(
        session=db,
        email=email,
        password=password,
        role=role,
    )
    authenticated = crud_admin.authenticate_admin_user(
        session=db,
        email=email,
        password=password,
    )
    unauthenticated = crud_admin.authenticate_admin_user(
        session=db,
        email=email,
        password="wrong-password",
    )
    feature_flag = crud_admin.create_feature_flag(
        session=db,
        feature_flag_in=FeatureFlagCreate(
            key=flag_key,
            description="P1 test flag",
            is_enabled=True,
            is_public=False,
        ),
    )
    updated_flag = crud_admin.update_feature_flag(
        session=db,
        db_feature_flag=feature_flag,
        feature_flag_in=FeatureFlagUpdate(
            description="Updated P1 test flag",
            is_public=True,
        ),
    )
    audit = crud_admin.create_feature_flag_audit(
        session=db,
        feature_flag=updated_flag,
        feature_flag_key=flag_key,
        action="updated",
        old_is_enabled=True,
        new_is_enabled=True,
        old_is_public=False,
        new_is_public=True,
        changed_by_user_id=None,
        changed_by_admin_id=admin_user.id,
        changed_by_email=email,
    )
    audits = crud_admin.list_feature_flag_audits(
        session=db,
        feature_flag_key=flag_key,
    )
    public_flags = crud_admin.list_feature_flags(session=db, only_public=True)
    crud_admin.delete_feature_flag(session=db, db_feature_flag=updated_flag)

    # Assert
    assert admin_user.email == email
    assert authenticated is not None
    assert authenticated[0].id == admin_user.id
    assert authenticated[1].code == "ops"
    assert unauthenticated is None
    assert updated_flag.description == "Updated P1 test flag"
    assert updated_flag.is_public is True
    assert audit.id in {item.id for item in audits}
    assert flag_key in {item.key for item in public_flags}
    assert crud_admin.get_feature_flag_by_key(session=db, key=flag_key) is None
