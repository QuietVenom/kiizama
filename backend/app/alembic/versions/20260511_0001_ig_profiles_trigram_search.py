"""add trigram search indexes for ig profiles

Revision ID: 20260511_0001
Revises: 20260506_0001
Create Date: 2026-05-11 00:00:00.000000
"""

from alembic import op

revision = "20260511_0001"
down_revision = "20260506_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_private_ig_profiles_username_trgm
        ON private.ig_profiles
        USING gin (lower(username) gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_private_ig_profiles_full_name_trgm
        ON private.ig_profiles
        USING gin (lower(coalesce(full_name, '')) gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS private.ix_private_ig_profiles_full_name_trgm")
    op.execute("DROP INDEX IF EXISTS private.ix_private_ig_profiles_username_trgm")
