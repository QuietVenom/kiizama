"""Add waiting list table

Revision ID: 4ab98a2898f3
Revises: c3f9ab2176e1
Create Date: 2026-02-28 00:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "4ab98a2898f3"
down_revision = "c3f9ab2176e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waiting_list",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("interest", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_waiting_list_email"), "waiting_list", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_waiting_list_email"), table_name="waiting_list")
    op.drop_table("waiting_list")
