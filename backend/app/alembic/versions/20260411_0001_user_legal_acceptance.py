"""add user legal acceptance audit table

Revision ID: 20260411_0001
Revises: 20260403_0001
Create Date: 2026-04-11 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260411_0001"
down_revision = "20260403_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_legal_acceptance",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("document_version", sa.String(length=32), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "document_type",
            "document_version",
            name="uq_private_user_legal_acceptance_user_document_version",
        ),
        schema="private",
    )
    op.create_index(
        "ix_private_user_legal_acceptance_user_id",
        "user_legal_acceptance",
        ["user_id"],
        unique=False,
        schema="private",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_private_user_legal_acceptance_user_id",
        table_name="user_legal_acceptance",
        schema="private",
    )
    op.drop_table("user_legal_acceptance", schema="private")
