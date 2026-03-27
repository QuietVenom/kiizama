"""Baseline schema for current backend models.

Revision ID: 20260325_0001
Revises:
Create Date: 2026-03-25 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260325_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    op.create_table(
        "lu_admin_role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lu_admin_role_code"),
        "lu_admin_role",
        ["code"],
        unique=True,
    )

    op.create_table(
        "user_admin",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["lu_admin_role.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_admin_email"),
        "user_admin",
        ["email"],
        unique=True,
    )

    op.create_table(
        "feature_flag",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feature_flag_key"),
        "feature_flag",
        ["key"],
        unique=True,
    )

    op.create_table(
        "feature_flag_audit",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("feature_flag_id", sa.UUID(), nullable=True),
        sa.Column("feature_flag_key", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("old_is_enabled", sa.Boolean(), nullable=True),
        sa.Column("new_is_enabled", sa.Boolean(), nullable=True),
        sa.Column("old_is_public", sa.Boolean(), nullable=True),
        sa.Column("new_is_public", sa.Boolean(), nullable=True),
        sa.Column("changed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("changed_by_admin_id", sa.UUID(), nullable=True),
        sa.Column("changed_by_email", sa.String(length=255), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feature_flag_audit_feature_flag_key"),
        "feature_flag_audit",
        ["feature_flag_key"],
        unique=False,
    )

    op.create_table(
        "waiting_list",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("interest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_waiting_list_email"),
        "waiting_list",
        ["email"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_waiting_list_email"), table_name="waiting_list")
    op.drop_table("waiting_list")

    op.drop_index(
        op.f("ix_feature_flag_audit_feature_flag_key"),
        table_name="feature_flag_audit",
    )
    op.drop_table("feature_flag_audit")

    op.drop_index(op.f("ix_feature_flag_key"), table_name="feature_flag")
    op.drop_table("feature_flag")

    op.drop_index(op.f("ix_user_admin_email"), table_name="user_admin")
    op.drop_table("user_admin")

    op.drop_index(op.f("ix_lu_admin_role_code"), table_name="lu_admin_role")
    op.drop_table("lu_admin_role")

    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
