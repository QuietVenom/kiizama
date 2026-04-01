"""add ig_scrape_jobs.execution_mode

Revision ID: 20260403_0001
Revises: 7a1ef1fcfc09
Create Date: 2026-04-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260403_0001"
down_revision = "7a1ef1fcfc09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ig_scrape_jobs",
        sa.Column(
            "execution_mode",
            sa.String(length=16),
            nullable=False,
            server_default="worker",
        ),
        schema="private",
    )
    op.execute(
        """
        UPDATE private.ig_scrape_jobs
        SET execution_mode = 'worker'
        WHERE execution_mode IS NULL OR execution_mode = '';
        """
    )
    op.create_index(
        "idx_ig_scrape_jobs_execution_mode_status_created_at",
        "ig_scrape_jobs",
        ["execution_mode", "status", "created_at"],
        unique=False,
        schema="private",
    )
    op.create_index(
        "ix_private_ig_scrape_jobs_execution_mode",
        "ig_scrape_jobs",
        ["execution_mode"],
        unique=False,
        schema="private",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_private_ig_scrape_jobs_execution_mode",
        table_name="ig_scrape_jobs",
        schema="private",
    )
    op.drop_index(
        "idx_ig_scrape_jobs_execution_mode_status_created_at",
        table_name="ig_scrape_jobs",
        schema="private",
    )
    op.drop_column("ig_scrape_jobs", "execution_mode", schema="private")
