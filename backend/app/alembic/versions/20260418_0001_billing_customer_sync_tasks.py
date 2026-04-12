"""add billing customer sync tasks

Revision ID: 20260418_0001
Revises: 20260417_0001
Create Date: 2026-04-18 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260418_0001"
down_revision = "20260417_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_customer_sync_task",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("sync_type", sa.String(length=64), nullable=False),
        sa.Column("desired_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.Column("last_stripe_request_id", sa.String(length=255), nullable=True),
        sa.Column("succeeded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["private.user.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="private",
    )
    op.create_index(
        "ix_private_billing_customer_sync_task_user_id",
        "billing_customer_sync_task",
        ["user_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_customer_sync_task_stripe_customer_id",
        "billing_customer_sync_task",
        ["stripe_customer_id"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_customer_sync_task_sync_type",
        "billing_customer_sync_task",
        ["sync_type"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_customer_sync_task_status",
        "billing_customer_sync_task",
        ["status"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_billing_customer_sync_task_next_attempt_at",
        "billing_customer_sync_task",
        ["next_attempt_at"],
        unique=False,
        schema="private",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_private_billing_customer_sync_task_next_attempt_at",
        table_name="billing_customer_sync_task",
        schema="private",
    )
    op.drop_index(
        "ix_private_billing_customer_sync_task_status",
        table_name="billing_customer_sync_task",
        schema="private",
    )
    op.drop_index(
        "ix_private_billing_customer_sync_task_sync_type",
        table_name="billing_customer_sync_task",
        schema="private",
    )
    op.drop_index(
        "ix_private_billing_customer_sync_task_stripe_customer_id",
        table_name="billing_customer_sync_task",
        schema="private",
    )
    op.drop_index(
        "ix_private_billing_customer_sync_task_user_id",
        table_name="billing_customer_sync_task",
        schema="private",
    )
    op.drop_table("billing_customer_sync_task", schema="private")
