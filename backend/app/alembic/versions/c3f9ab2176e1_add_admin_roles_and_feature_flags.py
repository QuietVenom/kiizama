"""Add admin roles and feature flags

Revision ID: c3f9ab2176e1
Revises: 6f60e3073c18
Create Date: 2026-02-27 00:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3f9ab2176e1"
down_revision = "6f60e3073c18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lu_admin_role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lu_admin_role_code"), "lu_admin_role", ["code"], unique=True)

    op.create_table(
        "user_admin",
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["lu_admin_role.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_admin_email"), "user_admin", ["email"], unique=True)

    op.create_table(
        "feature_flag",
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feature_flag_key"), "feature_flag", ["key"], unique=True)

    op.create_table(
        "feature_flag_audit",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("feature_flag_id", sa.UUID(), nullable=True),
        sa.Column("feature_flag_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("old_is_enabled", sa.Boolean(), nullable=True),
        sa.Column("new_is_enabled", sa.Boolean(), nullable=True),
        sa.Column("old_is_public", sa.Boolean(), nullable=True),
        sa.Column("new_is_public", sa.Boolean(), nullable=True),
        sa.Column("changed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("changed_by_admin_id", sa.UUID(), nullable=True),
        sa.Column("changed_by_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feature_flag_audit_feature_flag_key"),
        "feature_flag_audit",
        ["feature_flag_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_feature_flag_audit_feature_flag_key"), table_name="feature_flag_audit"
    )
    op.drop_table("feature_flag_audit")

    op.drop_index(op.f("ix_feature_flag_key"), table_name="feature_flag")
    op.drop_table("feature_flag")

    op.drop_index(op.f("ix_user_admin_email"), table_name="user_admin")
    op.drop_table("user_admin")

    op.drop_index(op.f("ix_lu_admin_role_code"), table_name="lu_admin_role")
    op.drop_table("lu_admin_role")
