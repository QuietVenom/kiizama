"""add search indexes for ig profiles

Revision ID: 20260506_0001
Revises: 20260418_0001
Create Date: 2026-05-06 00:00:00.000000
"""

from alembic import op

revision = "20260506_0001"
down_revision = "20260418_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_private_ig_profiles_follower_count",
        "ig_profiles",
        ["follower_count"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_ig_profiles_updated_at",
        "ig_profiles",
        ["updated_at"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_ig_profiles_ai_categories_gin",
        "ig_profiles",
        ["ai_categories"],
        unique=False,
        schema="private",
        postgresql_using="gin",
    )
    op.create_index(
        "ix_private_ig_profiles_ai_roles_gin",
        "ig_profiles",
        ["ai_roles"],
        unique=False,
        schema="private",
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_private_ig_profiles_ai_roles_gin",
        table_name="ig_profiles",
        schema="private",
    )
    op.drop_index(
        "ix_private_ig_profiles_ai_categories_gin",
        table_name="ig_profiles",
        schema="private",
    )
    op.drop_index(
        "ix_private_ig_profiles_updated_at",
        table_name="ig_profiles",
        schema="private",
    )
    op.drop_index(
        "ix_private_ig_profiles_follower_count",
        table_name="ig_profiles",
        schema="private",
    )
